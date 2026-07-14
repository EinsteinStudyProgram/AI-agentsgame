import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)

class AgentConsumer(AsyncWebsocketConsumer):
    """Agent ?? WebSocket ???
    ????????????????
    """
    async def connect(self):
        self.agent_id = self.scope["url_route"]["kwargs"]["agent_id"]
        self.group_name = f"agent_{self.agent_id}"

        # ?? Agent ???
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        logger.info(f"Agent {self.agent_id} WebSocket connected")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info(f"Agent {self.agent_id} WebSocket disconnected")

    async def receive(self, text_data):
        """???? Godot ???"""
        try:
            data = json.loads(text_data)
            msg_type = data.get("type", "")

            if msg_type == "position_update":
                # Agent ????
                await self.handle_position_update(data)
            elif msg_type == "proximity_detected":
                # ????? Agent ??
                await self.handle_proximity(data)
            elif msg_type == "chat_input":
                # ??????
                await self.handle_chat(data)
            else:
                await self.send(text_data=json.dumps({
                    "error": f"Unknown message type: {msg_type}"
                }))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"error": "Invalid JSON"}))

    async def handle_position_update(self, data):
        """??????"""
        from backend.apps.world.models import AgentPosition
        # TODO: ?? Agent ??
        pass

    async def handle_proximity(self, data):
        """??????"""
        # TODO: ??????
        pass

    async def handle_chat(self, data):
        """????"""
        # TODO: ?? LLM ????
        pass

    # ? Django ????????
    async def agent_state_update(self, event):
        """?? Agent ????"""
        await self.send(text_data=json.dumps(event["data"]))

    async def agent_dialogue(self, event):
        """????????"""
        await self.send(text_data=json.dumps({
            "type": "dialogue",
            "content": event["content"],
            "finished": event.get("finished", False)
        }))


class GameConsumer(AsyncWebsocketConsumer):
    """?????? WebSocket ????God Mode ???"""
    async def connect(self):
        self.game_id = self.scope["url_route"]["kwargs"]["game_id"]
        self.group_name = f"game_{self.game_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info(f"Game {self.game_id} WebSocket connected")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        # ????????
        await self.channel_layer.group_send(
            self.group_name,
            {"type": "game.broadcast", "data": data}
        )

    async def game_broadcast(self, event):
        await self.send(text_data=json.dumps(event["data"]))
