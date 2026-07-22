"""
Gateway 路由配置
============
整合 REST API 和 WebSocket 路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import viewsets

# REST API 路由器
router = DefaultRouter()

# Agents API
router.register(r"agents", viewsets.AgentViewSet, basename="agent")
router.register(r"mbti-configs", viewsets.MBTIConfigViewSet, basename="mbti-config")

# World API
router.register(r"scenes", viewsets.SceneViewSet, basename="scene")
router.register(r"events", viewsets.WorldEventViewSet, basename="world-event")

# Memory API
router.register(r"memories", viewsets.MemoryEntryViewSet, basename="memory")
router.register(r"memory-streams", viewsets.MemoryStreamViewSet, basename="memory-stream")

# Schedule API
router.register(r"schedules", viewsets.DailyScheduleViewSet, basename="schedule")
router.register(r"schedule-items", viewsets.ScheduleItemViewSet, basename="schedule-item")

urlpatterns = [
    path("api/", include(router.urls)),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
]


