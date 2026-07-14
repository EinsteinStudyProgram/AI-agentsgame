"""
世界空间服务层
============
空间感知、路径查询、邻近检测、场景管理
"""
import math
import logging
from typing import List, Optional, Tuple
from django.db.models import Q, F
from .models import World, City, District, Scene, AgentPosition, WorldEvent

logger = logging.getLogger(__name__)


class SpatialService:
    """空间服务：四级空间的查询和感知逻辑"""

    @staticmethod
    def find_agent_scene(agent_id) -> Optional[Scene]:
        """查找 Agent 当前所在的场景"""
        try:
            pos = AgentPosition.objects.get(agent_id=agent_id)
            return pos.scene
        except AgentPosition.DoesNotExist:
            return None

    @staticmethod
    def get_nearby_agents(agent_id: str, radius: float = 10.0) -> List[dict]:
        """获取指定半径内邻近的 Agent 列表"""
        try:
            pos = AgentPosition.objects.select_related("agent").get(agent_id=agent_id)
        except AgentPosition.DoesNotExist:
            return []

        scene = pos.scene
        if not scene:
            return []

        nearby = AgentPosition.objects.filter(
            scene=scene
        ).exclude(agent_id=agent_id).select_related("agent")

        result = []
        for np in nearby:
            dx = np.pos_x - pos.pos_x
            dy = np.pos_y - pos.pos_y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance <= radius:
                result.append({
                    "agent_id": str(np.agent_id),
                    "agent_name": np.agent.name,
                    "distance": round(distance, 2),
                    "heading": np.heading,
                    "scene_id": str(scene.id),
                    "scene_name": scene.name,
                })

        return result

    @staticmethod
    def get_scenes_by_function(district_id: str, function_tag: str) -> List[Scene]:
        """按功能标签查找场景"""
        return Scene.objects.filter(
            district_id=district_id,
            function_tags__contains=function_tag
        )

    @staticmethod
    def get_scene_occupants(scene_id: str) -> List[dict]:
        """获取场景内的所有 Agent"""
        positions = AgentPosition.objects.filter(
            scene_id=scene_id
        ).select_related("agent")

        return [
            {
                "agent_id": str(p.agent_id),
                "agent_name": p.agent.name,
                "pos_x": p.pos_x,
                "pos_y": p.pos_y,
            }
            for p in positions
        ]

    @staticmethod
    def move_agent(agent_id: str, new_x: float, new_y: float,
                   scene_id: Optional[str] = None) -> bool:
        """移动 Agent 到新位置"""
        try:
            pos = AgentPosition.objects.get(agent_id=agent_id)

            if pos.scene and (scene_id and str(pos.scene_id) != scene_id):
                Scene.objects.filter(id=pos.scene_id).update(
                    current_occupancy=F("current_occupancy") - 1
                )

            pos.pos_x = new_x
            pos.pos_y = new_y
            if scene_id:
                pos.scene_id = scene_id
                Scene.objects.filter(id=scene_id).update(
                    current_occupancy=F("current_occupancy") + 1
                )

            pos.save(update_fields=["pos_x", "pos_y", "scene_id", "updated_at"])
            return True

        except AgentPosition.DoesNotExist:
            logger.warning(f"Agent {agent_id} has no position record")
            return False


class SceneQuery:
    """场景查询：构建空间路径和查询"""

    @staticmethod
    def build_full_path(world_id: str = None, city_id: str = None,
                        district_id: str = None, scene_id: str = None) -> str:
        """构建完整四级空间路径"""
        parts = []

        if world_id:
            world = World.objects.filter(id=world_id).first()
            parts.append(world.name if world else "?")
            if city_id:
                city = City.objects.filter(id=city_id).first()
                parts.append(city.name if city else "?")
                if district_id:
                    district = District.objects.filter(id=district_id).first()
                    parts.append(district.name if district else "?")
                    if scene_id:
                        scene = Scene.objects.filter(id=scene_id).first()
                        parts.append(scene.name if scene else "?")

        return " / ".join(parts) if parts else "未知位置"

    @staticmethod
    def find_available_scene(district_id: str, function_tag: str = None) -> Optional[Scene]:
        """查找区域内可用的场景（未满且有指定功能）"""
        query = Scene.objects.filter(district_id=district_id)
        if function_tag:
            query = query.filter(function_tags__contains=function_tag)
        return query.filter(
            current_occupancy__lt=F("max_occupancy")
        ).order_by("-max_occupancy").first()


class EventService:
    """世界事件服务"""

    @staticmethod
    def get_active_events(scene_id: str, radius: float = 10.0) -> List[WorldEvent]:
        """获取场景中的活跃事件"""
        from django.utils import timezone
        now = timezone.now()
        return WorldEvent.objects.filter(
            Q(scene_id=scene_id) | Q(radius__gte=radius),
            expires_at__isnull=True
        ) | WorldEvent.objects.filter(
            Q(scene_id=scene_id) | Q(radius__gte=radius),
            expires_at__gte=now
        )

    @staticmethod
    def create_event(scene_id: str, event_type: str,
                     description: str, data: dict = None,
                     radius: float = 10.0,
                     expires_in_hours: int = None) -> WorldEvent:
        """创建世界事件"""
        from django.utils import timezone
        import datetime
        event = WorldEvent.objects.create(
            scene_id=scene_id,
            event_type=event_type,
            description=description,
            data=data or {},
            radius=radius,
            expires_at=(
                timezone.now() + datetime.timedelta(hours=expires_in_hours)
                if expires_in_hours else None
            ),
        )
        logger.info(f"Event created: {event}")
        return event
