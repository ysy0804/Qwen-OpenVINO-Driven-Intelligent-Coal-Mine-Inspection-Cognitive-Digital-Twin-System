import streamlit as st
import tempfile
import os
import json
from task_parser import TaskParser
import asyncio
import websockets
import threading
import time
import queue  # 线程安全UI反馈
from diagnosis_engine import DiagnosisEngine
import streamlit.components.v1 as components  # 新增：用于嵌入HTML组件

# 自定义CSS样式
# 自定义CSS样式（添加Unity嵌入样式）
def set_custom_style():
    st.markdown("""
    <style>
        /* 主色调 - 煤矿主题 */
        :root {
            --primary-color: #2c3e50;
            --secondary-color: #3498db;
            --accent-color: #e74c3c;
            --light-bg: #f5f7fa;
            --dark-text: #2c3e50;
        }

        /* 整体页面样式 */
        .stApp {
            background-color: var(--light-bg);
            color: var(--dark-text);
        }

        /* 标题样式 */
        h1 {
            color: var(--primary-color);
            border-bottom: 2px solid var(--secondary-color);
            padding-bottom: 10px;
        }

        /* 按钮样式 */
        .stButton>button {
            border: 2px solid var(--primary-color);
            background-color: white;
            color: var(--primary-color);
            border-radius: 5px;
            padding: 8px 16px;
            transition: all 0.3s;
        }

        .stButton>button:hover {
            background-color: var(--primary-color);
            color: white;
        }

        /* 文件上传区域 */
        .stFileUploader {
            border: 2px dashed var(--secondary-color);
            border-radius: 10px;
            padding: 20px;
            background-color: rgba(52, 152, 219, 0.1);
        }

        /* 卡片样式 */
        .card {
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            padding: 15px;
            margin-bottom: 15px;
        }

        /* 列间距调整 */
        .stColumn {
            padding: 0 10px;
        }

        /* 进度条和spinner颜色 */
        .stSpinner>div>div {
            border-color: var(--secondary-color) transparent transparent transparent !important;
        }

        /* 消息框样式 */
        .stAlert {
            border-radius: 10px;
        }

        /* 标签样式 */
        .st-b7 {
            color: var(--primary-color);
            font-weight: bold;
        }

        /* 调整间距 */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }

        /* 新增：Unity嵌入样式（全高、无边框） */
        .unity-container {
            width: 100%;
            height: 80vh;
            border: none;
            overflow: hidden;
        }
    </style>
    """, unsafe_allow_html=True)




# 页面配置
st.set_page_config(
    page_title="智能煤矿巡检任务发布平台",
    page_icon="🏭",
    layout="wide"
)

# 全局
# 全局
message_queue = queue.Queue()
server_thread = None
server_running = False
# 全局变量
current_client = None
client_lock = asyncio.Lock()  # 用于协程安全访问

# 初始化解析器
@st.cache_resource
def load_parser():
    return TaskParser()

# 初始化诊断引擎
@st.cache_resource
def load_diagnosis_engine():
    return DiagnosisEngine()


