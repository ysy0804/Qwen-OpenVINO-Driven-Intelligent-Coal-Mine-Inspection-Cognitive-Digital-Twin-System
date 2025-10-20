
# 端侧AI创新挑战赛-Qwen-OpenVINO驱动的智能煤矿巡检认知数字孪生系统

### 赛道二：英特尔AI-PC

### 1.项目背景

传统煤矿巡检场景，依赖人工巡检，成本高、费时且容易造成人员伤亡。随着无人化巡检技术的日益发展，无人机、无人巡检车等设备陆续被投入到日常巡检中。然而，目前的无人化巡检系统存在以下痛点：

（1）管理端与执行端脱节。管理人员缺少直观查看巡检状态的有效手段。

（2）需要人工将巡检任务配置成结构化指令，产生大量时间成本、人员培训成本，也增加了系统复杂度。

（3）巡检故障诊断算法精确度低，泛化能力差，严重依赖于人工从数据中提取的特征，处理多模态数据能力弱。

（4）需要大规模算力支撑，管理平台依赖云端部署，任务发布者需要到固定地点采用固定设备进行任务发布，灵活性差。

基于以上原因，我们为煤矿无人化巡检打造数字孪生系统，为管理人员提供能方便、直观的巡检管理工具。我们摒弃了传统的任务发布与故障诊断模式，引入通义大模型，实现了自然语言到结构化任务的快速转换，以及巡检故障的智能化诊断。系统部署在Intel AI PC上，为管理人员提供了便携式巡检管理平台，为矿山巡检领域提供了一项新颖的端侧人工智能应用案例。

本项目的优势与创新如下：

**（1）基于数字孪生的直观管理与实时交互，实现管理执行一体化闭环。**

本项目创新地构建了高保真煤矿数字孪生场景，将物理世界的巡检设备（无人机、巡检车）及其运行状态实时映射至虚拟空间。管理人员可通过AI PC上的三维可视化界面，直观地实时监控巡检轨迹、设备状态，并能直接接收诊断结果与故障告警，打破了管理端与执行端的信息壁垒。

**（2）基于Qwen大模型的自然语言任务交互，极大降低系统使用门槛。**

本项目的一项关键创新在于利用Qwen大模型的强大自然语言理解与推理能力。**任务发布者无需学习复杂的专业软件或编写结构化指令，可直接使用自然语言（如：“让无人机去检查一下A区皮带的运行状态”）描述巡检需求**。Qwen大模型将自动理解用户意图，并将其精准转化为可供无人机、巡检车执行的结构化任务序列与巡检路线，极大简化了操作流程，消除了培训成本。

**（3）基于大模型的端侧智能诊断，实现精准、可解释的故障分析。**

区别于传统单一、固化的诊断算法，本项目利用Qwen大模型的信息融合与强大的因果推理能力，对巡检设备传回的温度、振动等多源数据进行一体化综合分析。它不仅能识别预定义的故障模式，更能基于其内化的丰富知识进行推理，发现潜在隐患、分析故障根因，并以自然语言形式生成可读的诊断报告与维修建议。

**（4）基于英特尔® OpenVINO™工具套件的AI-PC端侧部署，实现高效能、高灵活性。**

本项目最大的特色在于将完整的认知智能 pipeline（从自然语言理解到故障诊断）通过**英特尔® OpenVINO™工具套件**优化并部署在**AI PC端侧**。这不仅减少了对云端算力的依赖，降低了网络延迟与数据安全风险，更使得管理人员能够**随时随地**通过个人AI PC发布任务、接收结果，实现了真正的移动办公与即时响应，系统灵活性与实用性获得质的飞跃。

综上，我们利用LLM的自然语言理解能力，赋能数字孪生具有认知能力，从宏观上看，管理人员可以直接对数字孪生体发出自然语言，数字孪生体能够理解自然语言进行巡检任务发布，接受巡检数据后，能够利用LLM在内部标记出故障。



### 2.功能介绍

系统结构图如下：

![](/img/1.png)

系统使用流程：

**（1）无人化巡检数字孪生体**

在”数字孪生系统“窗口中，可以查看矿区的3D建模场景，通过W、A、S、D键可以进行视角的前、左、后、右移动。

<img src="/img/2.gif" style="zoom: 100%" />

**（2）巡检任务文档上传与自动解析**

用自然语言描述的巡检任务文档：

![](/img/3.png)

点击按钮上传巡检任务文件，Qwen解析文档提取文本，提供预览：

![](/img/4.png)

点击解析任务按钮，Qwen将自然语言描述的巡检任务解析为json格式的结构化任务：

解析后提供任务概览：

![](/img/5.png)
解析后得到的结构化任务：

![](/img/6.png)
**（3）将结构化任务发送到数字孪生**

点击任务发布按钮，发送任务到数字孪生

![](/img/7.png)

数字孪生系统根据结构化任务执行巡检任务：

<img src="/img/8.gif" style="zoom: 100%" />

**（4）故障诊断**

巡检任务完成后，巡检数据被反馈到Qwen：

![](/img/9.png)

Qwen根据巡检数据，进行设备故障诊断：

![](/img/10.png)

得到结构化的诊断结果后，将诊断结果发送到数字孪生体，数字孪生体在故障相应位置进行标记：

