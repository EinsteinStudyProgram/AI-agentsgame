import logging
from django.contrib import admin
from django.utils.html import format_html
from .models import Agent, MBTIConfig, DailySchedule, ScheduleItem, SocialInteraction

logger = logging.getLogger(__name__)

@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = [
        "name", "colored_mbti", "age", "status", "energy",
        "social_energy", "is_busy", "created_at",
    ]
    list_filter = ["status", "mbti_type", "is_busy"]
    search_fields = ["name", "biography", "mbti_type"]
    ordering = ["-created_at"]
    readonly_fields = ["id", "created_at", "updated_at"]
    list_per_page = 25

    @admin.display(description="MBTI")
    def colored_mbti(self, obj):
        colors = {"INTJ":"#7B2D8E","INTP":"#4A90D9","ENTJ":"#D91A1A","ENTP":"#E67E22",
                  "INFJ":"#8E44AD","INFP":"#2ECC71","ENFJ":"#3498DB","ENFP":"#F39C12",
                  "ISTJ":"#2C3E50","ISFJ":"#1ABC9C","ESTJ":"#E74C3C","ESFJ":"#9B59B6",
                  "ISTP":"#34495E","ISFP":"#16A085","ESTP":"#C0392B","ESFP":"#8E44AD"}
        c = colors.get(obj.mbti_type, "#666666")
        return format_html(f'<span style="color:{c};font-weight:bold;">{obj.mbti_type}</span>')

    @admin.action(description="????")
    def make_active(self, request, qs):
        u = qs.update(status="active")
        self.message_user(request, f"??? {u} ?")

    @admin.action(description="????")
    def make_resting(self, request, qs):
        u = qs.update(status="resting")
        self.message_user(request, f"????? {u} ?")

    @admin.action(description="????")
    def reset_energy(self, request, qs):
        u = qs.update(energy=100.0, social_energy=100.0)
        self.message_user(request, f"??? {u} ?")

    actions = [make_active, make_resting, reset_energy]


@admin.register(MBTIConfig)
class MBTIConfigAdmin(admin.ModelAdmin):
    list_display = ["mbti_type", "core_drive", "social_initiative", "plan_adherence", "curiosity"]
    search_fields = ["mbti_type", "core_drive"]
    ordering = ["mbti_type"]


@admin.register(DailySchedule)
class DailyScheduleAdmin(admin.ModelAdmin):
    list_display = ["agent", "date", "generation_type", "is_active"]
    list_filter = ["generation_type", "is_active", "date"]
    search_fields = ["agent__name"]
    ordering = ["-date"]


@admin.register(ScheduleItem)
class ScheduleItemAdmin(admin.ModelAdmin):
    list_display = ["activity", "start_time", "end_time", "status"]
    list_filter = ["status"]
    search_fields = ["activity", "location"]


@admin.register(SocialInteraction)
class SocialInteractionAdmin(admin.ModelAdmin):
    list_display = ["initiator", "target", "interaction_type", "emotional_valence", "created_at"]
    list_filter = ["interaction_type", "emotional_valence"]
    search_fields = ["initiator__name", "target__name"]
    ordering = ["-created_at"]
