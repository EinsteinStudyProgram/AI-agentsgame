"""
世界状态模块 - 四级空间拓扑数据模型
=================================
World（世界）-> City（城市）-> District（区域）-> Scene（场景）
"""
import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class World(models.Model):
    """世界/城市群：最高层级的空间单位"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128, unique=True, verbose_name="世界名称")
    description = models.TextField(blank=True, default="", verbose_name="世界描述")
    width = models.FloatField(default=1000.0, verbose_name="世界宽度")
    height = models.FloatField(default=1000.0, verbose_name="世界高度")
    is_active = models.BooleanField(default=True, verbose_name="是否激活")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "世界"
        verbose_name_plural = "世界"
        ordering = ["name"]

    def __str__(self):
        return self.name


class City(models.Model):
    """城市：世界中的城市单元"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    world = models.ForeignKey(
        World, on_delete=models.CASCADE, related_name="cities",
        verbose_name="所属世界"
    )
    name = models.CharField(max_length=128, verbose_name="城市名称")
    description = models.TextField(blank=True, default="", verbose_name="城市描述")

    # 城市在世界中的位置偏移
    pos_x = models.FloatField(default=0.0, verbose_name="X 偏移")
    pos_y = models.FloatField(default=0.0, verbose_name="Y 偏移")
    width = models.FloatField(default=200.0, verbose_name="城市宽度")
    height = models.FloatField(default=200.0, verbose_name="城市高度")

    class Meta:
        verbose_name = "城市"
        verbose_name_plural = "城市"
        unique_together = ["world", "name"]
        ordering = ["world", "name"]

    def __str__(self):
        return f"{self.world.name} - {self.name}"


class District(models.Model):
    """区域：城市中的功能区"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    city = models.ForeignKey(
        City, on_delete=models.CASCADE, related_name="districts",
        verbose_name="所属城市"
    )
    name = models.CharField(max_length=128, verbose_name="区域名称")
    description = models.TextField(blank=True, default="", verbose_name="区域描述")

    DISTRICT_TYPES = [
        ("residential", "住宅区"),
        ("commercial", "商业区"),
        ("entertainment", "娱乐区"),
        ("park", "公园/绿地"),
        ("education", "教育区"),
        ("industrial", "工业区"),
        ("administrative", "行政区"),
        ("transportation", "交通枢纽"),
    ]
    district_type = models.CharField(
        max_length=20, choices=DISTRICT_TYPES, default="residential",
        verbose_name="区域类型"
    )

    pos_x = models.FloatField(default=0.0, verbose_name="X 偏移")
    pos_y = models.FloatField(default=0.0, verbose_name="Y 偏移")
    width = models.FloatField(default=50.0, verbose_name="区域宽度")
    height = models.FloatField(default=50.0, verbose_name="区域高度")

    class Meta:
        verbose_name = "区域"
        verbose_name_plural = "区域"
        unique_together = ["city", "name"]
        ordering = ["city", "name"]

    def __str__(self):
        return f"{self.city} - {self.name}"


class Scene(models.Model):
    """场景：最细粒度的空间单位，Agent 实际活动和交互的场所"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    district = models.ForeignKey(
        District, on_delete=models.CASCADE, related_name="scenes",
        verbose_name="所属区域"
    )
    name = models.CharField(max_length=128, verbose_name="场景名称")
    description = models.TextField(blank=True, default="", verbose_name="场景描述")

    pos_x = models.FloatField(default=0.0, verbose_name="X 坐标")
    pos_y = models.FloatField(default=0.0, verbose_name="Y 坐标")
    width = models.FloatField(default=5.0, verbose_name="场景宽度")
    height = models.FloatField(default=5.0, verbose_name="场景高度")

    max_occupancy = models.IntegerField(
        default=10, validators=[MinValueValidator(1)],
        verbose_name="最大容纳人数"
    )
    current_occupancy = models.IntegerField(
        default=0, validators=[MinValueValidator(0)],
        verbose_name="当前人数"
    )

    FUNC_TAGS = [
        ("eat", "餐饮"), ("sleep", "住宿/休息"), ("work", "工作"),
        ("study", "学习"), ("shop", "购物"), ("socialize", "社交"),
        ("entertain", "娱乐"), ("exercise", "运动"),
        ("worship", "宗教/冥想"), ("health", "医疗/健康"),
    ]
    function_tags = models.CharField(
        max_length=256, blank=True, default="",
        verbose_name="功能标签（逗号分隔）",
        help_text="如：eat,socialize 表示可用于餐饮和社交"
    )
    interactables = models.JSONField(
        default=list, blank=True, verbose_name="可交互对象",
        help_text="场景内的物品/设备列表"
    )

    class Meta:
        verbose_name = "场景"
        verbose_name_plural = "场景"
        unique_together = ["district", "name"]
        ordering = ["district", "name"]

    def __str__(self):
        return f"{self.district} - {self.name}"

    @property
    def is_full(self) -> bool:
        """场景是否已满"""
        return self.current_occupancy >= self.max_occupancy

    @property
    def world_path(self) -> str:
        """获取完整空间路径：世界/城市/区域/场景"""
        return f"{self.district.city.world.name}/{self.district.city.name}/{self.district.name}/{self.name}"


class AgentPosition(models.Model):
    """Agent 位置管理：记录每个 Agent 在四维空间中的精确位置"""
    agent = models.OneToOneField(
        "agents.Agent", on_delete=models.CASCADE, related_name="position",
        primary_key=True, verbose_name="Agent"
    )
    world = models.ForeignKey(
        World, on_delete=models.CASCADE, related_name="agent_positions",
        verbose_name="所在世界"
    )
    scene = models.ForeignKey(
        Scene, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="occupants", verbose_name="所在场景"
    )
    pos_x = models.FloatField(default=0.0, verbose_name="精确 X 坐标")
    pos_y = models.FloatField(default=0.0, verbose_name="精确 Y 坐标")
    heading = models.FloatField(default=0.0, verbose_name="朝向角度")
    speed = models.FloatField(default=1.0, verbose_name="移动速度")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="位置更新时间")

    class Meta:
        verbose_name = "Agent 位置"
        verbose_name_plural = "Agent 位置"
        indexes = [
            models.Index(fields=["world", "scene"]),
        ]

    def __str__(self):
        return f"{self.agent.name} @ {self.scene or '未知'}"


class WorldEvent(models.Model):
    """世界事件：记录世界中发生的重要事件"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scene = models.ForeignKey(
        Scene, on_delete=models.CASCADE, related_name="events",
        verbose_name="发生场景"
    )
    event_type = models.CharField(max_length=64, verbose_name="事件类型")
    description = models.TextField(verbose_name="事件描述")
    data = models.JSONField(default=dict, blank=True, verbose_name="附加数据")
    radius = models.FloatField(
        default=10.0, verbose_name="影响半径",
        help_text="在此半径内的 Agent 能感知到该事件"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="事件时间")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="过期时间")

    class Meta:
        verbose_name = "世界事件"
        verbose_name_plural = "世界事件"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.created_at.strftime('%H:%M')}] {self.event_type} @ {self.scene.name}"
