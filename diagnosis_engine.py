import json
import re
from model_manager import ModelManager
import numpy as np
import pandas as pd
from datetime import datetime
import random
from reportlab.lib.pagesizes import letter  # 新增：PDF生成库
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle  # 新增
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # 新增
from reportlab.lib import colors  # 新增
from reportlab.lib.units import inch  # 新增
import os  # 新增：文件操作
# 新增：中文字体支持
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from fpdf import FPDF


class DiagnosisEngine:
    def __init__(self):
        self.model_manager = ModelManager()
        self.pipe = self.model_manager.initialize_pipeline()
        self.equipment_knowledge = self.load_equipment_knowledge()

    def load_equipment_knowledge(self):
        """加载设备知识库（按检查目标+检查项分级）"""
        return {
            "提升机楼": {
                "油路检查": {
                    "normal_ranges": {
                        "Residual_Pressure": (0.1, 0.8),
                        "Temperature": (30, 60),
                        "Pressure": (6.0, 8.0),
                        "Level": (0.33, 0.6)
                    },
                    "common_faults": [
                        "油管泄漏",
                        "油泵压力不足",
                        "油温异常升高"
                    ],
                    "severity_levels": {
                        "Residual_Pressure": {"warning": (0.05, 0.1), "critical": (0, 0.05)},
                        "Temperature": {"warning": (60, 70), "critical": (70, 100)}
                    }
                },
                "电控系统检查": {
                    "normal_ranges": {
                        "Temperature": (18, 25),
                        "Humidity": (0.4, 0.6)
                    },
                    "common_faults": [
                        "电路短路",
                        "控制器故障",
                        "散热不良"
                    ],
                    "severity_levels": {
                        "Humidity": {"warning": (0.6, 0.7), "critical": (0.7, 1.0)}
                    }
                }
            },
            "1号仓库": {
                "排水检查": {
                    "normal_ranges": {
                        "Residual_Water_Volume": (0, 5),
                        "Drain_Outlet_Clear": (True, True)  # 期望值应为True
                    },
                    "common_faults": [
                        "排水管堵塞",
                        "水泵故障",
                        "水位传感器失灵"
                    ],
                    "severity_levels": {
                        "Residual_Water_Volume": {"warning": (5, 10), "critical": (10, float('inf'))}
                    }
                },
                "防火检查": {
                    "normal_ranges": {
                        "Fire_Extinguisher_Pressure": (1.0, 1.5),
                        "Evacuation_Pathway_Width": (1.2, 2.0),  # 标准要求最小宽度
                        "Fire_Door_Closure_Status": (True, True),  # 应常闭
                        "Fire_Hydrant_Water_Pressure": (0.5, 1.0)
                    },
                    "common_faults": [
                        "灭火器失效",
                        "安全通道堵塞",
                        "防火门损坏"
                    ],
                    "severity_levels": {
                        "Evacuation_Pathway_Width": {"warning": (0.8, 1.2), "critical": (0, 0.8)},
                        "Fire_Hydrant_Water_Pressure": {"warning": (0.3, 0.5), "critical": (0, 0.3)}
                    }
                }
            },
            "通用设备": {
                "default": {
                    "normal_ranges": {
                        "temperature": (40, 80),
                        "vibration": (0.1, 0.8),
                        "oil_pressure": (15, 30),
                        "motor_current": (70, 150),
                        "cutting_power": (80, 120)
                    },
                    "common_faults": [
                        "机械磨损",
                        "电气故障",
                        "润滑不良"
                    ]
                }
            }
        }