def main():
    set_custom_style()

    # 新增：初始化reports文件夹
    os.makedirs("./reports/", exist_ok=True)

    # 顶部标题和简介
    st.title("🏭 智能煤矿巡检任务发布平台")
    st.markdown("""
    <div style="background: linear-gradient(135deg, #2c3e50, #3498db); padding: 20px; border-radius: 10px; color: white;">
        <h3 style="color: white; margin: 0;">高效 · 智能 · 安全的煤矿巡检解决方案</h3>
        <p style="margin: 10px 0 0 0;">上传巡检任务PDF，自动生成结构化任务指令并发送至数字孪生系统</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # 初始化session state
    if 'structured_task' not in st.session_state:
        st.session_state.structured_task = None
    if 'pdf_path' not in st.session_state:
        st.session_state.pdf_path = None

    # 主内容区域：左右分栏布局
    col_left, col_right = st.columns([1, 2], gap="medium")  # 左侧窄（控制面板），右侧宽（Unity视图）

    # 主内容区域
    with st.container():
        # 新增：独立Unity嵌入，页面加载即显示，并居中
        st.markdown("---")
        col_pad1, col_unity, col_pad2 = st.columns([0.05, 0.9, 0.05])  # 三栏：左右垫片，中间Unity（60%宽度，自动居中）
        with col_unity:
            st.subheader("🌐 数字孪生系统")
            if os.path.exists("unity_build/index.html"):
                with st.spinner("加载数字孪生程序..."):
                    # 用iframe嵌入本地HTTP服务器（居中显示）
                    components.iframe("http://localhost:8000/unity_build/index.html", height=600,
                                              scrolling=False)
                st.info("提示：点击Unity视图激活键盘控制。")
            else:
                st.error("Unity构建文件未找到！请确保 'unity_build/index.html' 存在。")
                st.info(
                    "步骤：1. Unity中Build WebGL到unity_build/。2. 运行 'python -m http.server 8000' 服务文件夹。")


        # 文件上传区域
        st.subheader("📂 上传巡检任务文件")
        uploaded_file = st.file_uploader("选择PDF文件", type=['pdf'],
                                         help="请上传包含巡检任务说明的PDF文件")

        if uploaded_file is not None:
            # 保存上传的文件
            if st.session_state.pdf_path is None:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    st.session_state.pdf_path = tmp_file.name

            tmp_path = st.session_state.pdf_path

            # 显示PDF内容
            col1, col2 = st.columns([1, 1], gap="large")

            with col1:
                st.subheader("📄 上传的PDF内容预览")
                with st.expander("查看提取的文本", expanded=True):
                    try:
                        parser = load_parser()
                        pdf_text = parser.extract_text_from_pdf(tmp_path)
                        st.text_area("提取的文本",
                                     pdf_text[:1000] + "..." if len(pdf_text) > 1000 else pdf_text,
                                     height=200,
                                     label_visibility="collapsed")
                    except Exception as e:
                        st.error(f"PDF解析错误: {e}")

            # 解析按钮
            st.markdown("---")
            st.subheader("🔍 任务解析")
            parse_col1, parse_col2 = st.columns([1, 3])
            with parse_col1:
                if st.button("🚀 解析任务", type="primary", use_container_width=True):
                    with st.spinner("AI正在解析任务内容..."):
                        try:
                            parser = load_parser()
                            st.session_state.structured_task = parser.parse_task(tmp_path)
                            st.rerun()
                        except Exception as e:
                            st.error(f"任务解析失败: {e}")

            # 如果已解析，显示任务概览（简化版：仅指标卡，移除JSON和详细信息）
            if st.session_state.structured_task is not None:
                structured_task = st.session_state.structured_task

                st.subheader("🎯 任务概览")
                display_task_overview_simplified(structured_task)  # 新增简化函数

                # 发送按钮（不变）
                st.markdown("---")
                st.subheader("📡 任务发布")
                if st.button("发布任务到数字孪生系统", type="primary", use_container_width=True):
                    send_to_unity(structured_task)
                    st.balloons()


                # 修改：将下载报告部分移到这里（主容器末尾），独立显示
    st.markdown("---")
    st.subheader("📥 下载诊断报告")
    # 检查reports文件夹中最新PDF
    reports_dir = "./reports/"
    if os.path.exists(reports_dir):
        pdf_files = [f for f in os.listdir(reports_dir) if f.endswith('.pdf')]
        if pdf_files:
            latest_pdf = max(pdf_files,
                                key=lambda f: os.path.getctime(os.path.join(reports_dir, f)))
            st.session_state.latest_report_path = os.path.join(reports_dir, latest_pdf)
            st.info(f"最新报告: {latest_pdf}")
        else:
            st.warning("暂无诊断报告可用。请先进行故障诊断。")
            st.session_state.latest_report_path = None
    else:
        st.error("报告文件夹未找到，请检查路径。")
        st.session_state.latest_report_path = None

    if st.session_state.latest_report_path and os.path.exists(st.session_state.latest_report_path):
        with open(st.session_state.latest_report_path, "rb") as file:
            btn = st.download_button(
                label="⬇️ 下载最新诊断报告",
                data=file.read(),
                file_name=os.path.basename(st.session_state.latest_report_path),
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
            if btn:
                st.success("报告下载成功！")
                # 如果无报告，按钮不显示，但警告已输出

            # 服务器消息显示
    display_server_messages()


def display_task_overview(task_data):
    """可视化显示任务概览 - 修复版本"""

    # 从实际数据结构中提取数据
    # 注意：您的数据是在task_data['data']中
    if isinstance(task_data, dict) and 'data' in task_data:
        actual_data = task_data['data']
    else:
        actual_data = task_data

    # 安全地获取数据
    task_type = actual_data.get('task_type', 'N/A')
    priority = actual_data.get('priority', 'N/A')

    # 目标数量从inspections数组获取
    inspections = actual_data.get('inspections', [])
    targets_count = len(inspections) if isinstance(inspections, list) else 0

    # 所需设备
    required_vehicles = actual_data.get('required_vehicles', [])
    vehicles_text = ', '.join(required_vehicles) if required_vehicles else 'N/A'

    # 检查项目（从所有inspections中提取）
    inspection_items = []
    if inspections:
        for inspection in inspections:
            items = inspection.get('items', [])
            if isinstance(items, list):
                inspection_items.extend(items)

    items_text = ', '.join(inspection_items) if inspection_items else '无'

    # 预计耗时
    estimated_duration = actual_data.get('estimated_duration', 'N/A')
    if estimated_duration != 'N/A':
        estimated_duration = f"{estimated_duration}分钟"

    # 特殊说明（可以使用deadline）
    special_instructions = f"截止时间: {actual_data.get('deadline', '未指定')}"

    # 顶部指标卡
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="card">
            <h3 style="color: #2c3e50; margin-top: 0;">任务类型</h3>
            <p style="font-size: 24px; font-weight: bold; color: #3498db; margin: 0;">
                {task_type}
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        # 优先级颜色逻辑
        priority_color = '#2ecc71'  # 默认绿色
        if priority == '高':
            priority_color = '#e74c3c'
        elif priority == '中':
            priority_color = '#f39c12'

        st.markdown(f"""
        <div class="card">
            <h3 style="color: #2c3e50; margin-top: 0;">优先级</h3>
            <p style="font-size: 24px; font-weight: bold; color: {priority_color}; margin: 0;">
                {priority}
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="card">
            <h3 style="color: #2c3e50; margin-top: 0;">目标数量</h3>
            <p style="font-size: 24px; font-weight: bold; color: #3498db; margin: 0;">
                {targets_count}
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="card">
            <h3 style="color: #2c3e50; margin-top: 0;">所需设备</h3>
            <p style="font-size: 24px; font-weight: bold; color: #3498db; margin: 0;">
                {vehicles_text}
            </p>
        </div>
        """, unsafe_allow_html=True)

    # 详细信息卡片
    with st.expander("📋 任务详细信息", expanded=True):
        # 显示检查目标和项目
        targets_info = ""
        if inspections:
            for i, inspection in enumerate(inspections):
                target = inspection.get('target', '未知目标')
                items = inspection.get('items', [])
                items_text = ', '.join(items) if items else '无具体项目'
                targets_info += f"<strong>{target}:</strong> {items_text}<br>"
        else:
            targets_info = "无检查目标"

        st.markdown(f"""
        <div class="card">
            <h4 style="color: #2c3e50; margin-top: 0;">检查目标及项目</h4>
            <div style="font-size: 16px; margin: 0;">
                {targets_info}
            </div>

            <h4 style="color: #2c3e50; margin-top: 15px;">预计耗时</h4>
            <p style="font-size: 16px; margin: 0;">
                {estimated_duration}
            </p>

            <h4 style="color: #2c3e50; margin-top: 15px;">特殊说明</h4>
            <p style="font-size: 16px; margin: 0;">
                {special_instructions}
            </p>

            <h4 style="color: #2c3e50; margin-top: 15px;">任务ID</h4>
            <p style="font-size: 16px; margin: 0;">
                {actual_data.get('task_id', 'N/A')}
            </p>
        </div>
        """, unsafe_allow_html=True)


async def websocket_server(websocket, path=None):
    global current_client, server_running  # 正确的global声明位置

    try:
        # ✅ 使用 websocket.request.path 获取路径
        client_path = getattr(websocket, "path", None)  # 兼容旧版本
        if client_path is None:
            # 尝试从 request 获取（适用于新版本）
            client_path = getattr(getattr(websocket, "request", None), "path", "/unknown")

        print(f"[服务器] 新连接: path={client_path}")
        message_queue.put(f"🚀 新连接从 path={client_path}")

        # ❌ 不再使用列表，直接赋值（断开旧连接）
        async with client_lock:
            if current_client is not None:
                try:
                    await current_client.close(code=1001, reason="新连接接入，旧连接关闭")
                    message_queue.put("🔁 旧客户端已断开（单客户端模式）")
                except:
                    pass
            current_client = websocket

        welcome = json.dumps({"status": "connected", "from": "PythonServer"})
        await websocket.send(welcome)
        message_queue.put("✅ 已发送欢迎消息")

        async for message in websocket:
            print(f"[服务器] 收到消息: {message}")
            data = json.loads(message)
            message_queue.put(f"收到Unity消息: {data}")

            if data.get('type') == 'register':
                response = json.dumps({"status": "registered", "msg": "欢迎Unity！"})
                await websocket.send(response)
                message_queue.put("Unity已注册")
            elif data.get('message_type') == 'diagnosis_request':
                message_queue.put("收到诊断请求，处理中...")

                # 获取诊断引擎
                diagnosis_engine = load_diagnosis_engine()

                try:
                    # 执行诊断分析
                    diagnosis_result = diagnosis_engine.analyze_sensor_data(
                        data.get('sensor_data', {}),
                        data.get('task_data', {})
                    )

                    # 构建响应
                    resp = {
                        "message_type": "diagnosis_result",
                        "data": diagnosis_result
                    }

                    await websocket.send(json.dumps(resp))
                    message_queue.put("诊断结果已发送")

                except Exception as e:
                    error_resp = {
                        "message_type": "diagnosis_error",
                        "error": str(e)
                    }
                    await websocket.send(json.dumps(error_resp))
                    message_queue.put(f"诊断失败: {e}")
            else:
                print(f"[服务器] 未处理消息: {data}")

    except websockets.exceptions.ConnectionClosed:
        print("[服务器] 连接正常关闭")
        message_queue.put("Unity连接关闭")
    except json.JSONDecodeError as e:
        print(f"[服务器] JSON解析错误: {e}")
        await websocket.close(code=1003, reason="Invalid JSON")
    except Exception as e:
        print(f"[服务器] 异常: {e}")
        message_queue.put(f"WebSocket错误: {e}")
        try:
            await websocket.close(code=1011, reason=str(e))
        except:
            pass
    finally:
        async with client_lock:
            if current_client == websocket:
                current_client = None
        message_queue.put("🔚 客户端已断开")


async def Main(port=8080):
    """主服务器协程"""
    global server_running
    server_running = True
    async with websockets.serve(websocket_server, "localhost", port):
        message_queue.put(f"🚀 WebSocket服务器启动在 ws://localhost:{port}")
        await asyncio.Future()  # 保持服务器运行（永活）

def start_websocket_server(port=8080):
    """在后台线程启动服务器"""
    global server_thread, server_running
    if server_running:
        return

    server_running = True
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(Main(port))  # 这会等待服务器关闭
    except Exception as e:
        message_queue.put(f"服务器异常退出: {e}")
    finally:
        server_running = False
        loop.close()

def send_to_unity(task_data):
    """发送任务到Unity（服务器模式）"""
    global server_thread
    port = 8080  # 统一端口
    if not server_running:
        # 启动服务器
        server_thread = threading.Thread(target=lambda: start_websocket_server(port), daemon=True)
        server_thread.start()
        st.info("🚀 启动WebSocket服务器，等待Unity连接...")
        time.sleep(20)  # 等待启动

    # 准备任务消息（广播逻辑：实际需保存clients列表，这里简化打印）
    message = {
        "data": task_data
    }

    # ✅ 在后台线程中尝试发送
    def send_sync():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(send_to_current_client(task_data))
        finally:
            loop.close()

    threading.Thread(target=send_sync, daemon=True).start()

    st.success("✅ 任务已发布，正在发送给Unity...")
    st.json(task_data)


async def send_to_current_client(message: dict):
    global current_client
    """发送消息给当前唯一客户端"""
    async with client_lock:
        client = current_client

    if client is None:
        message_queue.put("⚠️ 无客户端连接，无法发送任务")
        return False

    try:
        await client.send(json.dumps(message))
        message_queue.put("✅ 任务已成功发送给Unity客户端")
        return True
    except Exception as e:
        message_queue.put(f"❌ 发送失败: {e}")
        # 连接可能已断开
        async with client_lock:
            if current_client == client:
                current_client = None
        return False


# send_websocket_message保持不变，但移除st.info
async def send_websocket_message(data):
    """异步发送WebSocket消息"""
    uri = "ws://localhost:8080"  # Unity WebSocket服务器地址
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps(data))
        # 移除st.info，改用同步反馈

def display_server_messages():
    while not message_queue.empty():
        try:
            msg = message_queue.get_nowait()
            st.info(msg)
        except queue.Empty:
            break



# 新增：简化版任务概览函数（仅指标卡，移除JSON和详细信息expander）
def display_task_overview_simplified(task_data):
    """简化可视化显示任务概览 - 仅指标卡"""

    # 从实际数据结构中提取数据
    if isinstance(task_data, dict) and 'data' in task_data:
        actual_data = task_data['data']
    else:
        actual_data = task_data

    # 安全地获取数据（不变）
    task_type = actual_data.get('task_type', 'N/A')
    priority = actual_data.get('priority', 'N/A')
    inspections = actual_data.get('inspections', [])
    targets_count = len(inspections) if isinstance(inspections, list) else 0
    required_vehicles = actual_data.get('required_vehicles', [])
    vehicles_text = ', '.join(required_vehicles) if required_vehicles else 'N/A'
    estimated_duration = actual_data.get('estimated_duration', 'N/A')
    if estimated_duration != 'N/A':
        estimated_duration = f"{estimated_duration}分钟"

    # 顶部指标卡（不变）
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="card">
            <h3 style="color: #2c3e50; margin-top: 0;">任务类型</h3>
            <p style="font-size: 24px; font-weight: bold; color: #3498db; margin: 0;">
                {task_type}
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        # 优先级颜色逻辑（不变）
        priority_color = '#2ecc71'  # 默认绿色
        if priority == '高':
            priority_color = '#e74c3c'
        elif priority == '中':
            priority_color = '#f39c12'

        st.markdown(f"""
        <div class="card">
            <h3 style="color: #2c3e50; margin-top: 0;">优先级</h3>
            <p style="font-size: 24px; font-weight: bold; color: {priority_color}; margin: 0;">
                {priority}
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="card">
            <h3 style="color: #2c3e50; margin-top: 0;">目标数量</h3>
            <p style="font-size: 24px; font-weight: bold; color: #3498db; margin: 0;">
                {targets_count}
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="card">
            <h3 style="color: #2c3e50; margin-top: 0;">所需设备</h3>
            <p style="font-size: 24px; font-weight: bold; color: #3498db; margin: 0;">
                {vehicles_text}
            </p>
        </div>
        """, unsafe_allow_html=True)



if __name__ == "__main__":
    main()