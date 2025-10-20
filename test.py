import openvino as ov

core = ov.Core()
print("可用设备:", core.available_devices)
# 输出示例: ['CPU', 'GPU.0', 'NPU']