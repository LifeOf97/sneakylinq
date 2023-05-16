from django.urls import path

from chat.consumers.chat_consumer import P2PChatConsumer
from chat.consumers.connect_consumer import ConnectConsumer, ScanConnectConsumer

websocket_urlpatterns = [
    path("ws/connect/", ConnectConsumer.as_asgi(), name="connect_consumer"),
    path(
        "ws/connect/scan/<uuid:did>/",
        ScanConnectConsumer.as_asgi(),
        name="scan_to_connect",
    ),
    path("ws/chat/", P2PChatConsumer.as_asgi(), name="chat_connect"),
]
