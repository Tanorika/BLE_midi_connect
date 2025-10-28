# BLE MIDI 转发器

一个通用的蓝牙BLE MIDI转发工具，可将任何支持BLE MIDI的设备的MIDI信号稳定转发到虚拟MIDI端口，解决常规软件断连问题。

## 功能特点

- 🔄 **自动扫描连接**：持续扫描并自动连接BLE MIDI设备
- 🔁 **自动重连**：连接断开后自动重新连接
- 🎹 **实时转发**：低延迟MIDI数据转发
- 🖥️ **图形界面**：直观的状态监控和配置
- 📊 **活动监控**：实时显示MIDI输入活动
- 🔧 **端口管理**：支持多种虚拟MIDI端口
- 🎯 **设备兼容**：支持所有标准BLE MIDI设备

## 兼容设备

- **电钢琴**：罗兰FP-18、雅马哈、卡西欧等支持BLE MIDI的型号
- **MIDI键盘**：任何支持蓝牙MIDI的键盘控制器
- **其他设备**：支持标准BLE MIDI协议的各类设备

## 系统要求

- Windows 10/11
- Python 3.8+
- 蓝牙4.0+ 适配器

## 安装步骤

### 1. 安装Python依赖
```bash
pip install bleak mido PyQt5 python-rtmidi
```

### 2. 安装虚拟MIDI端口（可选）
- 下载安装 [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html)
- 或使用 [MIDIberry](https://www.microsoft.com/store/productId/9NBLGGH69D85) 创建的端口

### 3. 下载项目文件
- `ble_midi_client.py` - BLE MIDI核心客户端
- `main_app.py` - 主应用程序（UI）
- `config.json` - 配置文件
- `requirements.txt` - 依赖列表

## 使用方法

1. **运行程序**：
   ```bash
   python main_app.py
   ```

2. **配置设备**：
   - 在"设备名称"中输入你的BLE MIDI设备名称（如"FP-18"、"Digital Piano"等）
   - 在MIDI输出端口中选择目标虚拟端口（如loopMIDI创建的端口）

3. **开始连接**：
   - 点击"开始连接"按钮
   - 程序将自动扫描并连接设备
   - 状态栏显示连接状态

4. **在DAW中使用**：
   - 在你的数字音频工作站（DAW）中选择对应的虚拟MIDI端口作为输入
   - 开始录制或演奏

## 配置文件说明

`config.json` 包含以下设置：
```json
{
    "device_name": "你的设备名称",
    "midi_port": "目标MIDI端口",
    "auto_reconnect": true,
    "scan_interval": 5
}
```

## 故障排除

### 常见问题

1. **找不到设备**
   - 确保设备蓝牙已开启且可被发现
   - 检查设备名称是否匹配（大小写敏感）
   - 尝试使用设备的部分名称

2. **连接后立即断开**
   - 检查蓝牙信号强度
   - 确保设备电量充足
   - 重启设备蓝牙

3. **MIDI数据不转发**
   - 确认虚拟MIDI端口已正确创建
   - 检查DAW中的MIDI输入设置
   - 查看程序中的MIDI活动监控

### 日志查看
- 程序界面底部显示详细运行日志
- 日志包含连接状态、错误信息和MIDI活动

## 技术特性

- 基于标准BLE MIDI协议（UUID: `03b80e5a-ede8-4b33-a751-6ce34ec4c700`）
- 支持所有标准MIDI消息类型（Note On/Off、Control Change、Pitch Bend等）
- 多线程架构，UI不卡顿
- 自动错误恢复机制


## 支持

如遇问题，请检查：
1. 设备是否支持标准BLE MIDI协议
2. Python依赖是否完整安装
3. 蓝牙适配器是否正常工作
```