#     def create_diagnosis_prompt(self, sensor_data: dict, task_data: dict) -> str:
#         """构建诊断Prompt"""
#         prompt = f"""你是一个煤矿设备故障诊断专家。请根据以下传感器数据和任务信息进行故障诊断：
#
# **任务信息**：
# - 任务ID: {task_data.get('task_id', 'N/A')}
# - 目标设备: {', '.join(task_data.get('targets', []))}
# - 检查项目: {', '.join(task_data.get('inspection_items', []))}
#
# **传感器数据**：
# {json.dumps(sensor_data, indent=2)}
#
# **诊断要求**：
# 1. 分析设备状态（正常/警告/故障）
# 2. 识别可能的故障类型
# 3. 评估故障严重程度（0-100）
# 4. 给出维修建议优先级（高/中/低）
# 5. 输出结构化JSON
#
# **输出格式**：
# {{
#     "equipment_status": "正常/警告/故障",
#     "fault_type": "故障类型",
#     "severity": 0-100,
#     "location": "故障位置",
#     "repair_priority": "高/中/低",
#     "diagnosis_details": "详细诊断分析",
#     "recommended_actions": ["建议1", "建议2"]
# }}
#
# 请开始输出JSON：
# """
#         return prompt

    def parse_diagnosis(self, raw_output: str) -> dict:
        print(f"原始LLM输出: {raw_output}...")
        try:
            # 清理 markdown 和前缀
            raw_output = re.sub(r'```json\s*', '', raw_output, flags=re.IGNORECASE)
            raw_output = re.sub(r'```\s*$', '', raw_output)  # 移除结尾 ```
            # 更宽松的 JSON 提取：使用 json 库的宽容解析或多次尝试
            # 先压缩空白
            raw_output = re.sub(r'\s+', ' ', raw_output)
            # 查找可能的 JSON 起始和结束
            start = raw_output.find('{')
            end = raw_output.rfind('}') + 1
            if start != -1 and end != -1:
                json_str = raw_output[start:end].strip()
            else:
                json_str = raw_output
            print(f"清理后的JSON字符串: {json_str}...")
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            # 备选：尝试修复常见错误，如添加缺失引号
            # 这里可以添加简单修复逻辑，例如用正则替换未引号的键
            return {"error": f"JSON解析失败: {str(e)}"}
        except Exception as e:
            return {"error": f"诊断结果解析失败: {str(e)}"}

    def analyze_sensor_data(self, sensor_data: dict, task_data: dict) -> dict:
        """分析传感器数据并生成诊断报告（适配Unity新数据格式）"""
        # 第一步：基于规则的基础诊断（适配新格式）
        basic_diagnosis = self.basic_rule_based_diagnosis(sensor_data, task_data)

        # 第二步：大模型深度分析
        prompt = self.create_diagnosis_prompt(sensor_data, task_data)
        llm_output = self.pipe.generate(prompt, max_length=2048)

        print(f"大模型输出: {llm_output}")
        print('\n')

        # 第三步：解析大模型输出
        llm_diagnosis = self.parse_diagnosis(llm_output)
        print(f"大模型诊断: {llm_diagnosis}")

        # 第四步：融合诊断结果
        final_diagnosis = self.fuse_diagnosis_results(basic_diagnosis, llm_diagnosis)

        # 添加时间戳和原始数据引用
        final_diagnosis.update({
            "timestamp": datetime.now().isoformat(),
            "original_data": sensor_data  # 保留原始数据引用
        })

        # 新增：生成PDF报告
        pdf_path = self.generate_pdf_report(final_diagnosis)
        if pdf_path:
            # 可以在这里更新全局变量或session_state，但由于是引擎类，建议在调用处处理
            pass

        return final_diagnosis

    def basic_rule_based_diagnosis(self, sensor_data: dict, task_data: dict) -> dict:
        """基于规则的初步诊断（适配新格式）"""
        diagnosis = {
            "status": "正常",
            "anomalies": [],
            "target_diagnoses": []  # 新增：按目标组织的诊断结果
        }

        # 遍历每个目标
        for target_data in sensor_data.get("targets", []):
            target_name = target_data["target_name"]
            target_diagnosis = {
                "target": target_name,
                "status": "正常",
                "anomalies": []
            }

            # 遍历目标下的设备检查项
            for equipment_data in target_data.get("equipments", []):
                equipment_type = equipment_data["equipment_type"]
                check_data = equipment_data["check_data"]

                # 获取知识库配置
                config = (self.equipment_knowledge.get(target_name, {})
                            .get(equipment_type,
                                self.equipment_knowledge["通用设备"]["default"]))

                # 检查每个参数
                for param, value in check_data.items():
                    if param in ["status", "last_check_time"]:  # 跳过元数据字段
                        continue

                    if param in config["normal_ranges"]:
                        min_val, max_val = config["normal_ranges"][param]
                        is_normal = True

                        # 特殊处理布尔型参数
                        if isinstance(min_val, bool):
                            is_normal = (value == min_val)
                        else:
                            is_normal = (min_val <= value <= max_val)

                        if not is_normal:
                            severity = self.calculate_severity(
                                param, value, config.get("severity_levels", {}))

                            anomaly = {
                                "parameter": param,
                                "value": value,
                                "normal_range": [min_val, max_val],
                                "equipment": equipment_type,
                                "severity": severity,
                                "suggestion": self.get_suggestion(param, config)
                            }

                            target_diagnosis["anomalies"].append(anomaly)
                            if severity > 50:  # 严重异常影响整体状态
                                target_diagnosis["status"] = "警告"
                                if severity > 70:
                                    target_diagnosis["status"] = "故障"

                # 更新全局状态
            if target_diagnosis["status"] != "正常":
                diagnosis["status"] = target_diagnosis["status"]

            diagnosis["target_diagnoses"].append(target_diagnosis)

        return diagnosis

    def calculate_severity(self, param: str, value: float, severity_levels: dict) -> int:
        """计算异常严重程度"""
        if param not in severity_levels:
            return 30  # 默认中等严重程度

        warning_range = severity_levels[param].get("warning", ())
        critical_range = severity_levels[param].get("critical", ())

        if critical_range and not (critical_range[0] <= value <= critical_range[1]):
            return 100  # 严重故障
        elif warning_range and not (warning_range[0] <= value <= warning_range[1]):
            return 60  # 警告
        return 30  # 轻微异常

    def get_suggestion(self, param: str, config: dict) -> str:
        """获取参数异常的建议"""
        common_faults = config.get("common_faults", [])
        if common_faults:
            return f"可能原因：{random.choice(common_faults)}"
        return "请检查设备状态"

    def create_diagnosis_prompt(self, sensor_data: dict, task_data: dict) -> str:
        """构建诊断Prompt（适配新格式）"""
        # 提取关键信息
        targets_info = []
        for target in sensor_data["targets"]:
            target_info = {
                "target": target["target_name"],
                "equipments": [
                    {
                        "type": eq["equipment_type"],
                        "status": eq["check_data"].get("status", "unknown"),
                        "abnormal_params": [
                            k for k, v in eq["check_data"].items()
                            if k not in ["status", "last_check_time"] and
                                not self.is_param_normal(k, v, target["target_name"], eq["equipment_type"])
                        ]
                    }
                    for eq in target["equipments"]
                ]
            }
            targets_info.append(target_info)

        prompt = f"""你是一个煤矿设备故障诊断专家。请根据以下信息进行诊断：

**任务概览**
- 任务ID: {task_data.get('task_id', 'N/A')}
- 检查目标: {', '.join(t['target'] for t in targets_info)}

**详细检查结果**
{json.dumps(targets_info, indent=2, ensure_ascii=False)}

**诊断要求**
1. 分析各目标设备的整体状态（正常/警告/故障）
2. 识别关键异常参数及其可能原因
3. 评估系统级风险（0-100）
4. 给出维修建议（按优先级排序）

**绝对指令：只输出纯JSON，无任何其他文本！从"{"开始，到"}"结束。如果内容过多，省略次要细节。**

**输出格式**
{{
    "overall_status": "总体状态",
    "task_id": "当前任务ID"
    "target_diagnoses": [
        {{
            "target": "目标名称",
            "status": "状态",
            "critical_issues": [
                {{
                    "parameter": "参数名",
                    "abnormal_value": 当前值,
                    "normal_range": [6.0, 8.0],
                    "possible_cause": "可能原因",
                    "severity": 0-100
                    "repair_priority":["设备1", "设备2"]
                }}
            ],
            "maintenance_suggestions": ["建议1", "建议2"]
        }}
    ],
    "system_risk": 85,
    "priority_actions": ["首要行动", "次要行动"]
}}

请开始分析并直接输出JSON："""
        return prompt

    def is_param_normal(self, param: str, value, target: str, equipment: str) -> bool:
        """检查参数是否在正常范围内"""
        config = (self.equipment_knowledge.get(target, {})
                    .get(equipment,
                        self.equipment_knowledge["通用设备"]["default"]))

        if param not in config["normal_ranges"]:
            return True  # 未知参数视为正常

        min_val, max_val = config["normal_ranges"][param]

        if isinstance(min_val, bool):
            return value == min_val
        return min_val <= value <= max_val

    def fuse_diagnosis_results(self, basic: dict, llm: dict) -> dict:
        """融合基础诊断和大模型诊断结果"""
        # 如果大模型诊断失败，返回基础诊断
        if "error" in llm:
            return {
                "equipment_status": basic["status"],
                "fault_type": "未知",
                "severity": max([anom["severity"] for anom in basic["anomalies"]], default=0),
                "location": "未指定",
                "repair_priority": "高" if basic["status"] == "故障" else "中",
                "diagnosis_details": "基础诊断结果",
                "recommended_actions": ["检查传感器数据", "联系技术人员"]
            }

        # 融合逻辑
        final = llm.copy()

        # 如果大模型没有提供严重程度，使用基础诊断的最大值
        if "severity" not in final or final["severity"] == 0:
            final["severity"] = max([anom["severity"] for anom in basic["anomalies"]], default=0)

        # 添加基础诊断发现的异常
        if basic["anomalies"]:
            final["basic_anomalies"] = basic["anomalies"]

        return final

    def generate_pdf_report(self, diagnosis_result: dict, output_dir: str = "./reports/",
                            font_path: str = "./fonts/simhei.ttf"):
        """生成可读的 PDF 诊断报告并保存到本地文件夹 - 使用 fpdf2 实现，支持中文"""
        import os
        from datetime import datetime
        from fpdf import FPDF

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        # 生成文件名（带时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"诊断报告_{timestamp}.pdf"
        filepath = os.path.join(output_dir, filename)

        try:
            # 创建 FPDF 文档
            pdf = FPDF(orientation='P', unit='mm', format='A4')
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()

            # 设置全局参数
            page_width = pdf.w - 2 * pdf.l_margin  # 可用宽度
            base_font_size = 10
            line_height = base_font_size * 0.6

            # 加载中文字体
            font_loaded = False
            if os.path.exists(font_path):
                try:
                    pdf.add_font('simhei', '', font_path, uni=True)
                    pdf.set_font('simhei', size=base_font_size)
                    font_loaded = True
                    print(f"成功加载中文字体: {font_path}")
                except Exception as e:
                    print(f"字体加载失败: {e}")
                    pdf.set_font('Arial', size=base_font_size)
            else:
                pdf.set_font('Arial', size=base_font_size)
                print("警告: 未找到中文字体，使用默认字体（可能乱码）")

            # === 1. 标题部分 ===
            pdf.set_font('simhei' if font_loaded else 'Arial', '', 16)
            pdf.cell(0, 10, '巡检设备故障诊断报告', 0, 1, 'C')
            pdf.ln(5)

            # === 2. 基本信息表格 ===
            pdf.set_font('simhei' if font_loaded else 'Arial', '', base_font_size)
            pdf.cell(0, line_height, '基本信息', 0, 1)
            pdf.set_font('simhei' if font_loaded else 'Arial', size=base_font_size)

            col_width = page_width / 2.5
            row_height = line_height * 1.8
            pdf.set_fill_color(240, 240, 240)

            # 提取基本信息
            report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            task_id = diagnosis_result.get('task_id', 'N/A')
            overall_status = diagnosis_result.get('overall_status', 'N/A')
            system_risk = diagnosis_result.get('system_risk', 'N/A')
            repair_priority_summary = "高" if system_risk > 70 else "中" if system_risk > 30 else "低"  # 示例逻辑

            info_data = [
                ['报告生成时间', report_time],
                ['任务 ID', task_id],
                ['总体状态', overall_status],
                ['系统风险评分', f"{system_risk}/100"],
                ['维修优先级', repair_priority_summary]
            ]

            for row in info_data:
                pdf.cell(col_width, row_height, row[0], 1, 0, 'L', fill=True)
                pdf.cell(col_width, row_height, str(row[1]), 1, 1, 'L')
            pdf.ln(5)

            # === 3. 诊断详情（可选：摘要）===
            pdf.set_font('simhei' if font_loaded else 'Arial', '', base_font_size)
            pdf.cell(0, line_height, '诊断详情', 0, 1)
            pdf.set_font('simhei' if font_loaded else 'Arial', size=base_font_size)
            summary = f"本次诊断共检查 {len(diagnosis_result.get('target_diagnoses', []))} 个目标，发现多个异常参数，系统整体风险较高。"
            pdf.multi_cell(0, line_height, summary)
            pdf.ln(5)

            # === 4. 异常列表（按 target 分组）===
            pdf.set_font('simhei' if font_loaded else 'Arial', '', base_font_size)
            pdf.cell(0, line_height, '发现的异常', 0, 1)
            pdf.set_font('simhei' if font_loaded else 'Arial', size=base_font_size)

            target_diagnoses = diagnosis_result.get('target_diagnoses', [])
            if not target_diagnoses:
                pdf.multi_cell(0, line_height, '未发现任何诊断目标。')
            else:
                anomaly_found = False
                for target in target_diagnoses:
                    target_name = target.get('target', '未知目标')
                    status = target.get('status', 'N/A')
                    issues = target.get('critical_issues', [])

                    if not issues:
                        continue

                    # 添加目标标题
                    pdf.set_font('simhei' if font_loaded else 'Arial', 'B', base_font_size)
                    pdf.cell(0, line_height, f"▶ {target_name} ({status})", 0, 1)
                    pdf.set_font('simhei' if font_loaded else 'Arial', size=base_font_size)

                    for issue in issues:
                        anomaly_found = True
                        param = issue.get('parameter', 'N/A')
                        value = issue.get('abnormal_value', 'N/A')
                        normal_range = issue.get('normal_range', 'N/A')
                        severity = issue.get('severity', 'N/A')
                        suggestion = issue.get('possible_cause', '暂无分析')

                        # 格式化 normal_range
                        if isinstance(normal_range, (list, tuple)) and len(normal_range) == 2:
                            normal_range_str = f"[{normal_range[0]}, {normal_range[1]}]"
                        else:
                            normal_range_str = str(normal_range)

                        anomaly_text = (
                            f"参数: {param}\n"
                            f"当前值: {value} (正常范围: {normal_range_str})\n"
                            f"严重程度: {severity}/100\n"
                            f"可能原因: {suggestion}"
                        )
                        pdf.multi_cell(0, line_height, anomaly_text)
                        pdf.ln(3)
                    pdf.ln(2)

                if not anomaly_found:
                    pdf.multi_cell(0, line_height, '无异常发现。')

            pdf.ln(5)

            # === 5. 推荐行动 ===
            pdf.set_font('simhei' if font_loaded else 'Arial', '', base_font_size)
            pdf.cell(0, line_height, '推荐行动', 0, 1)
            pdf.set_font('simhei' if font_loaded else 'Arial', size=base_font_size)

            actions = diagnosis_result.get('priority_actions', [])
            if not actions:
                pdf.multi_cell(0, line_height, '无具体建议。')
            else:
                for action in actions:
                    pdf.cell(5, line_height, '•', 0, 0)
                    pdf.multi_cell(0, line_height, action.strip())
                    pdf.ln(2)

            # 输出 PDF
            pdf.output(filepath)
            print(f"PDF 报告已生成: {filepath}")
            return filepath

        except Exception as e:
            print(f"PDF 生成失败: {e}")
            return None