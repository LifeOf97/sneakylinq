from enum import Enum


class DEVICE_EVENT_TYPES(Enum):
    DEVICE_CONNECT = "device.connect"
    DEVICE_NOTIFY = "device.notify"
    DEVICE_SETUP = "device.setup"


class SCAN_EVENT_TYPES(Enum):
    SCAN_CONNECT = "scan.connect"
    SCAN_NOTIFY = "scan.notify"
    SCAN_SETUP = "scan.setup"


class CHAT_EVENT_TYPES(Enum):
    CHAT_SETUP = "chat.setup"
    CHAT_MESSAGE = "chat.message"
    CHAT_CONNECT = "chat.connect"
