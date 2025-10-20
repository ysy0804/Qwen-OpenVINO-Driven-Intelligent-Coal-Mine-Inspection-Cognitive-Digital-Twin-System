using UnityEngine;

public class Dronefly : MonoBehaviour
{
    [Header("飞行设置")]
    public float flySpeed = 5.0f;           // 飞行速度（单位/秒）
    public float rotateSpeed = 10.0f;       // 转向平滑速度
    public float liftHeight = 2.0f;         // 飞行路径最高点偏移（形成弧线）
    public bool useArcTrajectory = true;    // 是否使用弧线轨迹

    [Header("调试")]
    public Vector3 targetPosition = new Vector3(10, 5, 10); // 目标点
    public bool autoTest = false;           // 自动测试：启动后飞向目标

    private Vector3 startPos;
    private Vector3 endPos;
    private float journeyLength;
    private float startTime;
    private bool isFlying = false;
    public bool isused = false;

    void Start()
    {
    
    }


   

    void StartFlight()
    {
        FlyTo(targetPosition);
    }

    /// <summary>
    /// 外部调用：让无人机飞向目标位置
    /// </summary>
    public void FlyTo(Vector3 target)
    {
        startPos = transform.position;
        endPos = target;

        // 弧线路径：中间点抬高
        if (useArcTrajectory)
        {
            Vector3 midPoint = (startPos + endPos) * 0.5f;
            midPoint.y += liftHeight; // 抬高中间高度
            journeyLength = Vector3.Distance(startPos, midPoint) + Vector3.Distance(midPoint, endPos);
        }
        else
        {
            journeyLength = Vector3.Distance(startPos, endPos);
        }

        startTime = Time.time;
        isFlying = true;
    }

    void Update()
    {

        if (autoTest)
        {
            Invoke("StartFlight", 2f); // 延迟2秒开始
        }

        if (!isFlying) return;

        // 计算飞行进度
        float distCovered = (Time.time - startTime) * flySpeed;
        float fracJourney = distCovered / journeyLength;

        // 限制进度在 0~1
        if (fracJourney >= 1f)
        {
            transform.position = endPos;
            isFlying = false;
            return;
        }

        //使用弧线插值（贝塞尔或抛物线）
        Vector3 newPosition;
        if (useArcTrajectory)
        {
            newPosition = CalculateArcPoint(startPos, endPos, liftHeight, fracJourney);
        }
        else
        {
            newPosition = Vector3.Lerp(startPos, endPos, fracJourney);
        }

        // 更新位置
        transform.position = newPosition;

        // 面向飞行方向
        Vector3 direction = (newPosition - transform.position).normalized;
        if (direction.sqrMagnitude > 0.01f)
        {
            Quaternion targetRot = Quaternion.LookRotation(direction, Vector3.up);
            transform.rotation = Quaternion.Slerp(transform.rotation, targetRot, rotateSpeed * Time.deltaTime);
        }
    }

    /// <summary>
    /// 计算弧线路径上的点（简化版：基于抛物线插值）
    /// </summary>
    Vector3 CalculateArcPoint(Vector3 start, Vector3 end, float height, float t)
    {
        // 用二次贝塞尔曲线模拟弧线
        Vector3 controlPoint = (start + end) * 0.5f;
        controlPoint.y += height;

        Vector3 p0 = Vector3.Lerp(start, controlPoint, t);
        Vector3 p1 = Vector3.Lerp(controlPoint, end, t);
        return Vector3.Lerp(p0, p1, t);
    }

    /// <summary>
    /// 可选：鼠标点击设置目标（用于测试）
    /// </summary>
    void OnMouseUp()
    {
        Ray ray = Camera.main.ScreenPointToRay(Input.mousePosition);
        if (Physics.Raycast(ray, out RaycastHit hit))
        {
            FlyTo(hit.point);
        }
    }

    // 可视化轨迹（仅在 Scene 视图显示）
    private void OnDrawGizmos()
    {
        if (isFlying)
        {
            Gizmos.color = Color.cyan;
            Vector3 mid = (startPos + endPos) * 0.5f;
            mid.y += liftHeight;
            Gizmos.DrawLine(transform.position, mid);
            Gizmos.DrawLine(mid, endPos);
        }
    }
}