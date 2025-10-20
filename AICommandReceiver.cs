using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityWebSocket;
using System.Text;
using Newtonsoft.Json;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;
/*using UnityEngine.InputSystem;*/
using System.Net.Sockets;
#if UNITY_EDITOR
using UnityEditor.PackageManager;
#endif

using System.Linq;
using Opc.Ua;
using System;
using Random = UnityEngine.Random; // 添加这行解决冲突

public class AICommandReceiver : MonoBehaviour
{
    public GameObject dronePrefab;
    public GameObject inspectionCarPrefab;
    // 新增字段：存储报警图标预制体
    public GameObject warningIconPrefab; // 拖拽SVG图标预制体到Inspector
    public Transform factoryBuildings; // 工厂建筑父对象
                                       // 在 AICommandReceiver 类中新增字段
    private HashSet<GameObject> usedDrones = new HashSet<GameObject>(); // 存储正在被使用的无人机对象

    private WebSocket websocket;
    [System.Serializable]
    public class VehicleEntry
    {
        public string vehicleType; // 如"无人机"、"巡检车"
        public GameObject vehicleObject;
    }

    // 巡检车辆列表
    public List<VehicleEntry> vehicleList = new List<VehicleEntry>();


    // 运行时转换为Dictionary（保持原有代码兼容性）
    private Dictionary<string, GameObject> vehicleMap
        => vehicleList.ToDictionary(v => v.vehicleType, v => v.vehicleObject);


    // 替换原来的factoryBuildings，使用可序列化的目标列表
    [System.Serializable]
    public class InspectionTarget
    {
        public string targetName; // 与TaskData中的targets名称对应
        public Transform targetTransform;
    }
    public List<InspectionTarget> inspectionTargets = new List<InspectionTarget>();

    // 新增：目标名称到Transform的快速查找字典
    private Dictionary<string, Transform> targetMap
        => inspectionTargets.ToDictionary(t => t.targetName, t => t.targetTransform);

    private bool isConnecting = false; // 新增：防止重复连接尝试
    private bool eventsRegistered = false; // 新增：避免重复注册事件

    async void Start()
    {
        // 连接到Python WebSocket服务器
        websocket = new WebSocket("ws://localhost:8080");

        RegisterEvents();
        // 启动重连协程（非阻塞）
        StartCoroutine(ReconnectLoop());


        // === 注册 WebSocket 事件回调 ===


        /*   websocket.OnOpen += (sender, e) =>
           {
               Debug.Log("WebSocket 连接已建立到 ws://localhost:8501");
               var registerMsg = new { type = "register", client = "UnityClient" };  // 明确注册
               string json = JsonConvert.SerializeObject(registerMsg);
               websocket.SendAsync(json);
               Debug.Log("客户端已注册");
           };

           websocket.OnMessage += (sender, e) =>
           {
               if (e.IsText)
               {
                   string message = e.Data;
                   Debug.Log("收到消息: " + message);
                   ProcessAICommand(message); // 处理接收到的命令
               }
               else if (e.IsBinary)
               {
                   Debug.Log("收到二进制消息，暂不处理");
               }
           };

           websocket.OnError += (sender, e) =>
           {
               Debug.LogError("WebSocket 错误: " + e.Message);
               if (e.Exception != null)
                   Debug.LogException(e.Exception);
           };

           websocket.OnClose += (sender, e) =>
           {
               Debug.LogWarning($"WebSocket 连接已关闭. 状态: {e.Code} - {e.Reason}");
           };

           // === 启动连接 ===
           try
           {
               websocket.ConnectAsync();
           }
           catch (System.Exception ex)
           {
               Debug.LogError("连接失败: " + ex.Message);
           }*/
    }

    void Update()
    {

    }


