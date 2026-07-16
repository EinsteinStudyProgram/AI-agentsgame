import pytest
import random
from django.test import TestCase
from backend.apps.agents.models import Agent, MBTIConfig, MBTIType, DailySchedule, ScheduleItem


@pytest.mark.django_db
class TestMBTIEngine:
    """MBTI ????????"""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        """??????????"""
        from backend.apps.agents.services import MBTIEngine, Planner
        self.engine = MBTIEngine
        self.planner = Planner

        # ?? Agent
        self.agent = Agent.objects.create(
            name="??Agent-INFP",
            mbti_type=MBTIType.INFP,
            age=25,
            biography="??????????",
            energy=80.0,
            social_energy=70.0,
        )

        # ?? MBTI ??
        self.config = MBTIConfig.objects.create(
            mbti_type=MBTIType.INFP,
            core_drive="???????????",
            communication_style="????????",
            decision_style="??????????",
            social_initiative=0.6,
            plan_adherence=0.4,
            curiosity=0.8,
            emotionality=0.7,
            talkativeness=0.5,
        )

        # ???? MBTI ??? Agent??????
        self.agent_no_config = Agent.objects.create(
            name="???Agent",
            mbti_type=MBTIType.ESTJ,
            age=30,
            energy=50.0,
            social_energy=90.0,
        )

    # ========== build_system_prompt ?? ==========

    def test_build_system_prompt_includes_name(self):
        """Prompt ???? Agent ??"""
        prompt = self.engine.build_system_prompt(self.agent)
        assert self.agent.name in prompt

    def test_build_system_prompt_includes_mbti(self):
        """Prompt ???? MBTI ??"""
        prompt = self.engine.build_system_prompt(self.agent)
        assert "INFP" in prompt

    def test_build_system_prompt_includes_biography(self):
        """Prompt ????????"""
        prompt = self.engine.build_system_prompt(self.agent)
        assert self.agent.biography in prompt

    def test_build_system_prompt_includes_config_params(self):
        """Prompt ???? MBTI ????????"""
        prompt = self.engine.build_system_prompt(self.agent)
        assert "?????" in prompt
        assert "?????" in prompt
        assert "???" in prompt

    def test_build_system_prompt_fallback_when_no_config(self):
        """? MBTI ???????????"""
        prompt = self.engine.build_system_prompt(self.agent_no_config)
        assert self.agent_no_config.name in prompt
        assert "ESTJ" in prompt

    def test_build_system_prompt_includes_action_rules(self):
        """Prompt ????????"""
        prompt = self.engine.build_system_prompt(self.agent)
        assert "????" in prompt
        assert "????" in prompt

    def test_build_system_prompt_not_empty(self):
        """Prompt ??????"""
        prompt = self.engine.build_system_prompt(self.agent)
        assert len(prompt) > 100

    # ========== decide_social_initiation ?? ==========

    def test_social_initiation_high_energy_high_prob(self):
        """?????? Agent ???????"""
        # ????????????
        results = []
        for _ in range(100):
            results.append(self.engine.decide_social_initiation(self.agent))
        true_ratio = sum(results) / len(results)
        # INFP social_initiative=0.6, social_energy=70 -> prob=0.6*0.6+0.7*0.4=0.64
        # 100 ????? 0.5-0.8 ??
        assert 0.4 <= true_ratio <= 0.9, f"Social initiation ratio {true_ratio} out of range"

    def test_social_initiation_low_energy(self):
        """?????? Agent ??????"""
        self.agent.social_energy = 10.0
        self.agent.save()
        results = []
        for _ in range(100):
            results.append(self.engine.decide_social_initiation(self.agent))
        true_ratio = sum(results) / len(results)
        # prob = 0.6*0.6 + 0.1*0.4 = 0.36+0.04 = 0.4
        assert 0.2 <= true_ratio <= 0.6

    def test_social_initiation_fallback_no_config(self):
        """?? MBTI ????????? 0.5"""
        results = []
        for _ in range(100):
            results.append(self.engine.decide_social_initiation(self.agent_no_config))
        true_ratio = sum(results) / len(results)
        assert 0.3 <= true_ratio <= 0.9

    # ========== get_decision_bias ?? ==========

    def test_get_decision_bias_returns_all_keys(self):
        """?????? 4 ???????"""
        bias = self.engine.get_decision_bias(self.agent)
        expected_keys = {"plan_adherence", "curiosity", "emotionality", "social_initiative"}
        assert set(bias.keys()) == expected_keys

    def test_get_decision_bias_values_match_config(self):
        """???????? MBTI ????"""
        bias = self.engine.get_decision_bias(self.agent)
        assert bias["social_initiative"] == 0.6
        assert bias["plan_adherence"] == 0.4
        assert bias["curiosity"] == 0.8
        assert bias["emotionality"] == 0.7

    def test_get_decision_bias_values_in_range(self):
        """??????? 0-1 ???"""
        bias = self.engine.get_decision_bias(self.agent)
        for k, v in bias.items():
            assert 0.0 <= v <= 1.0, f"{k}={v} out of range"

    def test_get_decision_bias_fallback_defaults(self):
        """????????? 0.5"""
        bias = self.engine.get_decision_bias(self.agent_no_config)
        for k, v in bias.items():
            assert v == 0.5, f"{k}={v} should be 0.5"

        # ========== Agent ?????? ==========

    def test_agent_str_method(self):
        """Agent __str__ ??????"""
        assert str(self.agent) == "??Agent-INFP (INFP)"

        

    def test_mbti_config_str_method(self):
        """MBTIConfig __str__ ????"""
        assert "INFP" in str(self.config)


