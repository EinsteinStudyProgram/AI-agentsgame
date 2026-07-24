"""
Agent 管理后台配置
"""
import logging
from django.contrib import admin
from django.utils.html import format_html
from .models import Agent, MBTIConfig, DailySchedule, ScheduleItem, SocialInteraction

logger = logging.getLogger(__name__)


# ============================================================
# Agent 管理
# ============================================================

@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    """Agent 后台管理
    提供列表、搜索、过滤以及自定义动作
    """
    list_display = [
        "name", "colored_mbti", "age", "status", "energy",
        "social_energy", "is_busy", "created_at",
    ]
    list_filter = ["status", "mbti_type", "is_busy", "created_at"]
    search_fields = ["name", "biography", "mbti_type"]
    ordering = ["-created_at"]
    readonly_fields = ["id", "created_at", "updated_at", "memory_count"]
    date_hierarchy = "created_at"

    # 列表每页条数
    list_per_page = 25
    list_max_show_all = 200

    # 详情页字段分组
    fieldsets = [
        ("基本信息", {
            "fields": ["id", "name", "age", "mbti_type", "biography"],
        }),
        ("状态监控", {
            "fields": ["status", "is_busy", "energy", "social_energy"],
        }),
        ("时间戳", {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
        ("统计信息", {
            "fields": ["memory_count"],
            "classes": ["collapse"],
        }),
    ]

    # 自定义列：带颜色的 MBTI
    @admin.display(description="MBTI")
    def colored_mbti(self, obj) -> str:
        color_map = {
            "INTJ": "#7B2D8E", "INTP": "#4A90D9",
            "ENTJ": "#D91A1A", "ENTP": "#E67E22",
            "INFJ": "#8E44AD", "INFP": "#2ECC71",
            "ENFJ": "#3498DB", "ENFP": "#F39C12",
            "ISTJ": "#2C3E50", "ISFJ": "#1ABC9C",
            "ESTJ": "#E74C3C", "ESFJ": "#9B59B6",
            "ISTP": "#34495E", "ISFP": "#16A085",
            "ESTP": "#C0392B", "ESFP": "#8E44AD",
        }
        color = color_map.get(obj.mbti_type, "#666666")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.mbti_type,
        )

        # 自定义动作
    def make_active(self, request, queryset):
        updated = queryset.update(status="active")
        self.message_user(request, f"已将 {updated} 个 Agent 设为活跃")
        make_active.short_description = "将选中的 Agent 设为活跃状态"  # type: ignore[attr-defined]

    def make_resting(self, request, queryset):
        updated = queryset.update(status="resting")
        self.message_user(request, f"已将 {updated} 个 Agent 设为休息")
    make_resting.short_description = "将选中的 Agent 设为休息状态"  # type: ignore[attr-defined]

    def reset_energy(self, request, queryset):
        updated = queryset.update(energy=100.0, social_energy=100.0)
        self.message_user(request, f"已重置 {updated} 个 Agent 的能量")
    reset_energy.short_description = "重置选中 Agent 的能量至满值"  # type: ignore[attr-defined]

    actions = [make_active, make_resting, reset_energy]


# ============================================================
# MBTI 配置管理
# ============================================================

@admin.register(MBTIConfig)
class MBTIConfigAdmin(admin.ModelAdmin):
    """MBTI 行为矩阵配置管理"""
    list_display = [
        "mbti_type", "core_drive", "communication_style",
        "social_initiative", "plan_adherence", "curiosity", "emotionality",
    ]
    list_filter = ["mbti_type"]
    search_fields = ["mbti_type", "core_drive", "communication_style"]
    ordering = ["mbti_type"]

    fieldsets = [
        ("基本配置", {
            "fields": ["mbti_type"],
        }),
        ("行为参数", {
            "fields": [
                "social_initiative", "plan_adherence",
                "curiosity", "emotionality", "talkativeness",
            ],
        }),
        ("风格描述", {
            "fields": ["core_drive", "communication_style", "decision_style"],
        }),
    ]


# ============================================================
# 日程管理
# ============================================================

class ScheduleItemInline(admin.TabularInline):
    """日程项内联显示"""
    model = ScheduleItem
    extra = 0
    fields = ["activity", "start_time", "end_time", "location", "status"]
    ordering = ["start_time"]
    readonly_fields = ["interruption_reason"]


@admin.register(DailySchedule)
class DailyScheduleAdmin(admin.ModelAdmin):
    """每日日程管理"""
    list_display = [
        "agent", "date", "generation_type", "item_count", "is_active", "created_at",
    ]
    list_filter = ["generation_type", "is_active", "date"]
    search_fields = ["agent__name"]
    ordering = ["-date", "agent"]
    date_hierarchy = "date"
    inlines = [ScheduleItemInline]

    @admin.display(description="日程项数")
    def item_count(self, obj) -> int:
        return obj.items.count()

    def activate_schedule(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"已激活 {updated} 个日程")
        activate_schedule.short_description = "激活选中的日程"  # type: ignore[attr-defined]

    actions = [activate_schedule]


@admin.register(ScheduleItem)
class ScheduleItemAdmin(admin.ModelAdmin):
    """日程项管理"""
    list_display = [
        "activity", "agent_name", "start_time", "end_time",
        "location", "status",
    ]
    list_filter = ["status", "start_time"]
    search_fields = ["activity", "location", "schedule__agent__name"]
    ordering = ["schedule__agent", "start_time"]

    @admin.display(description="Agent")
    def agent_name(self, obj) -> str:
        return obj.schedule.agent.name

    def mark_completed(self, request, queryset):
        updated = queryset.update(status="completed")
        self.message_user(request, f"已将 {updated} 个日程标记为已完成")
        mark_completed.short_description = "标记选中为已完成"  # type: ignore[attr-defined]

    actions = [mark_completed]


# ============================================================
# 社交交互管理
# ============================================================

@admin.register(SocialInteraction)
class SocialInteractionAdmin(admin.ModelAdmin):
    """社交交互记录管理"""
    list_display = [
        "interaction_id", "initiator", "target", "interaction_type",
        "emotional_valence", "duration_minutes", "created_at",
    ]
    list_filter = ["interaction_type", "emotional_valence", "created_at"]
    search_fields = ["initiator__name", "target__name", "content"]
    ordering = ["-created_at"]
    readonly_fields = ["id"]

    fieldsets = [
        ("交互信息", {
            "fields": ["id", "interaction_type", "content"],
        }),
        ("参与者", {
            "fields": ["initiator", "target"],
        }),
        ("情感分析", {
            "fields": ["emotional_valence"],
        }),
        ("时间", {
            "fields": ["created_at"],
            "classes": ["collapse"],
        }),
    ]

    @admin.display(description="交互 ID")
    def interaction_id(self, obj) -> str:
        return str(obj.id)[:8] + "..."