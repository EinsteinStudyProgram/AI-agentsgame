"""
WebSocket Consumers
====================
Agent WebSocket + Game God Mode WebSocket

Topics:
  ws/agent/<agent_id>/  - Real-time agent state & communication
  ws/game/<game_id>/     - GM broadcast channel
"""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.utils import timezone

logger = logging.getLogger(__name__)


# ============================================================
# Sync helper functions (called via sync_to_async)
# ============================================================

@sync_to_async
def _get_agent_sync(agent_id):
    """Async-safe: fetch Agent by id"""
    from backend.apps.agents.models import Agent
    try:
        return Agent.objects.get(id=agent_id)
    except Agent.DoesNotExist:
        return None


@sync_to_async
def _get_agent_position_sync(agent_id):
    """Async-safe: fetch AgentPosition with scene/district/city/world"""
    from backend.apps.world.models import AgentPosition
    try:
        return AgentPosition.objects.filter(agent_id=agent_id).select_related(
            "scene__district__city__world"
        ).first()
    except Exception:
        return None


@sync_to_async
def _run_engine_sync(agent_id):
    """Async-safe: run engine iteration"""
    from backend.apps.agents.models import Agent
    from backend.apps.agents.engine import AgentEngine
    agent = Agent.objects.get(id=agent_id)
    engine = AgentEngine(agent)
    return engine.run_iteration()


@sync_to_async
def _get_schedule_sync(agent_id):
    """Async-safe: fetch current schedule with items"""
    from backend.apps.agents.services import Planner
    from backend.apps.agents.models import ScheduleItem

    schedule = Planner.get_current_schedule(agent_id)
    if not schedule:
        return None, []

    items = list(ScheduleItem.objects.filter(
        schedule=schedule
    ).order_by("start_time").values())

    return schedule, items


@sync_to_async
def _move_agent_sync(agent_id, x, y, scene_id=None):
    """Async-safe: move agent to new position"""
    from backend.apps.world.services import SpatialService
    try:
        return SpatialService.move_agent(agent_id, float(x), float(y), scene_id)
    except Exception as e:
        logger.warning(f"_move_agent_sync failed: {e}")
        return False


@sync_to_async
def _build_chat_messages(agent_id: str, message: str, target_id: str | None = None):
    """Async-safe: build messages list with ORM data (sync part)"""
    from backend.apps.agents.models import Agent
    from backend.apps.agents.services import MBTIEngine

    agent = Agent.objects.get(id=agent_id)
    system_prompt = MBTIEngine.build_system_prompt(agent)

    position_info = ""
    try:
        from backend.apps.world.models import AgentPosition
        pos = AgentPosition.objects.filter(agent=agent).select_related("scene__district").first()
        if pos and pos.scene:
            position_info = f"\n当前所在场景：{pos.scene.name}（{pos.scene.district.name}）"
    except Exception:
        pass

    schedule_info = ""
    try:
        from backend.apps.agents.services import Planner
        from backend.apps.agents.models import ScheduleItem
        sched = Planner.get_current_schedule(agent)
        if sched:
            items = ScheduleItem.objects.filter(schedule=sched, status="pending").order_by("start_time")[:3]
            if items:
                schedule_info = "\n今日计划：" + ", ".join(
                    f"{i.start_time.strftime('%H:%M')} {i.activity}" for i in items
                )
    except Exception:
        pass

    target_hint = ""
    if target_id:
        try:
            target = Agent.objects.get(id=target_id)
            target_hint = f"\n对话对象：{target.name}（{target.mbti_type} 型人格）"
        except Agent.DoesNotExist:
            pass

    messages = [
        {
            "role": "system",
            "content": (
                f"{system_prompt}\n"
                f"【当前状态】\n"
                f"精力值：{agent.energy:.0f}%\n"
                f"社交能量：{agent.social_energy:.0f}%\n"
                f"当前状态：{agent.status}{position_info}{schedule_info}{target_hint}\n"
                f"\n请以第一人称角色身份回复，不超过 200 字。"
            ),
        },
        {"role": "user", "content": message},
    ]
    return messages, agent.name


