from django.urls import path

from chat.consumers.chat_consumer import P2PChatConsumer
from chat.consumers.connect_consumer import ConnectConsumer
from chat.consumers.scan_consumer import ScanConnectConsumer

websocket_urlpatterns = [
    path("ws/connect/", ConnectConsumer.as_asgi(), name="connect_consumer"),
    path(
        "ws/scan/connect/<uuid:did>/",
        ScanConnectConsumer.as_asgi(),
        name="scan_to_connect",
    ),
    path("ws/chat/p2p/", P2PChatConsumer.as_asgi(), name="chat_p2p_consumer"),
]
