"""
REST API 序列化器
============
为 agents / world / memory 三大模块提供 RESTful 数据序列化
"""
import uuid
from rest_framework import serializers
from backend.apps.agents.models import Agent, MBTIConfig, DailySchedule, ScheduleItem, SocialInteraction
from backend.apps.world.models import World, City, District, Scene, AgentPosition, WorldEvent
from backend.apps.memory.models import MemoryEntry, MemoryStream


# ============================================================
# Agents 序列化器
# ============================================================

class AgentListSerializer(serializers.ModelSerializer):
    """Agent 列表（精简版）"""
    class Meta:
        model = Agent
        fields = ["id", "name", "mbti_type", "status", "energy", "social_energy", "created_at"]


class AgentDetailSerializer(serializers.ModelSerializer):
    """Agent 详情（完整版）"""
    position = serializers.SerializerMethodField()

    class Meta:
        model = Agent
        fields = "__all__"

    def get_position(self, obj) -> dict:
        pos = AgentPosition.objects.filter(agent=obj).select_related("scene__district__city__world").first()
        if not pos:
            return None
        return {
            "world": pos.world.name if pos.world else None,
            "scene": pos.scene.name if pos.scene else None,
            "x": pos.pos_x,
            "y": pos.pos_y,
            "heading": pos.heading,
        }


class AgentCreateSerializer(serializers.Serializer):
    """创建 Agent 请求"""
    name = serializers.CharField(max_length=64)
    mbti_type = serializers.CharField(max_length=4)
    age = serializers.IntegerField(default=25, min_value=1)
    biography = serializers.CharField(required=False, allow_blank=True, default="")
    world_id = serializers.UUIDField(required=False)
    scene_id = serializers.UUIDField(required=False)
    pos_x = serializers.FloatField(default=0.0)
    pos_y = serializers.FloatField(default=0.0)


class MBTIConfigSerializer(serializers.ModelSerializer):
    """MBTI 行为矩阵配置"""
    class Meta:
        model = MBTIConfig
        fields = "__all__"


class ScheduleSerializer(serializers.ModelSerializer):
    """日程表"""
    class Meta:
        model = DailySchedule
        fields = "__all__"


class ScheduleItemSerializer(serializers.ModelSerializer):
    """日程项"""
    class Meta:
        model = ScheduleItem
        fields = "__all__"


class SocialInteractionSerializer(serializers.ModelSerializer):
    """社交交互记录"""
    class Meta:
        model = SocialInteraction
        fields = "__all__"


# ============================================================
# World 序列化器
# ============================================================

class WorldSerializer(serializers.ModelSerializer):
    """世界"""
    class Meta:
        model = World
        fields = "__all__"


class CitySerializer(serializers.ModelSerializer):
    """城市"""
    class Meta:
        model = City
        fields = "__all__"


class DistrictSerializer(serializers.ModelSerializer):
    """区域"""
    class Meta:
        model = District
        fields = "__all__"


class SceneListSerializer(serializers.ModelSerializer):
    """场景列表（含当前人数）"""
    occupancy_rate = serializers.SerializerMethodField()

    class Meta:
        model = Scene
        fields = ["id", "name", "description", "district_id", "max_occupancy",
                   "current_occupancy", "occupancy_rate", "function_tags", "interactables"]

    def get_occupancy_rate(self, obj) -> float:
        if obj.max_occupancy == 0:
            return 0.0
        return round(obj.current_occupancy / obj.max_occupancy, 2)


class SceneDetailSerializer(serializers.ModelSerializer):
    """场景详情（含在场 Agent）"""
    occupants = serializers.SerializerMethodField()
    events = serializers.SerializerMethodField()
    world_path = serializers.ReadOnlyField()

    class Meta:
        model = Scene
        fields = "__all__"

    def get_occupants(self, obj) -> list:
        positions = AgentPosition.objects.filter(scene=obj).select_related("agent")
        return [
            {"agent_id": str(p.agent_id), "name": p.agent.name}
            for p in positions
        ]

    def get_events(self, obj) -> list:
        events = WorldEvent.objects.filter(scene=obj).order_by("-created_at")[:5]
        return [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "description": e.description[:100],
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ]


class WorldEventSerializer(serializers.ModelSerializer):
    """世界事件"""
    class Meta:
        model = WorldEvent
        fields = "__all__"


# ============================================================
# Memory 序列化器
# ============================================================

class MemoryEntrySerializer(serializers.ModelSerializer):
    """记忆条目"""
    age_hours = serializers.ReadOnlyField()

    class Meta:
        model = MemoryEntry
        exclude = ["embedding"]  # 不暴露向量嵌入


class MemorySearchSerializer(serializers.Serializer):
    """记忆搜索请求"""
    query = serializers.CharField(max_length=500)
    top_k = serializers.IntegerField(default=5, min_value=1, max_value=50)
    memory_type = serializers.ChoiceField(
        choices=["episodic", "semantic", "reflective", "procedural", ""],
        required=False, allow_blank=True,
    )


class MemorySearchResultSerializer(serializers.Serializer):
    """记忆搜索结果"""
    id = serializers.UUIDField()
    type = serializers.CharField()
    content = serializers.CharField()
    summary = serializers.CharField()
    importance = serializers.FloatField()
    score = serializers.FloatField()
    created_at = serializers.DateTimeField()


class MemoryStreamSerializer(serializers.ModelSerializer):
    """记忆流"""
    class Meta:
        model = MemoryStream
        fields = "__all__"