<img src="/img/11.gif" style="zoom: 100%" />

与此同时，自动生成巡检故障诊断报告，在主页面可以下载最新的报告：

![](/img/12.png)

故障报告：

![](/img/13.png)

### 3.技术实现

**（1）运行平台**

- PC：HP 战66     
- CPU: Intel  UItra7-155H
- GPU: Intel Arc Graphics
- NPU: intel AI Boost

**（2）开发工具**

- 关键工具：

|   工具名称   |                版本号                 |                 作用                 |
| :----------: | :-----------------------------------: | :----------------------------------: |
|    Python    |                3.10.18                | 编写模型部署、推理代码、构建管理平台 |
|  streamlit   |                1.28.2                 |         搭建巡检任务发布平台         |
|   **Qwen**   | **Qwen2.5-Coder-7B-Instruct-int4-ov** |   **结构化巡检任务，实现故障诊断**   |
|   OpenVINO   |               2025.3.0                |             部署Qwen模型             |
|  modelScope  |                1.30.0                 |              魔搭模型库              |
|   PyMuPDF    |                1.26.4                 |            处理 PDF 文档             |
|  websockets  |                15.0.1                 |      数字孪生与Qwen间的数据传输      |
|  reportlab   |                 4.4.4                 |       生成故障诊断报告pdf文档        |
| unity Editor |             2022.3.62f2c1             |           构建数字孪生模型           |
|    WebGL     |                  2.0                  |       在浏览器渲染数字孪生模型       |

- 环境配置

Qwen模型端：

```python
pip install openvino-genai streamlit
pip install PyMuPDF
pip install websockets asyncio websocket-client
```

Qwen模型下载：

[组织详情 · 魔搭社区](https://www.modelscope.cn/organization/openvino/)

数字孪生端：

为Unity Editor添加WebGL模块

![](/img/14.png)

在Unity Editor中添加UnityWebsocket：

[GitHub - psygames/UnityWebSocket: :whale: The Best Unity WebSocket Plugin for All Platforms.](https://github.com/psygames/UnityWebSocket)

按照教程添加并补充代码

**（3）核心代码**

- **多源故障诊断融合**

```python
def fuse_diagnosis_results(self, basic: dict, llm: dict) -> dict:
    """融合规则引擎与大模型的诊断结果"""
    # 若大模型解析失败，降级使用规则诊断
    if "error" in llm:
        return {
            "equipment_status": basic["status"],
            "severity": max([anom["severity"] for anom in basic["anomalies"]], default=0),
            "repair_priority": "高" if basic["status"] == "故障" else "中",
            "diagnosis_details": "基于规则的初步诊断",
            "recommended_actions": ["检查传感器", "人工复核"]
        }
    
    # 成功时融合：用规则补充大模型可能缺失的严重度
    final = llm.copy()
    if "severity" not in final or final["severity"] == 0:
        final["severity"] = max([anom["severity"] for anom in basic["anomalies"]], default=0)
    return final
```

当大模型输出异常时，自动切换至可靠规则系统，保障系统鲁棒性。且优先使用大模型语义理解能力，同时用规则数据补全缺失数值

- **无人机调度与故障显示**

```C#
private GameObject GetNearestDrone(Vector3 targetPosition)
{
    // 从vehicleMap中筛选出未被使用的无人机
    var availableDrones = vehicleMap
        .Where(pair => pair.Key.Contains("无人机") && pair.Value != null)
        .Select(pair => pair.Value)
        .Where(drone => !usedDrones.Contains(drone)) // 关键：排除已占用的无人机
        .OrderBy(drone => Vector3.Distance(drone.transform.position, targetPosition))
        .ToList();

    if (availableDrones.Count == 0)
    {
        Debug.Log("没有可用的空闲无人机");
        return null;
    }

    GameObject nearestDrone = availableDrones.First();
    usedDrones.Add(nearestDrone); // 标记为已使用
    return nearestDrone;
}

// 当收到AI诊断结果时，显示红色报警图标
private void ShowWarningEffect(Vector3 position, float severity)
{
    if (warningIconPrefab == null) return;

    GameObject icon = Instantiate(warningIconPrefab, position + Vector3.up * 2, Quaternion.identity);
    icon.transform.localScale *= Mathf.Lerp(0.5f, 1.5f, severity); // 严重度越高图标越大

    // 颜色随严重度变化：绿 -> 黄 -> 红
    SpriteRenderer renderer = icon.GetComponent<SpriteRenderer>();
    if (renderer != null)
        renderer.color = severity > 0.7f ? Color.red : severity > 0.3f ? Color.yellow : Color.green;

    Destroy(icon, 100f); // 持续显示100秒
}
```

使用 LINQ 筛选并排序可用无人机，实现高效的资源分配。通过 `usedDrones` 集合避免多任务抢占同一设备。

### 4.完整项目地址

Github仓库：

[ysy0804/Qwen-OpenVINO-Driven-Intelligent-Coal-Mine-Inspection-Cognitive-Digital-Twin-System at unity](https://github.com/ysy0804/Qwen-OpenVINO-Driven-Intelligent-Coal-Mine-Inspection-Cognitive-Digital-Twin-System/tree/unity)

**！！！注意：服务端代码中不包含打包的unity模型资源，所占存储太大，无法推送至仓库**

![](/img/15.png)





