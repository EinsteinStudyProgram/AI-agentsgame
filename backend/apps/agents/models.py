"""
智能体核心模块 - 数据模型
=========================
包含：Agent 模型、MBTI 配置、日程规划、社交交互记录
"""
import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class MBTIType(models.TextChoices):
    """MBTI 16型人格枚举"""
    ISTJ = "ISTJ", "内向-实感-思考-判断 (检查员)"
    ISFJ = "ISFJ", "内向-实感-情感-判断 (守护者)"
    INFJ = "INFJ", "内向-直觉-情感-判断 (提倡者)"
    INTJ = "INTJ", "内向-直觉-思考-判断 (建筑师)"
    ISTP = "ISTP", "内向-实感-思考-感知 (鉴赏家)"
    ISFP = "ISFP", "内向-实感-情感-感知 (探险家)"
    INFP = "INFP", "内向-直觉-情感-感知 (调停者)"
    INTP = "INTP", "内向-直觉-思考-感知 (逻辑学家)"
    ESTP = "ESTP", "外向-实感-思考-感知 (企业家)"
    ESFP = "ESFP", "外向-实感-情感-感知 (表演者)"
    ENFP = "ENFP", "外向-直觉-情感-感知 (竞选者)"
    ENTP = "ENTP", "外向-直觉-思考-感知 (辩论家)"
    ESTJ = "ESTJ", "外向-实感-思考-判断 (总经理)"
    ESFJ = "ESFJ", "外向-实感-情感-判断 (领事)"
    ENFJ = "ENFJ", "外向-直觉-情感-判断 (主人公)"
    ENTJ = "ENTJ", "外向-直觉-思考-判断 (指挥官)"


class Agent(models.Model):
    """智能体核心模型
    每个 Agent 是世界中独立行动的 AI 角色，
    拥有 MBTI 人格、当前状态、位置和日程规划。
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name="Agent ID")
    name = models.CharField(max_length=64, unique=True, verbose_name="角色名称")
    age = models.IntegerField(default=25, validators=[MinValueValidator(1)], verbose_name="年龄")
    biography = models.TextField(blank=True, default="", verbose_name="背景故事",
                                 help_text="角色的背景故事描述，用于初始化 System Prompt")

    mbti_type = models.CharField(
        max_length=4, choices=MBTIType.choices, default=MBTIType.INFP,
        verbose_name="MBTI 人格类型",
        help_text="16型人格，影响决策系数和行为倾向"
    )

    STATUS_CHOICES = [
        ("idle", "空闲/待命"),
        ("moving", "移动中"),
        ("interacting", "交互中/社交中"),
        ("sleeping", "睡眠中"),
        ("busy", "忙碌（执行计划）"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="idle", verbose_name="当前状态")

    energy = models.FloatField(default=100.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
                               verbose_name="精力值", help_text="0-100，影响行动意愿和决策倾向")
    social_energy = models.FloatField(default=100.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
                                      verbose_name="社交能量", help_text="社交后降低，独处时恢复")

    pos_x = models.FloatField(default=0.0, verbose_name="X 坐标")
    pos_y = models.FloatField(default=0.0, verbose_name="Y 坐标")
    pos_z = models.FloatField(default=0.0, verbose_name="Z 坐标")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "智能体"
        verbose_name_plural = "智能体"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.mbti_type})"

class MBTIConfig(models.Model):
    """MBTI行为矩阵配置
    为每种 MBTI 人格定义行为参数，包括社交倾向、
    决策系数、System Prompt 模板变量等。
    """
    mbti_type = models.CharField(max_length=4, choices=MBTIType.choices, unique=True, verbose_name="MBTI类型")
    label = models.CharField(max_length=32, verbose_name="人格标签")

    core_drive = models.CharField(max_length=256, verbose_name="核心驱动力",
                                   help_text="例如：‘追求效率与秩序’ / ‘探索新可能性’")
    communication_style = models.CharField(max_length=256, verbose_name="沟通风格",
                                            help_text="例如：‘直接了当，注重事实’ / ‘委婉含蓄，关注感受’")
    decision_style = models.CharField(max_length=256, verbose_name="决策风格",
                                       help_text="例如：‘逻辑分析优先’ / ‘以人为本’")

    social_initiative = models.FloatField(default=0.5, verbose_name="社交主动性",
                                          help_text="主动发起社交的概率系数")
    plan_adherence = models.FloatField(default=0.7, verbose_name="计划遵循度",
                                       help_text="遵守原定计划的程度，越高越不易被打断")
    curiosity = models.FloatField(default=0.5, verbose_name="好奇心",
                                   help_text="探索新事物/新交互的倾向")
    emotionality = models.FloatField(default=0.5, verbose_name="情绪化程度",
                                      help_text="决策受情绪影响的程度")
    talkativeness = models.FloatField(default=0.5, verbose_name="健谈程度",
                                       help_text="对话中生成内容的长度和丰富度")

    class Meta:
        verbose_name = "MBTI 行为矩阵"
        verbose_name_plural = "MBTI 行为矩阵"
        ordering = ["mbti_type"]

    def __str__(self):
        return f"{self.mbti_type} - {self.label}"

    def to_prompt_dict(self):
        return {
            "personality_type": self.mbti_type,
            "core_drive": self.core_drive,
            "communication_style": self.communication_style,
            "decision_style": self.decision_style,
            "social_initiative": self.social_initiative,
            "plan_adherence": self.plan_adherence,
            "curiosity": self.curiosity,
            "talkativeness": self.talkativeness,
        }

class DailySchedule(models.Model):
    """每日日程表
    存储 Agent 的基础日程计划。系统会先生成一个基础计划，
    然后 LLM 可以动态覆盖/插入新的计划项。
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="schedules", verbose_name="关联 Agent")
    date = models.DateField(verbose_name="计划日期")

    GENERATION_CHOICES = [("base", "基础日程"), ("llm_dynamic", "LLM 动态覆盖"), ("player_intervention", "玩家干预")]
    generation_type = models.CharField(max_length=20, choices=GENERATION_CHOICES, default="base", verbose_name="生成方式")

    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, verbose_name="是否生效")

    class Meta:
        verbose_name = "每日日程表"
        verbose_name_plural = "每日日程表"
        unique_together = ["agent", "date", "generation_type"]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.agent.name} - {self.date}"

