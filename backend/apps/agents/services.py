"""
智能体核心服务层
=============
MBTI 行为矩阵引擎、混合规划器、模型路由
"""
import json
import logging
import random
from typing import Optional
from .models import Agent, MBTIConfig, DailySchedule, ScheduleItem

logger = logging.getLogger(__name__)


class MBTIEngine:
    """MBTI 行为矩阵引擎
    功能：
    1. 根据 Agent 的 MBTI 类型动态生成 System Prompt 参数
    2. 根据人格维度计算行为决策系数
    3. 提供社交触发判断的基准概率
    """

    @staticmethod
    def build_system_prompt(agent: Agent) -> str:
        """为指定 Agent 构建完整的 System Prompt"""
        try:
            config = MBTIConfig.objects.get(mbti_type=agent.mbti_type)
        except MBTIConfig.DoesNotExist:
            logger.warning(f"MBTI config not found for {agent.mbti_type}, using defaults")
            config = None

        prompt_parts = [
            f"# 角色设定\\n",
            f"你是 {agent.name}，{agent.mbti_type} 型人格。",
        ]

        if agent.biography:
            prompt_parts.append(f"背景故事：{agent.biography}")

        if config:
            prompt_parts.extend([
                f"\\n# 人格特征\\n",
                f"核心驱动力：{config.core_drive}",
                f"沟通风格：{config.communication_style}",
                f"决策风格：{config.decision_style}",
                f"\\n# 行为参数\\n",
                f"社交主动性：{config.social_initiative:.1f}",
                f"计划遵循度：{config.plan_adherence:.1f}",
                f"好奇心：{config.curiosity:.1f}",
                f"情绪化程度：{config.emotionality:.1f}",
                f"健谈程度：{config.talkativeness:.1f}",
            ])

        prompt_parts.append(
            "\\n# 行动规则\\n"
            "1. 你是一个在虚拟世界中生活的角色，拥有独立的日程安排。\\n"
            "2. 你可以主动发起社交互动，也可以对他人做出回应。\\n"
            "3. 你的决策受到人格类型的深刻影响。\\n"
            "4. 请用第一人称视角思考和行为。\\n"
            "5. 回复应该贴合你的性格设定，但保持自然和真实。\\n"
        )

        return "\\n".join(prompt_parts)

    @staticmethod
    def decide_social_initiation(agent: Agent) -> bool:
        """判断 Agent 是否主动发起社交
        基于 MBTI 社交主动性系数 + 当前社交能量 + 随机因子
        """
        try:
            config = MBTIConfig.objects.get(mbti_type=agent.mbti_type)
            base_prob = config.social_initiative
        except MBTIConfig.DoesNotExist:
            base_prob = 0.5

        # 社交能量影响：能量越高越可能社交
        energy_factor = agent.social_energy / 100.0

        # 综合概率
        final_prob = base_prob * 0.6 + energy_factor * 0.4

        # 随机判定
        return random.random() < final_prob

    @staticmethod
    def get_decision_bias(agent: Agent) -> dict:
        """获取决策倾向系数，供 LLM 调用时作为参数"""
        try:
            config = MBTIConfig.objects.get(mbti_type=agent.mbti_type)
        except MBTIConfig.DoesNotExist:
            return {
                "plan_adherence": 0.5,
                "curiosity": 0.5,
                "emotionality": 0.5,
                "social_initiative": 0.5,
            }

        return {
            "plan_adherence": config.plan_adherence,
            "curiosity": config.curiosity,
            "emotionality": config.emotionality,
            "social_initiative": config.social_initiative,
        }


class Planner:
    """混合规划器
    管理 Agent 的基础日程表 + LLM 动态覆盖的混合模式
    """

    @staticmethod
    def get_current_schedule(agent: Agent) -> Optional[DailySchedule]:
        """获取 Agent 当前生效的日程表"""
        from django.utils import timezone
        today = timezone.localdate()
        return DailySchedule.objects.filter(
            agent=agent, date=today, is_active=True
        ).order_by("-created_at").first()

    @staticmethod
    def get_next_schedule_item(agent: Agent) -> Optional[ScheduleItem]:
        """获取 Agent 的下一个待执行日程项"""
        from django.utils import timezone
        now = timezone.localtime()

        schedule = Planner.get_current_schedule(agent)
        if not schedule:
            return None

        return ScheduleItem.objects.filter(
            schedule=schedule,
            status="pending",
            start_time__gte=now.time(),
        ).order_by("start_time").first()

    @staticmethod
    def override_schedule(agent: Agent, activity: str, start_time,
                          end_time, location: str = "",
                          reason: str = "") -> ScheduleItem:
        """LLM 动态覆盖/插入新的日程项"""
        from django.utils import timezone
        today = timezone.localdate()
        schedule, _ = DailySchedule.objects.get_or_create(
            agent=agent, date=today,
            generation_type="llm_dynamic",
            defaults={"is_active": True}
        )

        item = ScheduleItem.objects.create(
            schedule=schedule,
            activity=activity,
            start_time=start_time,
            end_time=end_time,
            location=location,
            status="pending",
            interruption_reason=reason,
        )
        logger.info(f"Schedule overridden for {agent.name}: {activity}")
        return item


class ModelRouter:
    """模型路由器
    根据任务类型自动切换 DeepSeek V4-Pro 或 V4-Flash
    """
    # 需要复杂推理的任务类型 -> 使用 Pro 模型
    COMPLEX_TASKS = {"planning", "reflection", "decision", "mbti_analysis"}
    # 日常高频任务 -> 使用 Flash 模型
    DAILY_TASKS = {"dialogue", "greeting", "small_talk", "reaction"}

    def __init__(self):
        from django.conf import settings
        self.config = settings.LLM_CONFIG.get("deepseek", {})
        self.api_key = self.config.get("api_key", "")
        self.api_base = self.config.get("api_base", "")
        self.model_pro = self.config.get("model_pro", "deepseek-chat")
        self.model_flash = self.config.get("model_flash", "deepseek-chat")

    def get_model(self, task_type: str) -> str:
        """根据任务类型选择合适的模型"""
        if task_type in self.COMPLEX_TASKS:
            return self.model_pro
        return self.model_flash

    async def call_llm(self, messages: list, task_type: str = "dialogue",
                       stream: bool = False, max_retries: int = 3):
        """调用 LLM 的通用方法
        参数：
            messages: 对话消息列表 [{"role": "...", "content": "..."}]
            task_type: 任务类型，决定使用哪个模型
            stream: 是否流式输出
            max_retries: 最大重试次数（含降级）
        返回：API 响应
        """
        import openai
        import asyncio
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.api_base,
        )

        model = self.get_model(task_type)
        last_error = None

        for attempt in range(max_retries):
            try:
                if stream:
                    return await self._call_stream(client, model, messages)
                else:
                    response = await client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=2000,
                    )
                    return response.choices[0].message.content

            except Exception as e:
                last_error = e
                logger.warning(f"LLM call failed (attempt {attempt + 1}): {e}")

                # 降级策略：如果 Pro 失败，降级到 Flash
                if model == self.model_pro:
                    logger.info(f"Degrading from Pro to Flash model")
                    model = self.model_flash

                # 指数退避重试
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)

        logger.error(f"LLM call failed after {max_retries} retries: {last_error}")
        raise last_error

    async def _call_stream(self, client, model: str, messages: list):
        """流式调用 LLM"""
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
            stream=True,
        )
        return response