    // 新增：重连协程，实现持续连接尝试
    private IEnumerator ReconnectLoop()
    {
        while (true)
        {
            if (websocket.ReadyState != WebSocketState.Open && !isConnecting)
            {
                isConnecting = true;
                Debug.LogWarning($"[{Time.time:F1}] WebSocket连接未建立，开始重试..."); // 添加时间戳，便于追踪

                try
                {
                    // 用Task等待异步连接完成（避免立即检查）
                    websocket.ConnectAsync();
  
                }
                catch (System.Exception ex)
                {
                    Debug.LogWarning($"[{Time.time:F1}] 连接异常: {ex.Message}，1秒后重试。");
                }
                finally
                {
                    isConnecting = false;
                }

                Debug.Log($"[{Time.time:F1}] 连接状态: {websocket.ReadyState}, isConnecting: {isConnecting}");
            }

            yield return new WaitForSeconds(3f); // 每1秒检查
        }
    }

    // 新增：注册事件回调（提取为独立方法，避免重复）
    private void RegisterEvents()
    {
        websocket.OnOpen += (sender, e) =>
        {
            Debug.Log("WebSocket 连接已建立到 ws://localhost:8080"); // 修正日志端口
            var registerMsg = new { type = "register", client = "UnityClient" };
            string json = JsonConvert.SerializeObject(registerMsg);
            websocket.SendAsync(json);
            Debug.Log("客户端已注册");
        };

        websocket.OnMessage += (sender, e) =>
        {
            if (e.IsText)
            {
                string message = e.Data;
                Debug.Log("收到消息: " + message);
                ProcessAICommand(message);
            }
            else if (e.IsBinary)
            {
                Debug.Log("收到二进制消息，暂不处理");
            }
        };

        websocket.OnError += (sender, e) =>
        {
            Debug.LogError("WebSocket 错误: " + e.Message);
            if (e.Exception != null)
                Debug.LogException(e.Exception);
        };

        websocket.OnClose += (sender, e) =>
        {
            Debug.LogWarning($"WebSocket 连接已关闭. 状态: {e.Code} - {e.Reason}");
            eventsRegistered = false; // 重置注册标志，触发重连
            // 重连由协程处理，无需额外调用
        };

        eventsRegistered = true;
    }


    private void ProcessAICommand(string message)
    {
        try
        {
            // 解析JSON消息
            var jsonObj = JsonConvert.DeserializeObject<JObject>(message);

            // 检查消息类型
            string messageType = jsonObj["message_type"]?.ToString();

            Debug.Log("json: " + jsonObj);

            if (messageType == "task_command")
            {
                var taskData = jsonObj["data"].ToObject<TaskData>();
                ExecuteInspectionTask(taskData);
                SendDiagnosisRequest(taskData);
            }
            else if (messageType == "diagnosis_result")
            {
                var diagnosisData = jsonObj["data"].ToObject<DiagnosisResultData>();
                UpdateFaultVisualization(diagnosisData);
            }
            else
            {
                Debug.LogWarning("未知的消息类型: " + messageType);
            }
        }
        catch (System.Exception e)
        {
            Debug.LogError("命令解析错误: " + e.Message);
        }
    }

