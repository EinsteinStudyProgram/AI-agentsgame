import base64, json, os

files = {}

# ============================================================
# serializers.py content
# ============================================================
ser = """
from rest_framework import serializers
from backend.apps.agents.models import Agent, MBTIConfig
from backend.apps.world.models import Scene, AgentPosition, WorldEvent
from backend.apps.memory.models import MemoryEntry

class AgentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = [\"id\", \"name\", \"mbti_type\", \"status\", \"energy\"]

class AgentDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = \"__all__\"

class MBTIConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = MBTIConfig
        fields = \"__all__\"

class SceneListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scene
        fields = [\"id\", \"name\", \"function_tags\", \"max_occupancy\", \"current_occupancy\"]

class WorldEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorldEvent
        fields = \"__all__\"

class MemoryEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = MemoryEntry
        exclude = [\"embedding\"]

class MemorySearchSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=500)
    top_k = serializers.IntegerField(default=5, min_value=1)
    memory_type = serializers.CharField(required=False, allow_blank=True)
\"\"\"
files[\"/backend/apps/gateway/serializers.py\"] = base64.b64encode(ser.encode(\"utf-8\")).decode(\"ascii\")

print(json.dumps(files))