# ============================================================
# Agent Consumer
# ============================================================

class AgentConsumer(AsyncWebsocketConsumer):
    """Agent WebSocket 通信通道
    - 接收 Godot 客户端的位置/碰撞/聊天输入
    - 发送 Agent 状态更新、对话
    - 支持 engine 手动触发
    """

    async def connect(self):
        url_route = self.scope.get("url_route", {})
        self.agent_id = (url_route.get("kwargs") or {}).get("agent_id", "")
        if not self.agent_id:
            await self.close()
            return

        self.group_name = f"agent_{self.agent_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self._send_initial_state()
        logger.info(f"Agent {self.agent_id} WebSocket connected")

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info(f"Agent {self.agent_id} WebSocket disconnected")

    async def receive(self, text_data=None, bytes_data=None):
        """处理来自客户端的消息"""
        if text_data is None:
            return
        try:
            data = json.loads(text_data)
            msg_type = data.get("type", "")

            handlers = {
                "position_update": self._handle_position_update,
                "proximity_detected": self._handle_proximity,
                "chat_input": self._handle_chat,
                "run_engine": self._handle_run_engine,
                "get_schedule": self._handle_get_schedule,
                "get_state": self._handle_get_state,
            }

            handler = handlers.get(msg_type)
            if handler:
                await handler(data)
            else:
                await self._send_error(f"Unknown message type: {msg_type}")

        except json.JSONDecodeError:
            await self._send_error("Invalid JSON")

    # --- Initial State ---

    async def _send_initial_state(self):
        """发送 Agent 初始状态"""
        try:
            agent = await _get_agent_sync(self.agent_id)
            if not agent:
                return

            pos = await _get_agent_position_sync(self.agent_id)

            position_data = None
            if pos:
                position_data = {
                    "world": pos.world.name if pos.world else None,
                    "scene": pos.scene.name if pos.scene else None,
                    "x": pos.pos_x,
                    "y": pos.pos_y,
                }

            await self.send(text_data=json.dumps({
                "type": "initial_state",
                "agent": {
                    "id": str(agent.id),
                    "name": agent.name,
                    "mbti_type": agent.mbti_type,
                    "energy": agent.energy,
                    "social_energy": agent.social_energy,
                    "status": agent.status,
                },
                "position": position_data,
            }, default=str))
        except Exception as e:
            logger.warning(f"_send_initial_state error: {e}")

    # --- Message Handlers ---

    async def _handle_position_update(self, data):
        """更新 Agent 位置"""
        x = data.get("x", 0.0)
        y = data.get("y", 0.0)
        scene_id = data.get("scene_id")

        success = await _move_agent_sync(self.agent_id, x, y, scene_id)
        await self.send(text_data=json.dumps({
            "type": "position_updated",
            "success": success,
        }))

    async def _handle_proximity(self, data):
        """处理碰撞/靠近检测"""
        other_id = data.get("other_agent_id")
        distance = data.get("distance", 0.0)
        await self.send(text_data=json.dumps({
            "type": "proximity_event",
            "other_agent_id": other_id,
            "distance": distance,
        }))

    async def _handle_chat(self, data):
        """处理聊天输入 - 调用 LLM 生成人格化回复"""
        message = data.get("message", "")
        target_id = data.get("target_id")

        if not message:
            await self._send_error("Empty chat message")
            return

        # 先发送"typing"状态让客户端知道模型正在生成
        await self.send(text_data=json.dumps({
            "type": "chat_typing",
            "target_id": target_id,
        }))

        try:
            # 1) 构建 messages（同步 ORM，sync_to_async）
            messages, agent_name = await _build_chat_messages(
                self.agent_id, message, target_id
            )

            # 2) 调用 LLM（纯 async，在事件循环中直接执行）
            from backend.apps.agents.services import ModelRouter
            router = ModelRouter()
            try:
                reply = await router.call_llm(
                    messages, task_type="dialogue", stream=False
                )
                error = None
            except Exception as e:
                logger.error(f"LLM call failed for agent {self.agent_id}: {e}")
                reply = f"（{agent_name} 似乎陷入了沉思……）"
                error = str(e)

            await self.send(text_data=json.dumps({
                "type": "chat_response",
                "message": message,
                "target_id": target_id,
                "reply": reply,
                "llm_error": error is not None,
            }))

            if error:
                logger.warning(f"LLM fallback used for agent {self.agent_id}: {error}")

        except Exception as e:
            logger.error(f"_handle_chat error: {e}")
            await self._send_error(f"Chat failed: {e}")

    async def _handle_run_engine(self, data):
        """手动触发 Agent 行为引擎"""
        try:
            result = await _run_engine_sync(self.agent_id)

            await self.send(text_data=json.dumps({
                "type": "engine_result",
                "loop": result.get("loop", 0),
                "perception": result.get("perception"),
                "plan": result.get("plan"),
                "action_result": result.get("action_result"),
                "memory_id": result.get("memory_id"),
                "error": result.get("error"),
            }, default=str))
        except Exception as e:
            logger.warning(f"_handle_run_engine error: {e}")
            await self._send_error(f"Engine run failed: {e}")

    async def _handle_get_schedule(self, data):
        """获取当前日程"""
        try:
            schedule, items = await _get_schedule_sync(self.agent_id)

            if not schedule:
                await self.send(text_data=json.dumps({
                    "type": "schedule",
                    "items": [],
                }))
                return

            await self.send(text_data=json.dumps({
                "type": "schedule",
                "schedule_id": str(schedule.id),
                "date": str(schedule.date),
                "items": items,
            }, default=str))
        except Exception as e:
            logger.warning(f"_handle_get_schedule error: {e}")
            await self._send_error(f"Get schedule failed: {e}")

    async def _handle_get_state(self, data):
        """获取当前完整状态"""
        try:
            agent = await _get_agent_sync(self.agent_id)
            if not agent:
                return
            await self.send(text_data=json.dumps({
                "type": "state",
                "agent_id": str(agent.id),
                "name": agent.name,
                "energy": agent.energy,
                "social_energy": agent.social_energy,
                "status": agent.status,
                "updated_at": str(agent.updated_at),
            }))
        except Exception as e:
            logger.warning(f"_handle_get_state error: {e}")

    async def _send_error(self, message: str):
        """发送错误消息"""
        await self.send(text_data=json.dumps({
            "type": "error",
            "message": message,
        }))

    # --- Server-to-Client push methods (via channel_layer) ---

    async def agent_state_update(self, event):
        """从 engine 推送状态更新"""
        await self.send(text_data=json.dumps(event["data"]))

    async def agent_dialogue(self, event):
        """推送对话内容"""
        await self.send(text_data=json.dumps({
            "type": "dialogue",
            "content": event["content"],
            "finished": event.get("finished", False),
        }))

    async def schedule_update(self, event):
        """日程变更推送"""
        await self.send(text_data=json.dumps({
            "type": "schedule_update",
            "data": event["data"],
        }))


# ============================================================
# Game Consumer (God Mode)
# ============================================================

class GameConsumer(AsyncWebsocketConsumer):
    """游戏上帝模式 WebSocket
    广播事件到所有订阅同一 game 的客户端
    """
    async def connect(self):
        url_route = self.scope.get("url_route", {})
        self.game_id = (url_route.get("kwargs") or {}).get("game_id", "")
        if not self.game_id:
            await self.close()
            return

        self.group_name = f"game_{self.game_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info(f"Game {self.game_id} WebSocket connected")

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            if text_data is None:
                return
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"error": "Invalid JSON"}))
            return

        await self.channel_layer.group_send(
            self.group_name,
            {"type": "game.broadcast", "data": data},
        )

    async def game_broadcast(self, event):
        await self.send(text_data=json.dumps(event["data"]))