@pytest.mark.django_db
class TestPlanner:
    """?????"""

    @pytest.fixture(autouse=True)
    def setup_planner(self):
        from backend.apps.agents.services import Planner
        from django.utils import timezone
        import datetime
        self.planner = Planner
        self.agent = Agent.objects.create(name="??Agent", mbti_type=MBTIType.INFP)
        now = timezone.now()
        self.schedule = DailySchedule.objects.create(
            agent=self.agent,
            date=timezone.localdate(),
            generation_type="system",
            is_active=True,
        )
        self.item1 = ScheduleItem.objects.create(
            schedule=self.schedule,
            activity="??",
            start_time=datetime.time(7, 0),
            end_time=datetime.time(7, 30),
            status="completed",
        )
        self.item2 = ScheduleItem.objects.create(
            schedule=self.schedule,
            activity="??",
            start_time=datetime.time(9, 0),
            end_time=datetime.time(12, 0),
            status="pending",
        )

    def test_get_current_schedule_exists(self):
        """??????"""
        s = self.planner.get_current_schedule(self.agent)
        assert s is not None
        assert s.date == self.schedule.date

    def test_get_current_schedule_none(self):
        """?????? None"""
        new_agent = Agent.objects.create(name="?Agent", mbti_type=MBTIType.INTJ)
        s = self.planner.get_current_schedule(new_agent)
        assert s is None

    def test_override_schedule(self):
        """LLM ??????"""
        import datetime
        item = self.planner.override_schedule(
            self.agent, "????",
            datetime.time(14, 0), datetime.time(15, 0),
            location="???A",
            reason="??????",
        )
        assert item.activity == "????"
        assert item.status == "pending"
        assert item.location == "???A"


@pytest.mark.django_db
class TestModelRouter:
    """????????"""

    def setup_method(self):
        from backend.apps.agents.services import ModelRouter
        self.router = ModelRouter()

    def test_complex_tasks_use_pro(self):
        """?????? Pro ??"""
        for task in ["planning", "reflection", "decision", "mbti_analysis"]:
            model = self.router.get_model(task)
            assert model == "deepseek-chat"

    def test_daily_tasks_use_flash(self):
        """??????? Flash ??"""
        for task in ["dialogue", "greeting", "small_talk", "reaction"]:
            model = self.router.get_model(task)
            assert model == "deepseek-chat"  # ???????

    def test_unknown_task_defaults_to_flash(self):
        """?????????? Flash"""
        model = self.router.get_model("unknown_task_type")
        assert model == "deepseek-chat"
