import sys
import os
import json
import threading
import time
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QLabel, QPushButton, QTextEdit, QComboBox,
                            QCheckBox, QGroupBox)
import asyncio
from ble_midi_client import start_ble_midi_bridge, MidiPortManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.bridge_thread = None
        self.bridge_loop = None
        self.is_running = False
        self.config = self.load_config()
        self.init_ui()
        
    def load_config(self):
        """加载配置文件"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {
                "device_name": "FP-18",
                "midi_port": "loopMIDI ToSeeMusic",
                "auto_reconnect": True,
                "scan_interval": 5
            }
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("FP-18 BLE MIDI 转发器")
        self.setGeometry(100, 100, 600, 500)
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 连接控制组
        connection_group = QGroupBox("连接控制")
        connection_layout = QVBoxLayout(connection_group)
        
        # 设备设置行
        device_layout = QHBoxLayout()
        device_layout.addWidget(QLabel("设备名称:"))
        self.device_edit = QComboBox()
        self.device_edit.setEditable(True)
        self.device_edit.addItems(["FP-18", "Roland FP-18", "Digital Piano"])
        self.device_edit.setCurrentText(self.config.get("device_name", "FP-18"))
        device_layout.addWidget(self.device_edit)
        
        self.auto_reconnect_check = QCheckBox("自动重连")
        self.auto_reconnect_check.setChecked(self.config.get("auto_reconnect", True))
        device_layout.addWidget(self.auto_reconnect_check)
        
        device_layout.addStretch()
        connection_layout.addLayout(device_layout)
        
        # MIDI端口选择
        midi_layout = QHBoxLayout()
        midi_layout.addWidget(QLabel("MIDI输出端口:"))
        self.midi_port_combo = QComboBox()
        self.refresh_midi_ports()
        midi_layout.addWidget(self.midi_port_combo)
        
        self.refresh_ports_btn = QPushButton("刷新端口")
        self.refresh_ports_btn.clicked.connect(self.refresh_midi_ports)
        midi_layout.addWidget(self.refresh_ports_btn)
        connection_layout.addLayout(midi_layout)
        
        # 扫描间隔设置
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("扫描间隔(秒):"))
        self.interval_spin = QComboBox()
        self.interval_spin.addItems(["3", "5", "10", "15", "30"])
        self.interval_spin.setCurrentText(str(self.config.get("scan_interval", 5)))
        interval_layout.addWidget(self.interval_spin)
        interval_layout.addStretch()
        connection_layout.addLayout(interval_layout)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始连接")
        self.start_btn.clicked.connect(self.start_bridge)
        button_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("停止连接")
        self.stop_btn.clicked.connect(self.stop_bridge)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)
        
        connection_layout.addLayout(button_layout)
        layout.addWidget(connection_group)
        
        # 状态显示组
        status_group = QGroupBox("状态信息")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("就绪 - 点击'开始连接'启动")
        status_layout.addWidget(self.status_label)
        
        self.activity_text = QTextEdit()
        self.activity_text.setMaximumHeight(120)
        self.activity_text.setReadOnly(True)
        status_layout.addWidget(self.activity_text)
        
        layout.addWidget(status_group)
        
        # 日志组
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
        
        # 启动日志重定向
        self.setup_logging()
    
    def setup_logging(self):
        """设置日志重定向到文本框"""
        import logging
        class TextEditHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget
                self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            
            def emit(self, record):
                msg = self.format(record)
                # 使用QTimer确保线程安全
                QTimer.singleShot(0, lambda: self.append_text(msg))
            
            def append_text(self, msg):
                self.text_widget.append(msg)
                # 保持最后200行
                lines = self.text_widget.toPlainText().split('\n')
                if len(lines) > 200:
                    self.text_widget.setPlainText('\n'.join(lines[-200:]))
                # 自动滚动到底部
                cursor = self.text_widget.textCursor()
                cursor.movePosition(cursor.End)
                self.text_widget.setTextCursor(cursor)
        
        handler = TextEditHandler(self.log_text)
        logger = logging.getLogger()
        logger.addHandler(handler)
    
    def refresh_midi_ports(self):
        """刷新MIDI端口列表"""
        midi_manager = MidiPortManager()
        ports = midi_manager.refresh_ports()
        
        self.midi_port_combo.clear()
        self.midi_port_combo.addItems(ports)
        
        # 自动选择配置的端口或loopMIDI
        config_port = self.config.get("midi_port", "")
        for i, port in enumerate(ports):
            if config_port and config_port in port:
                self.midi_port_combo.setCurrentIndex(i)
                break
            elif 'loopMIDI' in port or 'ToSeeMusic' in port:
                self.midi_port_combo.setCurrentIndex(i)
                break
    
    def status_callback(self, message):
        """状态回调函数"""
        QTimer.singleShot(0, lambda: self.status_label.setText(message))
    
    def activity_callback(self, message):
        """MIDI活动回调函数"""
        timestamp = time.strftime("%H:%M:%S")
        QTimer.singleShot(0, lambda: self.activity_text.append(f"[{timestamp}] {message}"))
    
    def start_bridge(self):
        """启动BLE桥接器"""
        if self.is_running:
            return
        
        device_name = self.device_edit.currentText().strip()
        midi_port = self.midi_port_combo.currentText()
        
        if not device_name:
            self.status_label.setText("❌ 请输入设备名称")
            return
        
        if not midi_port:
            self.status_label.setText("❌ 请选择MIDI输出端口")
            return
        
        self.is_running = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # 在单独线程中运行BLE客户端
        def run_bridge():
            self.bridge_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.bridge_loop)
            
            try:
                self.bridge_loop.run_until_complete(
                    start_ble_midi_bridge(
                        device_name=device_name,
                        midi_port_name=midi_port,
                        status_callback=self.status_callback,
                        activity_callback=self.activity_callback
                    )
                )
            except Exception as e:
                self.status_callback(f"❌ 桥接器错误: {e}")
            finally:
                self.bridge_loop.close()
                QTimer.singleShot(0, self.on_bridge_stopped)
        
        self.bridge_thread = threading.Thread(target=run_bridge, daemon=True)
        self.bridge_thread.start()
        
        self.status_callback("🚀 启动BLE MIDI桥接器...")
    
    def stop_bridge(self):
        """停止BLE桥接器"""
        self.is_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_callback("⏹️ 正在停止桥接器...")
    
    def on_bridge_stopped(self):
        """桥接器停止后的回调"""
        self.is_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("已停止")
    
    def closeEvent(self, event):
        """关闭窗口事件"""
        self.stop_bridge()
        event.accept()

def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    # 检查依赖
    try:
        import bleak
        import mido
        import PyQt5
    except ImportError as e:
        print(f"缺少依赖: {e}")
        print("请安装: pip install bleak mido PyQt5 python-rtmidi")
        sys.exit(1)
    
    main()