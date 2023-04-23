from django.urls import path

from chat.consumers.connect_consumer import ConnectConsumer

urlpatterns = [
    path("ws/connect/", ConnectConsumer.as_asgi(), name="connect_consumer"),
]
