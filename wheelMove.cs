using UnityEngine;

public class wheelMove : MonoBehaviour
{
    [Header("轮子旋转设置")]
    public float rollSpeed = 100.0f;        // 滚动速度（绕指定轴）
    public float yawSpeed = 0.0f;           // Y 轴旋转速度（转向速度，可随时间变化）

    [Header("自定义旋转轴参考物体")]
    public Transform rotationAxisReference; // 提供旋转轴方向（如车轴方向）
    public Axis rollAxis = Axis.X;          // 轮子滚动绕哪个轴转（通常是 X 或 Z）

    public enum Axis
    {
        X = 0,
        Y = 1,
        Z = 2
    }

    private Vector3 originalLocalEulerAngles; // 保存初始旋转，避免漂移

    void Start()
    {
        // 保存初始姿态
        originalLocalEulerAngles = transform.localEulerAngles;
    }

    void Update()
    {

        // 
        Vector3 euler = transform.eulerAngles;
        euler.y = 30; // ← 这就是你要的“改变 rotation 的 y”

        // 重要：重新赋值时要保留原来的 X 和 Z
        transform.rotation = Quaternion.Euler(euler);

        // 
        // 所以建议使用 localRotation 或者控制好顺序
    
     }

    /// <summary>
    /// 设置轮子的 Y 轴朝向（例如转向角度）
    /// </summary>
    public void SetYawAngle(float yAngle)
    {
        Vector3 eulers = transform.localEulerAngles;
        eulers.y = yAngle;
        transform.localEulerAngles = eulers;
    }

    /// <summary>
    /// 绕 Y 轴增量旋转（用于转向动画）
    /// </summary>
    void RotateYaw(float angle)
    {
        transform.Rotate(Vector3.up, angle, Space.Self);
    }

    /// <summary>
    /// 绕指定轴滚动（自转）
    /// </summary>
    void RotateRoll(float angle)
    {
        if (rotationAxisReference == null) return;

        Vector3 axis = Vector3.right;

        switch (rollAxis)
        {
            case Axis.X:
                axis = rotationAxisReference.right;
                break;
            case Axis.Y:
                axis = rotationAxisReference.up;
                break;
            case Axis.Z:
                axis = rotationAxisReference.forward;
                break;
        }

        // 转换为世界坐标轴方向
        axis = rotationAxisReference.TransformDirection(axis);
        transform.Rotate(axis, angle, Space.World);
    }
}