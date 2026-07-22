"""
REST API 视图集
============
为 agents / world / memory 模块提供 RESTful API 端点
"""
import logging
from typing import Optional
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404

from backend.apps.agents.models import Agent, MBTIConfig, DailySchedule, ScheduleItem
from backend.apps.world.models import World, City, District, Scene, AgentPosition, WorldEvent
from backend.apps.memory.models import MemoryEntry, MemoryStream
from backend.apps.memory.services import MemoryRetriever, MemoryManager
from backend.apps.agents.services import MBTIEngine, Planner
from .serializers import (
    AgentListSerializer, AgentDetailSerializer, AgentCreateSerializer,
    MBTIConfigSerializer, ScheduleSerializer, ScheduleItemSerializer,
    WorldSerializer, CitySerializer, DistrictSerializer,
    SceneListSerializer, SceneDetailSerializer, WorldEventSerializer,
    MemoryEntrySerializer, MemorySearchSerializer, MemoryStreamSerializer,
)

logger = logging.getLogger(__name__)


# ============================================================
# Agents API
# ============================================================

class AgentViewSet(viewsets.ModelViewSet):
    """Agent 管理 API
    GET    /api/agents/           - 列表
    POST   /api/agents/           - 创建
    GET    /api/agents/{id}/      - 详情
    PUT    /api/agents/{id}/      - 更新
    DELETE /api/agents/{id}/      - 删除
    """
    queryset = Agent.objects.all()
    permission_classes = [AllowAny]

    # type: ignore[override]
    def get_serializer_class(self):
        if self.action == "list":
            return AgentListSerializer
        if self.action == "create":
            return AgentCreateSerializer
        return AgentDetailSerializer

    # type: ignore[override]
    def perform_create(self, serializer):
        data = serializer.validated_data
        agent = Agent.objects.create(
            name=data["name"],
            mbti_type=data.get("mbti_type", "INFP"),
            age=data.get("age", 25),
            biography=data.get("biography", ""),
        )
        # 同步创建位置记录
        world_id = data.get("world_id")
        scene_id = data.get("scene_id")
        if world_id:
            AgentPosition.objects.create(
                agent=agent,
                world_id=world_id,
                scene_id=scene_id,
                pos_x=data.get("pos_x", 0),
                pos_y=data.get("pos_y", 0),
            )
        return agent

    @action(detail=True, methods=["get"])
    def system_prompt(self, request, pk=None):
        """获取 Agent 的 System Prompt"""
        agent = self.get_object()
        prompt = MBTIEngine.build_system_prompt(agent)
        return Response({"system_prompt": prompt})

    @action(detail=True, methods=["get"])
    def schedule(self, request, pk=None):
        """获取 Agent 当前日程"""
        schedule = Planner.get_current_schedule(pk)
        if not schedule:
            return Response({"items": []})
        items = ScheduleItem.objects.filter(schedule=schedule).order_by("start_time")
        return Response(ScheduleItemSerializer(items, many=True).data)

    @action(detail=True, methods=["get"])
    def nearby(self, request, pk=None):
        """获取附近的 Agent"""
        from backend.apps.world.services import SpatialService
        radius = float(request.query_params.get("radius", 10))
        nearby = SpatialService.get_nearby_agents(pk, radius)
        return Response({"nearby_agents": nearby, "radius": radius})

    @action(detail=True, methods=["post"])
    def move(self, request, pk=None):
        """移动 Agent 位置"""
        from backend.apps.world.services import SpatialService
        x = request.data.get("x", 0.0)
        y = request.data.get("y", 0.0)
        scene_id = request.data.get("scene_id")
        success = SpatialService.move_agent(pk, x, y, scene_id)
        return Response({"success": success})

    @action(detail=True, methods=["get"])
    def memories(self, request, pk=None):
        """获取 Agent 记忆（支持 type 过滤）"""
        memory_type = request.query_params.get("type")
        limit = int(request.query_params.get("limit", 10))
        qs = MemoryEntry.objects.filter(agent_id=pk, status="active")
        if memory_type:
            qs = qs.filter(memory_type=memory_type)
        memories = qs.order_by("-created_at")[:limit]
        return Response(MemoryEntrySerializer(memories, many=True).data)

    @action(detail=True, methods=["post"])
    def search_memories(self, request, pk=None):
        """语义搜索 Agent 记忆"""
        serializer = MemorySearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        retriever = MemoryRetriever()
        results = retriever.retrieve(
            agent_id=pk,
            query=serializer.validated_data["query"],
            memory_type=serializer.validated_data.get("memory_type"),
            top_k=serializer.validated_data["top_k"],
        )
        return Response({
            "results": [
                {
                    "id": str(r["memory"].id),
                    "type": r["memory"].memory_type,
                    "content": r["memory"].content[:300],
                    "summary": r["memory"].summary,
                    "importance": r["memory"].importance,
                    "score": r["score"],
                    "created_at": r["memory"].created_at,
                }
                for r in results
            ]
        })


