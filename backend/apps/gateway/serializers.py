from rest_framework import serializers
from backend.apps.agents.models import Agent, MBTIConfig
from backend.apps.world.models import Scene, AgentPosition, WorldEvent
from backend.apps.memory.models import MemoryEntry, MemoryStream

class AgentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = ["id", "name", "mbti_type", "status", "energy", "social_energy", "created_at"]

class AgentDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = "__all__"

class AgentCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=64)
    mbti_type = serializers.ChoiceField(choices=[t.value for t in __import__("backend.apps.agents.models", fromlist=["MBTIType"]).MBTIType])
    age = serializers.IntegerField(default=25)
    biography = serializers.CharField(required=False, allow_blank=True, default="")
    world_id = serializers.UUIDField(required=False)
    scene_id = serializers.UUIDField(required=False)
    pos_x = serializers.FloatField(default=0.0)
    pos_y = serializers.FloatField(default=0.0)

class MBTIConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = MBTIConfig
        fields = "__all__"

class SceneListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scene
        fields = ["id", "name", "district_id", "function_tags", "max_occupancy", "current_occupancy"]

class SceneDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scene
        fields = "__all__"

class WorldEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorldEvent
        fields = "__all__"

class MemoryEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = MemoryEntry
        exclude = ["embedding"]

class MemorySearchSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=500)
    top_k = serializers.IntegerField(default=5)
    memory_type = serializers.CharField(required=False, allow_blank=True)

class MemoryStreamSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemoryStream
        fields = "__all__"