    private void ExecuteInspectionTask(TaskData taskData)
    {
        Debug.Log($"开始执行巡检任务: {taskData.task_id}");

        // 1. 查询任务清单中的巡检目标
        foreach (var inspection in taskData.inspections)
        {
            string building = inspection.target;
            string[] items = inspection.items;
            Debug.Log("测试building: " + building);
            if (targetMap.ContainsKey(building))
            {
                Debug.Log("building: " + building);

                if (building.Equals("1号仓库"))
                {
                    foreach (var vehicle in taskData.required_vehicles)
                    {
                        Debug.Log("vehicle: " + vehicle);
                        if (vehicle.Equals("巡检车"))
                        {
                            // 遍历所有载具
                            foreach (KeyValuePair<string, GameObject> kvp in vehicleMap)
                            {
                                if (kvp.Key.Contains("巡检车1"))
                                {
                                    // 执行巡检车特定操作
                                    // 获取1号仓库的Transform
                                    Transform Car = kvp.Value.transform;
                                    var Script = Car.GetComponent<NewMove>();
                                    if (Script != null)
                                    {
                                        Debug.Log("进入巡检车1");
                                        Script.isstart = true; // 调用脚本方法
                                    }
                                    else
                                    {
                                        Debug.LogWarning("未找到巡检车1脚本");
                                    }
                                }
                                else if (kvp.Key.Contains("巡检车2"))
                                {
                                    Transform Car = kvp.Value.transform;
                                    var Script = Car.GetComponent<Move3>();
                                    if (Script != null)
                                    {
                                        Script.isstart = true; // 调用脚本方法
                                    }
                                    else
                                    {
                                        Debug.LogWarning("未找到巡检车2脚本");
                                    }
                                }
                                else if (kvp.Key.Contains("巡检车3"))
                                {
                                    Transform Car = kvp.Value.transform;
                                    var Script = Car.GetComponent<CarMove>();
                                    if (Script != null)
                                    {
                                        Script.isstart = true; // 调用脚本方法
                                    }
                                    else
                                    {
                                        Debug.LogWarning("未找到巡检车3脚本");
                                    }
                                }
                                else if (kvp.Key.Contains("巡检车4"))
                                {
                                    Transform Car = kvp.Value.transform;
                                    var Script = Car.GetComponent<chacheMove>();
                                    if (Script != null)
                                    {
                                        Script.isstart = true; // 调用脚本方法
                                    }
                                    else
                                    {
                                        Debug.LogWarning("未找到巡检车4脚本");
                                    }
                                }
                            }
                        }
                        if (vehicle.Equals("无人机"))
                        {
                            foreach (KeyValuePair<string, GameObject> kvp in vehicleMap)
                            {
                                if (kvp.Key.Contains("无人机"))
                                {
                                    // 对于无人机，先尝试获取现有无人机
                                    Transform targetBuilding = targetMap[building]; // 获取第一个建筑作为示例目标
                                    if (targetBuilding != null)
                                    {
                                        GameObject existingDrone = GetNearestDrone(targetBuilding.position);
                                   
                                        if (existingDrone != null)
                                        {
                                            // 标记为已使用
                                            usedDrones.Add(existingDrone);
                                            Transform Drone = existingDrone.transform;
                                            var Script = Drone.GetComponent<Dronefly>();
                                            if (Script != null)
                                            {
                                     
                                                Script.targetPosition = targetBuilding.position;
                                                Script.autoTest = true;
                                                Script.isused = true;
                                                Debug.Log("启动无人机："+ Script.autoTest);
                                            }
                                        }
                                    }
                                    else
                                    {
                                        Debug.LogWarning("未找到无人机脚本");
                                    }
                                }
                            }

                        }
                  
                    }
                }
                if(building.Equals("提升机楼"))
                {
                    foreach (var vehicle in taskData.required_vehicles)
                    {
                        if (vehicle.Equals("无人机"))
                        {
                            foreach (KeyValuePair<string, GameObject> kvp in vehicleMap)
                            {
                                if (kvp.Key.Contains("无人机"))
                                {
                                    // 对于无人机，先尝试获取现有无人机
                                    Transform targetBuilding = targetMap[building]; // 获取建筑作为目标
                                    if (targetBuilding != null)
                                    {
                                        GameObject existingDrone = GetNearestDrone(targetBuilding.position);
                                        if (existingDrone != null)
                                        {
                                            // 标记为已使用
                                            usedDrones.Add(existingDrone);
                                            Transform Drone = existingDrone.transform;
                                            var Script = Drone.GetComponent<Dronefly>();
                                            if (Script != null)
                                            {

                                                Script.targetPosition = targetBuilding.position;
                                                Script.autoTest = true;
                                                Debug.Log("启动无人机：" + Script.autoTest);
                                            }
                                        }
                                    }
                                    else
                                    {
                                        Debug.LogWarning("未找到无人机脚本");
                                    }
                                }
                            }

                        }

                    }
                }
               /* GameObject vehicleObj = InstantiateVehicle(vehicle);*/
                /*   vehicleMap[vehicle] = vehicleObj;*/
                /*            Debug.Log($"创建载具: {vehicle}");*/
            }
        }


        // 1. 在数字孪生中创建或激活载具
  

        // 2. 规划路径并开始移动
    /*    StartCoroutine(ExecuteInspectionRoute(taskData));*/
    }