class MBTIConfigViewSet(viewsets.ReadOnlyModelViewSet):
    """MBTI 配置查看 API"""
    queryset = MBTIConfig.objects.all()
    serializer_class = MBTIConfigSerializer
    permission_classes = [AllowAny]


# ============================================================
# World API
# ============================================================

class WorldViewSet(viewsets.ReadOnlyModelViewSet):
    """世界查看 API"""
    queryset = World.objects.filter(is_active=True)
    serializer_class = WorldSerializer
    permission_classes = [AllowAny]

    @action(detail=True, methods=["get"])
    def cities(self, request, pk=None):
        """获取世界中的城市列表"""
        cities = City.objects.filter(world_id=pk)
        return Response(CitySerializer(cities, many=True).data)


class CityViewSet(viewsets.ReadOnlyModelViewSet):
    """城市查看 API"""
    queryset = City.objects.all()
    serializer_class = CitySerializer
    permission_classes = [AllowAny]

    @action(detail=True, methods=["get"])
    def districts(self, request, pk=None):
        """获取城市中的区域列表"""
        districts = District.objects.filter(city_id=pk)
        return Response(DistrictSerializer(districts, many=True).data)


class DistrictViewSet(viewsets.ReadOnlyModelViewSet):
    """区域查看 API"""
    queryset = District.objects.all()
    serializer_class = DistrictSerializer
    permission_classes = [AllowAny]

    @action(detail=True, methods=["get"])
    def scenes(self, request, pk=None):
        """获取区域中的场景列表"""
        scenes = Scene.objects.filter(district_id=pk)
        return Response(SceneListSerializer(scenes, many=True).data)


