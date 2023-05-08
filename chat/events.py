from enum import Enum


class DEVICE_EVENT_TYPES(Enum):
    DEVICE_CONNECT = "device.connect"
    DEVICE_SETUP = "device.setup"


class SCAN_EVENT_TYPES(Enum):
    SCAN_NOTIFY = "scan.notify"
    SCAN_SETUP = "scan.setup"