    private Transform FindBuilding(string buildingName)
    {
        foreach (Transform child in factoryBuildings)
        {
            if (child.name == buildingName)
                return child;
        }
        return null;
    }






    /// <summary>
    /// 获取距离目标最近的无人机对象
    /// </summary>
    private GameObject GetNearestDrone(Vector3 targetPosition)
    {
        // 获取所有 key 包含 "无人机" 的 GameObject，并排除已被使用的
        var availableDrones = vehicleMap
            .Where(pair => pair.Key.Contains("无人机") && pair.Value != null)
            .Select(pair => pair.Value)
            .Where(drone => !usedDrones.Contains(drone)) // 关键：只选未被使用的
            .OrderBy(drone => Vector3.Distance(drone.transform.position, targetPosition))
            .ToList();

        if (availableDrones.Count == 0)
        {
            Debug.Log("没有可用的空闲无人机（所有无人机都在使用中或未找到）");
            return null;
        }

        GameObject nearestDrone = availableDrones.First();

        Debug.Log($"选择空闲无人机：{nearestDrone.name}，距离目标：{Vector3.Distance(nearestDrone.transform.position, targetPosition):F2}米");
        return nearestDrone;
    }


    // 模拟传感器数据生成 - 三层分级结构
    private JObject SimulateSensorData(TaskData taskData)
    {
        // 创建顶层JSON对象
        JObject sensorData = new JObject();

        // 添加元数据
        sensorData["timestamp"] = DateTime.UtcNow.ToString("o");

        // 创建检查目标数组
        JArray targetsArray = new JArray();

        foreach (var inspection in taskData.inspections)
        {
            // 每个检查目标创建一个对象
            JObject targetObj = new JObject();
            targetObj["target_name"] = inspection.target;

            // 创建设备类型数组
            JArray equipmentArray = new JArray();

            foreach (var item in inspection.items)
            {
                // 每个检查项创建一个设备对象
                JObject equipmentObj = new JObject();
                equipmentObj["equipment_type"] = item;

                // 添加设备特定数据
                JObject checkData = new JObject();

                switch (item)
                {
                    case "油路检查":
                        checkData["Residual_Pressure"] = Math.Round(Random.Range(0.1f, 0.8f), 2);
                        checkData["Temperature"] = Random.Range(30, 60);
                        checkData["Pressure"] = Math.Round(Random.Range(6.0f, 8.0f), 1);
                        checkData["Level"] = Math.Round(Random.Range(0.33f, 0.6f), 2);
                        break;

                    case "电控系统检查":
                        checkData["Temperature"] = Mathf.Round(Random.Range(18, 25));
                        checkData["Humidity"] = Math.Round(Random.Range(0.4f, 0.6f), 2);
                        break;

                    case "排水检查":
                        checkData["Residual_Water_Volume"] = Mathf.Round(Random.Range(0, 10));
                        checkData["Drain_Outlet_Clear"] = Random.value > 0.9f;
                        break;

                    case "防火检查":
                        checkData["Fire_Extinguisher_Pressure"] = Math.Round(Random.Range(1.0f, 1.5f), 1);
                        checkData["Evacuation_Pathway_Width"] = Math.Round(Random.Range(0f, 2f), 1);
                        checkData["Fire_Door_Closure_Status"] = Random.value > 0.9f;
                        checkData["Fire_Hydrant_Water_Pressure"] = Math.Round(Random.Range(0f, 1f), 1);
                        break;

                    default:
                        checkData["temperature"] = Math.Round(Random.Range(40f, 80f), 1);
                        checkData["vibration"] = Math.Round(Random.Range(0.1f, 0.8f), 2);
                        checkData["oil_pressure"] = Math.Round(Random.Range(15f, 30f), 1);
                        checkData["motor_current"] = Random.Range(70, 150);
                        checkData["cutting_power"] = Random.Range(80, 120);
                        break;
                }

                // 添加状态标记
                checkData["status"] = Random.value > 0.8f ? "fault" : "normal";
                checkData["last_check_time"] = DateTime.UtcNow.ToString("yyyy-MM-dd HH:mm:ss");

                equipmentObj["check_data"] = checkData;
                equipmentArray.Add(equipmentObj);
            }

            targetObj["equipments"] = equipmentArray;
            targetsArray.Add(targetObj);
        }

        sensorData["targets"] = targetsArray;

        return sensorData;
    }







/*    private void UpdateFaultVisualization(DiagnosisData diagnosisData)
    {
        Debug.Log($"发现故障: {diagnosisData.fault_type} 在 {diagnosisData.location}");

        // 在故障位置显示警示效果
        Transform faultBuilding = FindBuilding(diagnosisData.location);
        if (faultBuilding != null)
        {
            // 显示红色警示光圈等视觉效果
            ShowWarningEffect(faultBuilding.position, diagnosisData.severity);
        }
    }

    private void ShowWarningEffect(Vector3 position, float severity)
    {
        // 创建警示效果对象
        GameObject warningEffect = new GameObject("WarningEffect");
        warningEffect.transform.position = position + Vector3.up * 2;

        // 添加粒子系统组件
        var particleSystem = warningEffect.AddComponent<ParticleSystem>();
        var mainModule = particleSystem.main;
        mainModule.startSize = 0.5f * severity;
        mainModule.startColor = Color.Lerp(Color.yellow, Color.red, severity);

        // 自动销毁
        Destroy(warningEffect, 5.0f);
    }*/




