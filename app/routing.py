from django.urls import path
from app.consumers import EspConsumer, MonitorConsumer

websocket_urlpatterns = [
    path('ws/esp/', EspConsumer.as_asgi()),
    path('ws/monitor/', MonitorConsumer.as_asgi()),
]
