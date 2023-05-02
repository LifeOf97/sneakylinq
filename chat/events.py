from enum import Enum


class CONNECT_EVENT_TYPES(Enum):
    CONNECT_DEVICE = "connect.device"
    CONNECT_SETUP = "connect.setup"


class SCAN_EVENT_TYPES(Enum):
    SCAN_NOTIFY = "scan.notify"
    SCAN_SETUP = "scan.setup"
