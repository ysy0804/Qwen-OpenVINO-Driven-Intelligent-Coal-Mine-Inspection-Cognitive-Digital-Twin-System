import fitz  # PyMuPDF
import json
import re
from model_manager import ModelManager


class TaskParser:
    def __init__(self):
        self.model_manager = ModelManager()
        self.pipe = self.model_manager.initialize_pipeline()

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """从PDF提取文本"""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text.strip()
        except Exception as e:
            raise Exception(f"PDF解析失败: {str(e)}")

    def create_task_parsing_prompt(self, task_description: str) -> str:
        return f"""【指令】请严格按以下要求执行：
        1. 将任务描述转换为指定JSON格式
        2. 禁止输出任何解释、思考过程或额外文本
        3. 若信息缺失则留空或写"无"

        【输入】
        {task_description}

        【输出格式】
        {{
            "message_type": "task_command",
            "data": {{
                "task_id": "TASK_<自动填充3位数字>",
                "task_type": "巡检任务",
                "inspections": [
                    {{
                        "target": "提升机楼",
                        "items": ["油路", "电控系统"]
                    }},
                    {{
                        "target": "1号仓库",
                        "items": ["建筑结构"]
                    }}
                ],
                "priority": "高",
                "estimated_duration": 120,
                "required_vehicles": ["无人机", "巡检车"],
                "deadline": "<自动填充下周一9点>",
                "special_instructions": "无人机负责高空拍摄"
            }}
        }}

        【注意】必须直接输出完整JSON，不要包含```标记"""

    def _extract_json_from_text(self, text: str) -> str:
        """
        从模型输出中提取纯净的JSON字符串
        支持多种格式：
        - ```json{...}```
        - ```{...}```
        - {...}
        """
        # 1. 优先匹配 ```json ... ```
        match = re.search(r'```json\s*([\s\S]*?)\s*```', text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # 2. 匹配 ``` ... ```（任意语言）
        match = re.search(r'```\s*([\s\S]*?)\s*```', text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # 3. 尝试提取最外层的 { ... }
        # 找到第一个 { 和最后一个 }
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and start < end:
            potential_json = text[start:end+1]
            # 验证是否是合法JSON
            try:
                json.loads(potential_json)
                return potential_json
            except json.JSONDecodeError:
                pass

        # 4. 如果以上都失败，返回 None
        return None

    def parse_task(self, pdf_path: str) -> dict:
        """解析PDF任务并生成结构化数据"""
        # 1. 提取PDF文本
        pdf_text = self.extract_text_from_pdf(pdf_path)
        print(f"提取的文本: {pdf_text}...")

        # 2. 构建Prompt
        prompt = self.create_task_parsing_prompt(pdf_text)

        # 3. 使用OpenVINO GenAI推理
        try:
            result = self.pipe.generate(prompt, max_new_tokens=512)
            print(f"模型原始输出: {result}")

            # 4. ✅ 使用增强版JSON提取
            json_str = self._extract_json_from_text(result)

            if not json_str:
                raise Exception("未找到有效的JSON格式输出")

            # 5. 解析JSON
            structured_data = json.loads(json_str)
            return structured_data

        except json.JSONDecodeError as e:
            print(f"JSON解析失败，原始输出: {result}")
            raise Exception(f"JSON格式错误: {str(e)}")
        except Exception as e:
            raise Exception(f"任务解析失败: {str(e)}")