    private async void SendDiagnosisRequest(TaskData taskData)
    {
        if (websocket.ReadyState == WebSocketState.Open)
        {
            try
            {
                // 生成结构化传感器数据
                JObject sensorData = SimulateSensorData(taskData);

                // 构建诊断请求
                var diagnosisRequest = new
                {
                    message_type = "diagnosis_request",
                    task_id = taskData.task_id,
                    task_data = new
                    {
                        task_id = taskData.task_id,
                        inspections = taskData.inspections.Select(i => new {
                            target = i.target,
                            items = i.items
                        }).ToArray()
                    },
                    sensor_data = sensorData
                };

                // 序列化并发送
                string jsonMessage = JsonConvert.SerializeObject(diagnosisRequest, Formatting.Indented);
                websocket.SendAsync(jsonMessage);
                Debug.Log("诊断请求已发送:\n" + jsonMessage);
            }
            catch (Exception ex)
            {
                Debug.LogError($"发送诊断请求失败: {ex.Message}");
            }
        }
    }


    // 修改：更新故障可视化方法，处理多个目标
    private void UpdateFaultVisualization(DiagnosisResultData diagnosisData)
    {
        Debug.Log($"诊断结果: 整体状态 {diagnosisData.overall_status}, 系统风险 {diagnosisData.system_risk}");

        // 遍历每个目标诊断
        foreach (var targetDiag in diagnosisData.target_diagnoses)
        {
            if (targetDiag.status == "故障" && targetMap.ContainsKey(targetDiag.target))
            {
                // 获取目标Transform
                Transform targetTransform = targetMap[targetDiag.target];
                Debug.Log($"目标 {targetDiag.target} 故障，位置: {targetTransform.position}");

                // 计算严重度：优先使用critical_issues中的severity，如果为空则用system_risk
                float severity = diagnosisData.system_risk / 100f; // 归一化到0-1
                if (targetDiag.critical_issues != null && targetDiag.critical_issues.Count > 0)
                {
                    severity = targetDiag.critical_issues[0].severity / 100f; // 使用第一个问题的严重度
                }

                // 显示红色报警效果
                ShowWarningEffect(targetTransform.position, severity);

                // 可选：输出维护建议日志
                if (targetDiag.maintenance_suggestions != null)
                {
                    Debug.Log($"维护建议 for {targetDiag.target}: {string.Join(", ", targetDiag.maintenance_suggestions)}");
                }
            }
            else if (targetDiag.status == "正常")
            {
                Debug.Log($"目标 {targetDiag.target} 正常，无需报警");
                // 可选：清除之前的效果（如果需要持久化状态）
            }
        }
    }