class ScheduleItem(models.Model):
    """日程项：日程表中的具体条目"""
    schedule = models.ForeignKey(DailySchedule, on_delete=models.CASCADE, related_name="items", verbose_name="所属日程")
    start_time = models.TimeField(verbose_name="开始时间")
    end_time = models.TimeField(verbose_name="结束时间")
    activity = models.CharField(max_length=256, verbose_name="活动描述")
    location = models.CharField(max_length=128, blank=True, default="", verbose_name="活动地点")

    STATUS_CHOICES = [("pending", "待执行"), ("in_progress", "执行中"), ("completed", "已完成"), ("interrupted", "被打断"), ("cancelled", "已取消")]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", verbose_name="状态")

    interrupted_by = models.ForeignKey(Agent, on_delete=models.SET_NULL, null=True, blank=True, related_name="interruptions", verbose_name="打断者")
    interruption_reason = models.TextField(blank=True, default="", verbose_name="打断原因")
    order = models.IntegerField(default=0, verbose_name="排序")

    class Meta:
        verbose_name = "日程项"
        verbose_name_plural = "日程项"
        ordering = ["schedule", "start_time"]

    def __str__(self):
        return f"{self.start_time.strftime('%H:%M')} - {self.activity}"

class SocialInteraction(models.Model):
    """社交交互记录"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    initiator = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="initiated_interactions", verbose_name="发起方")
    target = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="received_interactions", verbose_name="接收方")

    INTERACTION_TYPES = [("greeting", "打招呼"), ("conversation", "对话"), ("joint_activity", "共同活动"), ("conflict", "冲突")]
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES, verbose_name="交互类型")

    trigger_context = models.TextField(blank=True, default="", verbose_name="触发上下文")
    summary = models.TextField(blank=True, default="", verbose_name="交互摘要")
    interrupted_initiator_plan = models.BooleanField(default=False, verbose_name="是否打断发起方计划")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="交互时间")
    duration_minutes = models.IntegerField(default=0, verbose_name="持续分钟数")

    class Meta:
        verbose_name = "社交交互记录"
        verbose_name_plural = "社交交互记录"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.initiator.name} -> {self.target.name}"
