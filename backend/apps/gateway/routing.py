from django.urls import re_path
from . import consumers

# WebSocket URL patterns
# ?? ws://host/ws/agent/<agent_id>/ ?????
websocket_urlpatterns = [
    re_path(r"ws/agent/(?P<agent_id>[a-f0-9-]+)/$", consumers.AgentConsumer.as_asgi()),
    re_path(r"ws/game/(?P<game_id>[a-f0-9-]+)/$", consumers.GameConsumer.as_asgi()),
]
