from enum import Enum


class CONNECT_EVENT_TYPES(Enum):
    CONNECT_USER = "connect.device"
    CONNECT_SETUP = "connect.setup"


class SCAN_EVENT_TYPES(Enum):
    SCAN_NOTIFY = "scan.notify"
