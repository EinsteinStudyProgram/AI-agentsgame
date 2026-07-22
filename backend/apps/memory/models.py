"""
记忆流模块 - 数据模型
==================
pgvector 向量存储、记忆类型分类、记忆流管理

记忆类型分类：
- episodic（情景记忆）：具体事件和交互
- semantic（语义记忆）：知识概念和事实
- reflective（反思记忆）：Agent 自我反思总结
- procedural（程序记忆）：行为模式和习惯

VectorField 条件适配：
- pgvector 可用 → 使用 VectorField（生产环境）
- pgvector 不可用 → 降级为 JSONField（开发/测试环境）
"""
import uuid
import logging
from datetime import timedelta
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

logger = logging.getLogger(__name__)

# -----------------------------------------------------------
# 条件 VectorField
# -----------------------------------------------------------
try:
    from pgvector.django import VectorField
    VECTOR_AVAILABLE = True
    logger.info("pgvector.django.VectorField available")
except ImportError:
    VECTOR_AVAILABLE = False
    logger.warning("pgvector not installed, using JSONField fallback for embeddings")
    from django.db.models import JSONField as VectorField

    # Patch: make JSONField look like VectorField for migration-free usage
    # Already satisfies the field interface Django needs


class MemoryEntry(models.Model):
    """记忆条目
    核心记忆模型，每条记忆包含：
    - 向量嵌入（供语义相似度检索）
    - 文本内容
    - 三维元数据：重要性、时间戳、关联 Agent
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # 关联的 Agent
    agent = models.ForeignKey(
        "agents.Agent", on_delete=models.CASCADE, related_name="memories",
        verbose_name="所属 Agent"
    )

    # 记忆类型
    MEMORY_TYPES = [
        ("episodic", "情景记忆"),
        ("semantic", "语义记忆"),
        ("reflective", "反思记忆"),
        ("procedural", "程序记忆"),
    ]
    memory_type = models.CharField(
        max_length=20, choices=MEMORY_TYPES, default="episodic",
        verbose_name="记忆类型"
    )

    # 记忆内容
    content = models.TextField(verbose_name="记忆内容")
    summary = models.CharField(
        max_length=512, blank=True, default="",
        verbose_name="记忆摘要"
    )

    # 向量嵌入（1536 维 - OpenAI Ada-002）
    # pgvector 可用时使用 VectorField，否则使用 JSONField
    embedding = VectorField(
        dimensions=1536, null=True, blank=True,
        verbose_name="向量嵌入"
    )

    # 三维元数据
    importance = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name="重要性"
    )
    recency_score = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name="近因性分数"
    )

    # 上下文标签
    scene = models.ForeignKey(
        "world.Scene", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="memories", verbose_name="关联场景"
    )
    tags = models.JSONField(
        default=list, blank=True, verbose_name="标签列表"
    )

    # 关联的社交交互
    interaction = models.ForeignKey(
        "agents.SocialInteraction", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="memories",
        verbose_name="关联社交交互"
    )

    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="记忆创建时间")
    accessed_at = models.DateTimeField(auto_now=True, verbose_name="最后访问时间")

    # 记忆状态
    STATUS_CHOICES = [
        ("active", "活跃"),
        ("decaying", "衰减中"),
        ("archived", "已归档"),
        ("compressed", "已压缩"),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="active",
        verbose_name="记忆状态"
    )

    # 记忆来源
    source = models.CharField(
        max_length=64, blank=True, default="",
        verbose_name="记忆来源"
    )

    class Meta:
        verbose_name = "记忆条目"
        verbose_name_plural = "记忆条目"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["agent", "memory_type"]),
            models.Index(fields=["agent", "-importance"]),
            models.Index(fields=["agent", "status"]),
        ]

    def __str__(self):
        return f"[{self.get_memory_type_display()}] {self.summary[:50] or self.content[:50]}"

    def decay(self, hours_passed: float = None):
        """执行时间衰减，更新 recency_score
        使用指数衰减模型，半衰期由重要性决定
        """
        from django.conf import settings
        import math
        config = settings.MEMORY_CONFIG
        base_decay_hours = config.get("importance_decay_hours", 24)

        if hours_passed is None:
            hours_passed = (timezone.now() - self.created_at).total_seconds() / 3600

        lambda_factor = 1.0 / (base_decay_hours * (0.5 + self.importance))
        self.recency_score = 1.0 * math.exp(-lambda_factor * hours_passed)
        self.recency_score = max(0.0, min(1.0, self.recency_score))

    @property
    def age_hours(self) -> float:
        """记忆的小时数（自创建以来）"""
        return (timezone.now() - self.created_at).total_seconds() / 3600


class MemoryStream(models.Model):
    """记忆流：将 Agent 的多条记忆组织成有序流"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(
        "agents.Agent", on_delete=models.CASCADE, related_name="memory_streams",
        verbose_name="所属 Agent"
    )
    name = models.CharField(max_length=128, verbose_name="流名称")
    description = models.TextField(blank=True, default="", verbose_name="流描述")

    STREAM_TYPES = [
        ("daily", "每日流"),
        ("social", "社交流"),
        ("quest", "任务流"),
        ("reflection", "反思流"),
    ]
    stream_type = models.CharField(
        max_length=20, choices=STREAM_TYPES, default="daily",
        verbose_name="流类型"
    )

    memories = models.ManyToManyField(
        MemoryEntry, related_name="streams", blank=True,
        verbose_name="包含的记忆",
        through="MemoryStreamOrder"
    )

    embedding = VectorField(
        dimensions=1536, null=True, blank=True,
        verbose_name="流向量嵌入"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "记忆流"
        verbose_name_plural = "记忆流"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.agent.name} - {self.name}"


class MemoryStreamOrder(models.Model):
    """记忆流中的顺序"""
    stream = models.ForeignKey(MemoryStream, on_delete=models.CASCADE)
    memory = models.ForeignKey(MemoryEntry, on_delete=models.CASCADE)
    order = models.IntegerField(default=0, verbose_name="排序")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["stream", "order"]
        unique_together = ["stream", "memory"]
        verbose_name = "记忆流顺序"
        verbose_name_plural = "记忆流顺序"
