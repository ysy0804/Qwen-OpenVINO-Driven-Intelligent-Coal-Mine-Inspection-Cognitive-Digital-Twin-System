import huggingface_hub as hf_hub
import openvino_genai as ov_genai
import os
from modelscope import snapshot_download
import openvino as ov

class ModelManager:
    def __init__(self, model_id: str = "OpenVINO/Qwen2.5-Coder-7B-Instruct-int4-ov"):
        self.model_id = model_id
        # 使用 ModelScope 下载模型
        self.model_path = snapshot_download(model_id)
        self.device = self.get_preferred_device()
        print(f"使用设备: {self.device}")

    def get_preferred_device(self):
        core = ov.Core()
        if "GPU" in core.available_devices:
            return "GPU"
        elif "NPU" in core.available_devices:
            return "NPU"
        else:
            return "CPU"
    def download_model(self):
        """使用ModelScope下载OpenVINO优化模型"""
        if not os.path.exists(self.model_path):
            print(f"通过ModelScope下载模型 {self.model_id}...")
            # ModelScope会自动下载到缓存目录，这里我们只需要确保路径存在
            self.model_path = snapshot_download(self.model_id)
        else:
            print("模型已存在，跳过下载")
    def initialize_pipeline(self):
        """初始化推理管道"""
        self.download_model()

        # 创建推理管道
        self.pipe = ov_genai.LLMPipeline(self.model_path, self.device)

        # 设置聊天模板（确保指令跟随能力）
        try:
            self.pipe.get_tokenizer().set_chat_template(
                self.pipe.get_tokenizer().chat_template
            )
        except:
            # 使用通用模板
            self.set_default_chat_template()

        print("模型管道初始化完成")
        return self.pipe

    def set_default_chat_template(self):
        """设置默认对话模板"""
        default_template = "{% for message in messages %}{{message['content']}}{% endfor %}"
        self.pipe.get_tokenizer().chat_template = default_template