class SceneViewSet(viewsets.ReadOnlyModelViewSet):
    """场景查看 API"""
    queryset = Scene.objects.all()
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == "list":
            return SceneListSerializer
        return SceneDetailSerializer

    @action(detail=False, methods=["get"])
    def by_function(self, request):
        """按功能标签查找场景"""
        tag = request.query_params.get("tag", "")
        district_id = request.query_params.get("district_id")
        if not tag and not district_id:
            return Response(
                {"error": "Provide tag or district_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = Scene.objects.all()
        if tag:
            qs = qs.filter(function_tags__contains=tag)
        if district_id:
            qs = qs.filter(district_id=district_id)
        return Response(SceneListSerializer(qs, many=True).data)

    @action(detail=True, methods=["get"])
    def events(self, request, pk=None):
        """获取场景事件"""
        events = WorldEvent.objects.filter(scene_id=pk).order_by("-created_at")[:20]
        return Response(WorldEventSerializer(events, many=True).data)


class WorldEventViewSet(viewsets.ModelViewSet):
    """世界事件 API"""
    queryset = WorldEvent.objects.all()
    serializer_class = WorldEventSerializer
    permission_classes = [AllowAny]


# ============================================================
# Memory API
# ============================================================

class MemoryEntryViewSet(viewsets.ReadOnlyModelViewSet):
    """记忆查看 API"""
    queryset = MemoryEntry.objects.all()
    serializer_class = MemoryEntrySerializer
    permission_classes = [AllowAny]
    filterset_fields = ["agent_id", "memory_type", "status"]

    @action(detail=False, methods=["post"])
    def search(self, request):
        """全局限量记忆搜索"""
        serializer = MemorySearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        agent_id = request.data.get("agent_id")
        if not agent_id:
            return Response({"error": "agent_id required"}, status=status.HTTP_400_BAD_REQUEST)

        retriever = MemoryRetriever()
        results = retriever.retrieve(
            agent_id=agent_id,
            query=serializer.validated_data["query"],
            memory_type=serializer.validated_data.get("memory_type"),
            top_k=serializer.validated_data["top_k"],
        )
        return Response({
            "results": [
                {
                    "id": str(r["memory"].id),
                    "type": r["memory"].memory_type,
                    "content": r["memory"].content[:300],
                    "summary": r["memory"].summary,
                    "importance": r["memory"].importance,
                    "score": r["score"],
                    "created_at": r["memory"].created_at,
                }
                for r in results
            ]
        })


class MemoryStreamViewSet(viewsets.ReadOnlyModelViewSet):
    """记忆流查看 API"""
    queryset = MemoryStream.objects.all()
    serializer_class = MemoryStreamSerializer
    permission_classes = [AllowAny]



# ============================================================
# Schedule API
# ============================================================

class DailyScheduleViewSet(viewsets.ModelViewSet):
    """日程管理 API
    GET    /api/schedules/            - 所有日程列表
    POST   /api/schedules/            - 创建日程
    GET    /api/schedules/{id}/       - 日程详情
    PUT    /api/schedules/{id}/       - 更新日程
    DELETE /api/schedules/{id}/       - 删除日程
    """
    queryset = DailySchedule.objects.all().order_by("-date")
    serializer_class = ScheduleSerializer
    permission_classes = [AllowAny]
    filterset_fields = ["agent", "date", "generation_type", "is_active"]

    @action(detail=True, methods=["get"])
    def items(self, request, pk=None):
        """获取日程的所有日程项"""
        schedule = self.get_object()
        items = ScheduleItem.objects.filter(schedule=schedule).order_by("start_time")
        return Response(ScheduleItemSerializer(items, many=True).data)

    @action(detail=True, methods=["post"])
    def generate(self, request, pk=None):
        """使用 Planner 重新生成日程"""
        schedule = self.get_object()
        from backend.apps.agents.services import Planner
        planner = Planner()
        success = planner.generate_daily_schedule(schedule.agent)
        if success:
            items = ScheduleItem.objects.filter(schedule=schedule).order_by("start_time")
            return Response(ScheduleItemSerializer(items, many=True).data)
        return Response({"error": "Schedule generation failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["post"])
    def daily(self, request):
        """获取/创建当天的日程
        POST /api/schedules/daily/
        Body: {"agent_id": "..."}
        """
        agent_id = request.data.get("agent_id")
        if not agent_id:
            return Response({"error": "agent_id required"}, status=status.HTTP_400_BAD_REQUEST)

        from django.utils import timezone
        today = timezone.localdate()
        schedule, created = DailySchedule.objects.get_or_create(
            agent_id=agent_id,
            date=today,
            defaults={"generation_type": "base", "is_active": True},
        )
        if created:
            from backend.apps.agents.services import Planner
            planner = Planner()
            planner.generate_daily_schedule(schedule.agent)

        items = ScheduleItem.objects.filter(schedule=schedule).order_by("start_time")
        return Response({
            "schedule": ScheduleSerializer(schedule).data,
            "items": ScheduleItemSerializer(items, many=True).data,
            "created": created,
        })


class ScheduleItemViewSet(viewsets.ModelViewSet):
    """日程项管理 API
    GET    /api/schedule-items/           - 所有日程项
    POST   /api/schedule-items/           - 创建日程项
    GET    /api/schedule-items/{id}/      - 日程项详情
    PUT    /api/schedule-items/{id}/      - 更新日程项
    DELETE /api/schedule-items/{id}/      - 删除日程项
    """
    queryset = ScheduleItem.objects.all().order_by("start_time")
    serializer_class = ScheduleItemSerializer
    permission_classes = [AllowAny]
    filterset_fields = ["schedule", "schedule__agent", "status", "activity"]

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """标记日程项为已完成"""
        item = self.get_object()
        item.status = "completed"
        item.save()
        return Response(ScheduleItemSerializer(item).data)

    @action(detail=False, methods=["get"])
    def current(self, request):
        """获取当前时间的所有活跃日程项"""
        agent_id = request.query_params.get("agent_id")
        if not agent_id:
            return Response({"error": "agent_id required"}, status=status.HTTP_400_BAD_REQUEST)

        from backend.apps.agents.services import Planner
        from django.utils import timezone

        now = timezone.localtime()
        schedule = Planner.get_current_schedule(agent_id)
        if not schedule:
            return Response({"items": []})

        items = ScheduleItem.objects.filter(
            schedule=schedule,
            start_time__lte=now.time(),
            end_time__gte=now.time(),
            status__in=["pending", "in_progress"],
        ).order_by("start_time")

        return Response({
            "current_time": now.strftime("%H:%M"),
            "items": ScheduleItemSerializer(items, many=True).data,
        })
