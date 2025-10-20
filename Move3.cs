using UnityEngine;
using System.Collections;

public class Move3 : MonoBehaviour
{
    // 路径点（Y坐标固定为-7.1）
    private Vector3[] waypoints = new Vector3[]
    {
        new Vector3(-84.07902f, -7f, 113.5f),  // 第一段：X轴移动（无需转向）
        new Vector3(-84.07902f, -7f, 29.5f),   // 第二段：Z轴移动（左转-90°）
    };

    public float moveSpeed = 1f;             // 移动速度（米/秒）
    public float wheelRadius = -0.111879f;         // 车轮半径
    public Transform[] wheels;               // 车轮Transform数组
    public float rotationSpeed = 90f;        // 转向速度（度/秒）

    private int currentWaypoint = 0;
    private bool isRotating = false;
    private float wheelCircumference;

    public bool isstart = false;

    void Start()
    {
        wheelCircumference = 2f * Mathf.PI * wheelRadius;
        transform.position = new Vector3(-84.07902f, -7f, 113.5f);
        /*    transform.rotation = (); // 初始朝向X轴正方向*/



    }

    void Update()
    {
        if (isstart)
        {
            StartCoroutine(MoveAlongPath());
            isstart = false;
        }
    }

    IEnumerator MoveAlongPath()
    {
        while (currentWaypoint < waypoints.Length)
        {
            Vector3 startPos = transform.position;
            Vector3 endPos = waypoints[currentWaypoint];
            float distance = Vector3.Distance(startPos, endPos);
            float moveDuration = distance / moveSpeed;
            float elapsedTime = 0f;

            // 阶段转向控制
/*            if (currentWaypoint == 2) // 到达第一个点后左转-90°
            {
                yield return StartCoroutine(RotateTruck(90f));
            }
            else if (currentWaypoint == 3) // 到达第二个点后右转+90°
            {
                yield return StartCoroutine(RotateTruck(90f));
            }
            else if (currentWaypoint == 4) // 到达第二个点后右转+90°
            {
                yield return StartCoroutine(RotateTruck(90f));
            }*/
            // 直线移动
            while (elapsedTime < moveDuration)
            {
                transform.position = Vector3.Lerp(startPos, endPos, elapsedTime / moveDuration);
                /*       RotateWheels(moveSpeed, elapsedTime);*/
                elapsedTime += Time.deltaTime;
                yield return null;
            }

            transform.position = endPos;
            currentWaypoint++;
        }
    }

    // 精确角度旋转协程
    IEnumerator RotateTruck(float targetAngle)
    {
        isRotating = true;
        Quaternion startRotation = transform.rotation;
        Quaternion endRotation = startRotation * Quaternion.Euler(0, 0, targetAngle);
        float rotateDuration = Mathf.Abs(targetAngle) / rotationSpeed;
        float elapsedTime = 0f;

        while (elapsedTime < rotateDuration)
        {
            transform.rotation = Quaternion.Slerp(
                startRotation,
                endRotation,
                elapsedTime / rotateDuration
            );
            elapsedTime += Time.deltaTime;
            yield return null;
        }

        transform.rotation = endRotation;
        isRotating = false;
    }

    // 车轮旋转（保持不变）
    /*    void RotateWheels(float speed, float time)
        {
            float distanceMoved = speed * time;
            float rotationAngle = (distanceMoved / wheelCircumference) * 360f;
            foreach (Transform wheel in wheels)
            {
                wheel.localRotation = Quaternion.Euler(0, rotationAngle, 0);
            }
        }*/
}