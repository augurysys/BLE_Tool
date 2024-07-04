# This is a sample Python script.
import asyncio
from dataclasses import dataclass
from functools import cached_property
import sys
import struct
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QLabel
)
import qasync
from bleak import BleakScanner, BleakClient
from bleak.backends.device import BLEDevice

UART_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_CHAR_UUID = "ac7bf687-7a30-4336-a6f6-b8030930854d" #"6E400002-B5A3-F393-E0A9-E50E24DCCA9E"  # for send
UART_TX_CHAR_UUID = "00002a2b-0000-1000-8000-00805f9b34fb"#"6E400003-B5A3-F393-E0A9-E50E24DCCA9E"  # for recice

UART_SAFE_SIZE = 20


@dataclass
class QBleakClient(QObject):
    device: BLEDevice

    messageChanged = pyqtSignal(bytes)
    def __post_init__(self):
        super().__init__()

    @cached_property
    def client(self) -> BleakClient:
        return BleakClient(self.device, disconnected_callback=self._handle_disconnect)

    async def start(self):
        await self.client.connect()
        await self.client.start_notify(UART_TX_CHAR_UUID, self._handle_read)

    async def stop(self):
        await self.client.disconnect()

    async def write(self, data):
        await self.client.write_gatt_char(UART_RX_CHAR_UUID, data)
        print("send:", data)
        print("send:", data.hex())





        # write_data = bytearray(struct.pack('BBH', 0, 0, 0))
        # await self.client.write_gatt_char(UART_RX_CHAR_UUID, write_data)
        # write_data = bytearray(struct.pack('=H', 2))
        # await self.client.write_gatt_char(UART_RX_CHAR_UUID, write_data)

    def _handle_disconnect(self) -> None:
        print("Device was disconnected, goodbye.")
        # cancelling all tasks effectively ends the program
        for task in asyncio.all_tasks():
            task.cancel()

    def _handle_read(self, _: int, data: bytearray) -> None:
        print("received:", data)
        self.messageChanged.emit(data)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(640, 480)

        self._client = None

        labal = QLabel("Augury Ble Tester Tool - V1" )
        scan_button = QPushButton("Scan Devices")
        self.devices_combobox = QComboBox()
        connect_button = QPushButton("Connect")
        self.message_lineedit = QLineEdit()
        send_button = QPushButton("Send Message")
        self.log_edit = QPlainTextEdit()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        lay = QVBoxLayout(central_widget)
        lay.addWidget(labal)
        lay.addWidget(scan_button)
        lay.addWidget(self.devices_combobox)
        lay.addWidget(connect_button)
        lay.addWidget(self.message_lineedit)
        lay.addWidget(send_button)
        lay.addWidget(self.log_edit)

        scan_button.clicked.connect(self.handle_scan)
        connect_button.clicked.connect(self.handle_connect)
        send_button.clicked.connect(self.handle_send)

    @cached_property
    def devices(self):
        return list()

    @property
    def current_client(self):
        return self._client

    async def build_client(self, device):
        if self._client is not None:
            await self._client.stop()
        self._client = QBleakClient(device)
        self._client.messageChanged.connect(self.handle_message_changed)
        await self._client.start()

    @qasync.asyncSlot()
    async def handle_connect(self):
        self.log_edit.appendPlainText("try connect")
        device = self.devices_combobox.currentData()
        if isinstance(device, BLEDevice):
            await self.build_client(device)
            self.log_edit.appendPlainText("connected")

    @qasync.asyncSlot()
    async def handle_scan(self):
        self.log_edit.appendPlainText("Started scanner")
        self.devices.clear()
        devices = await BleakScanner.discover()
        self.devices.extend(devices)
        self.devices_combobox.clear()
        for i, device in enumerate(self.devices):
            self.devices_combobox.insertItem(i, device.name, device)
        self.log_edit.appendPlainText("Finish scanner")

    def handle_message_changed(self, message):
        self.log_edit.appendPlainText(f"msg: {message.decode()}")

    @qasync.asyncSlot()
    async def handle_send(self):
        if self.current_client is None:
            return
        message = self.message_lineedit.text()
        if message:
            await self.current_client.write(message.encode())
            self.log_edit.appendPlainText(str(message.encode()))


def main():
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    w = MainWindow()
    w.show()
    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()