    // 修改：增强警示效果，确保红色报警
    private void ShowWarningEffect(Vector3 position, float severity)
    {
        if (warningIconPrefab == null)
        {
            Debug.LogError("未分配报警图标预制体！");
            return;
        }

        // 实例化图标
        GameObject icon = Instantiate(warningIconPrefab, position + Vector3.up * 2, Quaternion.identity);

        // 根据严重度调整图标大小和颜色
        float scale = Mathf.Lerp(0.5f, 1.5f, severity); // 严重度越高图标越大
        icon.transform.localScale = Vector3.one * scale;

        // 可选：动态修改颜色（如正常=绿色，警告=黄色，严重=红色）
        SpriteRenderer renderer = icon.GetComponent<SpriteRenderer>();
        if (renderer != null)
        {
            renderer.color = severity > 0.7f ? Color.red :
                             severity > 0.3f ? Color.yellow : Color.green;
        }

        // 添加旋转动画（可选）
        StartCoroutine(RotateIcon(icon));

        // 自动销毁
        Destroy(icon, 100f);
    }


    // 旋转动画协程（可选）
    private IEnumerator RotateIcon(GameObject icon)
    {
        while (icon != null)
        {
            icon.transform.Rotate(Vector3.up, 90 * Time.deltaTime);
            yield return null;
        }
    }


    async void OnApplicationQuit()
    {
        if (websocket != null && websocket.ReadyState == WebSocketState.Open)
        {
            websocket.CloseAsync();
        }
    }
}

// 数据类定义
[System.Serializable]
public class InspectionEntry
{
    public string target;
    public string[] items;
}
public class TaskData
{
    public string task_id;
    public string task_type;
    public InspectionEntry[] inspections;
    public string priority;
    public string[] required_vehicles;
    public string estimated_duration;
    public string deadline;
    public string special_instructions;
}

[System.Serializable]
public class DiagnosisData
{
    public string location;
    public string fault_type;
    public float severity;
}

// 新增：诊断结果数据类，匹配JSON结构
[System.Serializable]
public class DiagnosisResultData
{
    public string overall_status; // 如 "部分故障"
    public string task_id;
    public List<TargetDiagnosis> target_diagnoses; // 目标诊断数组
    public int system_risk; // 系统风险值，如 85
    public int severity; // 整体严重度，如 0
    public string timestamp;
    public object original_data; // 原数据，可忽略或进一步解析

    [System.Serializable]
    public class TargetDiagnosis
    {
        public string target; // 目标名称，如 "提升机楼"
        public string status; // 状态，如 "故障" 或 "正常"
        public List<CriticalIssue> critical_issues; // 关键问题数组
        public List<string> maintenance_suggestions; // 维护建议

        [System.Serializable]
        public class CriticalIssue
        {
            public string parameter; // 参数，如 "油路状态"
            public string abnormal_value; // 异常值，如 "故障"
            public List<object> normal_range; // 正常范围
            public string possible_cause; // 可能原因
            public int severity; // 严重度，如 90
            public List<string> repair_priority; // 修复优先级
        }
    }
}