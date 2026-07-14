import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from backend.apps.agents.models import Agent, MBTIConfig
from backend.apps.world.models import World, City, District, Scene, AgentPosition, WorldEvent
from backend.apps.memory.models import MemoryEntry, MemoryStream
from backend.apps.memory.services import MemoryRetriever, MemoryManager
from backend.apps.agents.services import MBTIEngine, Planner
from .serializers import (
    AgentListSerializer, AgentDetailSerializer, AgentCreateSerializer,
    MBTIConfigSerializer, SceneListSerializer, SceneDetailSerializer,
    WorldEventSerializer, MemoryEntrySerializer, MemorySearchSerializer,
    MemoryStreamSerializer,
)

logger = logging.getLogger(__name__)


class AgentViewSet(viewsets.ModelViewSet):
    queryset = Agent.objects.all()
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == "list":
            return AgentListSerializer
        if self.action == "create":
            return AgentCreateSerializer
        return AgentDetailSerializer

    def perform_create(self, serializer):
        agent = Agent.objects.create(**serializer.validated_data)
        return agent

    @action(detail=True, methods=["get"])
    def system_prompt(self, request, pk=None):
        agent = self.get_object()
        prompt = MBTIEngine.build_system_prompt(agent)
        return Response({"system_prompt": prompt})

    @action(detail=True, methods=["get"])
    def schedule(self, request, pk=None):
        schedule = Planner.get_current_schedule(pk)
        if not schedule:
            return Response({"items": []})
        items = schedule.items.all().order_by("start_time")
        return Response([{"activity": i.activity, "start_time": str(i.start_time), "status": i.status} for i in items])

    @action(detail=True, methods=["get"])
    def nearby(self, request, pk=None):
        from backend.apps.world.services import SpatialService
        radius = float(request.query_params.get("radius", 10))
        nearby = SpatialService.get_nearby_agents(pk, radius)
        return Response({"nearby_agents": nearby, "radius": radius})

    @action(detail=True, methods=["post"])
    def move(self, request, pk=None):
        from backend.apps.world.services import SpatialService
        x = request.data.get("x", 0.0)
        y = request.data.get("y", 0.0)
        scene_id = request.data.get("scene_id")
        success = SpatialService.move_agent(pk, x, y, scene_id)
        return Response({"success": success})

    @action(detail=True, methods=["get"])
    def memories(self, request, pk=None):
        memory_type = request.query_params.get("type")
        limit = int(request.query_params.get("limit", 10))
        qs = MemoryEntry.objects.filter(agent_id=pk, status="active")
        if memory_type:
            qs = qs.filter(memory_type=memory_type)
        memories = qs.order_by("-created_at")[:limit]
        return Response(MemoryEntrySerializer(memories, many=True).data)

    @action(detail=True, methods=["post"])
    def search_memories(self, request, pk=None):
        serializer = MemorySearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        retriever = MemoryRetriever()
        results = retriever.retrieve(
            agent_id=pk,
            query=serializer.validated_data["query"],
            memory_type=serializer.validated_data.get("memory_type"),
            top_k=serializer.validated_data["top_k"],
        )
        return Response({"results": [
            {"id": str(r["memory"].id), "type": r["memory"].memory_type,
             "content": r["memory"].content[:300], "score": r["score"]}
            for r in results
        ]})


class MBTIConfigViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MBTIConfig.objects.all()
    serializer_class = MBTIConfigSerializer
    permission_classes = [AllowAny]


class SceneViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Scene.objects.all()
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == "list":
            return SceneListSerializer
        return SceneDetailSerializer

    @action(detail=False, methods=["get"])
    def by_function(self, request):
        tag = request.query_params.get("tag", "")
        district_id = request.query_params.get("district_id")
        qs = Scene.objects.all()
        if tag:
            qs = qs.filter(function_tags__contains=tag)
        if district_id:
            qs = qs.filter(district_id=district_id)
        return Response(SceneListSerializer(qs, many=True).data)

    @action(detail=True, methods=["get"])
    def events(self, request, pk=None):
        events = WorldEvent.objects.filter(scene_id=pk).order_by("-created_at")[:20]
        return Response(WorldEventSerializer(events, many=True).data)


class WorldEventViewSet(viewsets.ModelViewSet):
    queryset = WorldEvent.objects.all()
    serializer_class = WorldEventSerializer
    permission_classes = [AllowAny]


class MemoryEntryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MemoryEntry.objects.all()
    serializer_class = MemoryEntrySerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=["post"])
    def search(self, request):
        serializer = MemorySearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        agent_id = request.data.get("agent_id")
        if not agent_id:
            return Response({"error": "agent_id required"}, status=400)
        retriever = MemoryRetriever()
        results = retriever.retrieve(
            agent_id=agent_id,
            query=serializer.validated_data["query"],
            memory_type=serializer.validated_data.get("memory_type"),
            top_k=serializer.validated_data["top_k"],
        )
        return Response({"results": [
            {"id": str(r["memory"].id), "type": r["memory"].memory_type,
             "content": r["memory"].content[:300], "score": r["score"]}
            for r in results
        ]})


class MemoryStreamViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MemoryStream.objects.all()
    serializer_class = MemoryStreamSerializer
    permission_classes = [AllowAny]
