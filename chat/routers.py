from django.urls import path

from chat.consumers.connect_consumer import ConnectConsumer, ScanConnectConsumer

urlpatterns = [
    path("ws/connect/", ConnectConsumer.as_asgi(), name="connect_consumer"),
    path(
        "ws/connect/scan/<uuid:did>/",
        ScanConnectConsumer.as_asgi(),
        name="scan_to_connect",
    ),
]
