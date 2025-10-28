import asyncio
import json
import logging
from bleak import BleakScanner, BleakClient
from bleak.exc import BleakError
import mido
from mido import Message

# 设置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MidiPortManager:
    """管理MIDI输出端口"""
    def __init__(self):
        self.output_ports = []
        self.current_port = None
        self.refresh_ports()
    
    def refresh_ports(self):
        """刷新可用的MIDI输出端口"""
        self.output_ports = mido.get_output_names()
        return self.output_ports
    
    def open_port(self, port_name):
        """打开MIDI输出端口"""
        try:
            if self.current_port:
                self.current_port.close()
            
            if port_name in self.output_ports:
                self.current_port = mido.open_output(port_name)
                logger.info(f"已打开MIDI端口: {port_name}")
                return True
            else:
                logger.error(f"MIDI端口不存在: {port_name}")
                return False
        except Exception as e:
            logger.error(f"打开MIDI端口失败: {e}")
            return False
    
    def send_message(self, message):
        """发送MIDI消息"""
        if self.current_port:
            try:
                self.current_port.send(message)
                return True
            except Exception as e:
                logger.error(f"发送MIDI消息失败: {e}")
                return False
        return False
    
    def close(self):
        """关闭MIDI端口"""
        if self.current_port:
            self.current_port.close()
            self.current_port = None

class BleMidiBridge:
    """BLE MIDI 桥接器"""
    
    # BLE MIDI服务UUID (标准MIDI over BLE)
    MIDI_SERVICE_UUID = "03b80e5a-ede8-4b33-a751-6ce34ec4c700"
    MIDI_CHARACTERISTIC_UUID = "7772e5db-3868-4112-a1a9-f2669d106bf3"
    
    def __init__(self, device_name="FP-18", midi_port_name=None, status_callback=None, activity_callback=None):
        self.device_name = device_name
        self.midi_port_name = midi_port_name
        self.status_callback = status_callback
        self.activity_callback = activity_callback
        
        self.client = None
        self.is_connected = False
        self.should_reconnect = True
        self.auto_reconnect = True
        self.scan_interval = 5
        
        self.midi_manager = MidiPortManager()
        
    def update_status(self, message):
        """更新状态信息"""
        logger.info(message)
        if self.status_callback:
            self.status_callback(message)
    
    def update_activity(self, message):
        """更新MIDI活动信息"""
        logger.info(f"MIDI活动: {message}")
        if self.activity_callback:
            self.activity_callback(message)
    
    async def connect_to_device(self):
        """尝试连接设备"""
        device = None
        max_scan_attempts = 3
        
        for attempt in range(max_scan_attempts):
            self.update_status(f"扫描设备中... (尝试 {attempt + 1}/{max_scan_attempts})")
            
            try:
                devices = await BleakScanner.discover(timeout=10.0)
                for d in devices:
                    if d.name and self.device_name.lower() in d.name.lower():
                        device = d
                        self.update_status(f"找到设备: {d.name} ({d.address})")
                        break
            except Exception as e:
                logger.error(f"扫描设备时出错: {e}")
                self.update_status(f"扫描错误: {e}")
            
            if device:
                break
            await asyncio.sleep(2)
        
        if not device:
            self.update_status(f"❌ 未找到设备: {self.device_name}")
            return None
        
        try:
            self.client = BleakClient(device.address)
            await self.client.connect()
            self.is_connected = True
            self.update_status(f"✅ 已连接: {device.name}")
            
            # 打开MIDI端口
            if self.midi_port_name:
                if not self.midi_manager.open_port(self.midi_port_name):
                    self.update_status("❌ 无法打开MIDI端口，但BLE连接已建立")
            
            return self.client
        except Exception as e:
            self.update_status(f"❌ 连接失败: {e}")
            return None
    
    def midi_data_handler(self, sender, data):
        """处理MIDI数据"""
        try:
            if len(data) < 3:
                return
                
            # 查找MIDI状态字节 (0x80-0xEF)
            midi_data = bytearray()
            for byte in data:
                if byte >= 0x80 and byte <= 0xEF:
                    if midi_data:  # 如果已经有数据，先处理之前的消息
                        self.process_midi_message(bytes(midi_data))
                    midi_data = bytearray([byte])
                elif midi_data and byte < 0x80:
                    midi_data.append(byte)
            
            if midi_data:
                self.process_midi_message(bytes(midi_data))
                
        except Exception as e:
            logger.error(f"处理MIDI数据时出错: {e}")
    
    def process_midi_message(self, data):
        """处理MIDI消息并转发"""
        try:
            if len(data) >= 1:
                message_type = data[0] & 0xF0
                
                # 创建MIDI消息
                if message_type == 0x80 and len(data) >= 3:  # Note Off
                    msg = Message('note_off', note=data[1], velocity=data[2])
                    self.midi_manager.send_message(msg)
                    self.update_activity(f"Note Off: 音符 {data[1]}")
                    
                elif message_type == 0x90 and len(data) >= 3:  # Note On
                    velocity = data[2]
                    msg = Message('note_on', note=data[1], velocity=velocity)
                    self.midi_manager.send_message(msg)
                    if velocity > 0:
                        self.update_activity(f"Note On: 音符 {data[1]} (力度: {velocity})")
                    else:
                        self.update_activity(f"Note Off: 音符 {data[1]}")  # 力度为0的Note On相当于Note Off
                    
                elif message_type == 0xB0 and len(data) >= 3:  # Control Change
                    msg = Message('control_change', control=data[1], value=data[2])
                    self.midi_manager.send_message(msg)
                    self.update_activity(f"控制改变: {data[1]} = {data[2]}")
                    
                elif message_type == 0xE0 and len(data) >= 3:  # Pitch Bend
                    value = (data[2] << 7) | data[1]
                    msg = Message('pitchwheel', pitch=value)
                    self.midi_manager.send_message(msg)
                    self.update_activity(f"弯音: {value}")
                
        except Exception as e:
            logger.error(f"处理MIDI消息时出错: {e}")
    
    async def run(self):
        """主运行循环"""
        while self.should_reconnect:
            try:
                client = await self.connect_to_device()
                if not client:
                    if self.auto_reconnect:
                        self.update_status(f"{self.scan_interval}秒后重试连接...")
                        await asyncio.sleep(self.scan_interval)
                    continue
                
                # 设置MIDI特性通知
                await client.start_notify(self.MIDI_CHARACTERISTIC_UUID, self.midi_data_handler)
                self.update_status("🎹 MIDI转发已启动，开始接收数据...")
                
                # 保持连接状态
                while self.should_reconnect and client.is_connected:
                    await asyncio.sleep(1)
                
                if client.is_connected:
                    await client.stop_notify(self.MIDI_CHARACTERISTIC_UUID)
                    await client.disconnect()
                
                self.is_connected = False
                self.update_status("⚠️ 连接已断开")
                
            except Exception as e:
                logger.error(f"运行错误: {e}")
                self.update_status(f"错误: {e}")
                self.is_connected = False
            
            if self.should_reconnect and self.auto_reconnect:
                self.update_status(f"{self.scan_interval}秒后重新连接...")
                await asyncio.sleep(self.scan_interval)
    
    def stop(self):
        """停止连接"""
        self.should_reconnect = False
        if self.client and self.client.is_connected:
            asyncio.create_task(self.client.disconnect())
        self.midi_manager.close()

async def start_ble_midi_bridge(device_name, midi_port_name, status_callback, activity_callback):
    """启动BLE MIDI桥接器"""
    bridge = BleMidiBridge(device_name, midi_port_name, status_callback, activity_callback)
    await bridge.run()