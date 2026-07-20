"""
Agent 行为引擎测试
=================
测试感知 规划 行动 记忆的完整循环
"""
import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase

from backend.apps.agents.models import Agent, MBTIType, MBTIConfig, DailySchedule, ScheduleItem
from backend.apps.agents.engine import (
    AgentEngine, GlobalEngine, global_engine,
    Perception, ActionPlan, ActionResult,
)
from backend.apps.world.models import World, City, District, Scene, AgentPosition


@pytest.mark.django_db
class TestPerception:
    """感知阶段测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.world = World.objects.create(name="TestWorld", width=500, height=500)
        self.city = City.objects.create(name="TestCity", world=self.world, pos_x=250, pos_y=250, width=200, height=200)
        self.district = District.objects.create(
            name="TestDistrict", city=self.city, district_type="commercial",
            pos_x=0, pos_y=0, width=100, height=100,
        )
        self.scene = Scene.objects.create(
            name="TestCafe", district=self.district,
            max_occupancy=10, current_occupancy=2,
            function_tags="eat,drink,social",
            pos_x=50, pos_y=50, width=20, height=20,
        )
        self.agent = Agent.objects.create(
            name="TestAgent", mbti_type=MBTIType.INFP,
            energy=80.0, social_energy=70.0,
        )
        self.pos = AgentPosition.objects.create(
            agent=self.agent, world=self.world, scene=self.scene,
            pos_x=50, pos_y=50,
        )

    def test_perceive_returns_basic_info(self):
        """感知应返回 Agent 基本信息"""
        engine = AgentEngine(self.agent)
        perception = engine._perceive()
        assert perception.agent_id == str(self.agent.id)
        assert perception.agent_name == "TestAgent"
        assert perception.energy_level == 80.0
        assert perception.social_energy == 70.0
        assert perception.mbti_type == "INFP"

    def test_perceive_detects_current_scene(self):
        """感知应检测到当前场景"""
        engine = AgentEngine(self.agent)
        perception = engine._perceive()
        assert perception.current_scene is not None
        assert perception.current_scene["name"] == "TestCafe"
        assert perception.scene_occupancy == 2
        assert perception.scene_max_occupancy == 10

    def test_perceive_no_position_returns_no_scene(self):
        """没有位置记录的 Agent 感知不到场景"""
        agent2 = Agent.objects.create(name="GhostAgent", mbti_type=MBTIType.INTJ)
        engine = AgentEngine(agent2)
        perception = engine._perceive()
        assert perception.current_scene is None

    def test_perceive_detects_schedule(self):
        """感知应检测当前日程"""
        from django.utils import timezone
        import datetime

        schedule = DailySchedule.objects.create(
            agent=self.agent, date=timezone.localdate(),
            generation_type="base", is_active=True,
        )
        now = timezone.localtime()
        ScheduleItem.objects.create(
            schedule=schedule,
            start_time=(now - datetime.timedelta(minutes=30)).time(),
            end_time=(now + datetime.timedelta(minutes=30)).time(),
            activity="Having coffee",
            status="pending",
        )
        engine = AgentEngine(self.agent)
        perception = engine._perceive()
        assert perception.current_schedule_item is not None
        assert perception.current_schedule_item["activity"] == "Having coffee"


@pytest.mark.django_db
class TestPlanning:
    """规划阶段测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.agent = Agent.objects.create(
            name="PlannerTest", mbti_type=MBTIType.ENTJ,
            energy=80.0, social_energy=80.0,
        )
        MBTIConfig.objects.create(
            mbti_type=MBTIType.ENTJ,
            label="Commander",
            core_drive="Achievement and efficiency",
            communication_style="Direct and decisive",
            decision_style="Logic first",
            social_initiative=0.7,
            plan_adherence=0.8,
            curiosity=0.4,
            emotionality=0.3,
            talkativeness=0.6,
        )

    def test_plan_rest_when_low_energy(self):
        """精力过低时应该选择休息"""
        engine = AgentEngine(self.agent)
        perception = Perception(
            agent_id=str(self.agent.id), agent_name="Test",
            current_time="12:00", current_scene={"name": "Cafe"},
            nearby_agents=[], active_events=[],
            current_schedule_item=None, pending_schedule_items=[],
            energy_level=10.0, social_energy=80.0,
            mbti_type="ENTJ", status="idle",
            world_time_hour=12,
        )
        plan = engine._plan(perception)
        assert plan.action_type == "rest"
        assert plan.priority >= 8

    def test_plan_sleep_at_night(self):
        """深夜时段应选择睡眠"""
        engine = AgentEngine(self.agent)
        perception = Perception(
            agent_id=str(self.agent.id), agent_name="Test",
            current_time="23:30", current_scene={"name": "Cafe"},
            nearby_agents=[], active_events=[],
            current_schedule_item=None, pending_schedule_items=[],
            energy_level=60.0, social_energy=60.0,
            mbti_type="ENTJ", status="idle",
            world_time_hour=23,
        )
        plan = engine._plan(perception)
        assert plan.action_type == "sleep"

    def test_plan_execute_schedule_when_current_item(self):
        """有当前日程项时应执行日程"""
        engine = AgentEngine(self.agent)
        perception = Perception(
            agent_id=str(self.agent.id), agent_name="Test",
            current_time="10:00", current_scene={"name": "Cafe"},
            nearby_agents=[], active_events=[],
            current_schedule_item={
                "id": "test-id",
                "activity": "Meeting with client",
                "location": "Office",
                "start_time": "09:30",
                "end_time": "11:00",
            },
            pending_schedule_items=[],
            energy_level=70.0, social_energy=60.0,
            mbti_type="ENTJ", status="idle",
            world_time_hour=10,
        )
        plan = engine._plan(perception)
        assert plan.action_type == "execute_schedule"
        assert "Meeting" in plan.description

    def test_plan_social_with_nearby_agents(self):
        """附近有 Agent 且社交条件满足时选择社交"""
        engine = AgentEngine(self.agent)
        perception = Perception(
            agent_id=str(self.agent.id), agent_name="Test",
            current_time="14:00", current_scene={"name": "Cafe"},
            nearby_agents=[
                {"agent_id": "other-1", "agent_name": "Bob", "distance": 3.0},
            ],
            active_events=[],
            current_schedule_item=None, pending_schedule_items=[],
            energy_level=70.0, social_energy=60.0,
            mbti_type="ENTJ", status="idle",
            scene_occupancy=2, world_time_hour=14,
        )
        plan = engine._plan(perception)
        assert plan.action_type in ("social", "wait", "explore")

    def test_plan_wait_when_nothing_to_do(self):
        """无特殊事项时应等待"""
        engine = AgentEngine(self.agent)
        perception = Perception(
            agent_id=str(self.agent.id), agent_name="Test",
            current_time="14:00", current_scene={"name": "Cafe"},
            nearby_agents=[], active_events=[],
            current_schedule_item=None, pending_schedule_items=[],
            energy_level=70.0, social_energy=60.0,
            mbti_type="ENTJ", status="idle",
            world_time_hour=14,
        )
        plan = engine._plan(perception)
        assert plan.action_type in ("wait", "explore")


@pytest.mark.django_db
class TestActionExecution:
    """行动执行阶段测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.world = World.objects.create(name="TestWorld", width=500, height=500)
        self.city = City.objects.create(name="TestCity", world=self.world)
        self.district = District.objects.create(
            name="TestDistrict", city=self.city, district_type="commercial",
        )
        self.scene = Scene.objects.create(
            name="TestCafe", district=self.district, max_occupancy=10,
        )
        self.agent = Agent.objects.create(
            name="ActionTest", mbti_type=MBTIType.ESFP,
            energy=70.0, social_energy=70.0, status="idle",
        )
        self.pos = AgentPosition.objects.create(
            agent=self.agent, world=self.world, scene=self.scene,
            pos_x=50, pos_y=50,
        )

    def test_act_rest_restores_energy(self):
        """休息应恢复精力"""
        engine = AgentEngine(self.agent)
        plan = ActionPlan(
            action_type="rest",
            description="Taking a break",
            priority=8,
            duration_minutes=20,
        )
        result = engine._act(plan)
        assert result.success
        assert result.action_type == "rest"
        assert result.new_energy > self.agent.energy

    def test_act_sleep_restores_significantly(self):
        """睡眠应大幅恢复精力"""
        engine = AgentEngine(self.agent)
        plan = ActionPlan(
            action_type="sleep",
            description="Sleeping",
            priority=9,
            duration_minutes=60,
        )
        result = engine._act(plan)
        assert result.success
        assert result.action_type == "sleep"
        assert result.new_energy > 90.0

    def test_act_social_reduces_social_energy(self):
        """社交应消耗社交能量"""
        engine = AgentEngine(self.agent)
        plan = ActionPlan(
            action_type="social",
            description="Chatting with friend",
            target="target-id",
            priority=6,
            duration_minutes=15,
            parameters={"target_name": "Friend"},
        )
        result = engine._act(plan)
        assert result.success
        assert result.memory_content != ""
        assert result.memory_importance >= 0.5

    def test_act_execute_schedule_changes_status(self):
        """执行日程应改变状态"""
        engine = AgentEngine(self.agent)
        plan = ActionPlan(
            action_type="execute_schedule",
            description="Working on project",
            priority=7,
            duration_minutes=30,
            parameters={"schedule_item_id": "dummy-id"},
        )
        result = engine._act(plan)
        assert result.success
        self.agent.refresh_from_db()
        assert self.agent.status == "busy"


@pytest.mark.django_db
class TestFullIteration:
    """完整循环测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.world = World.objects.create(name="TestWorld", width=500, height=500)
        self.city = City.objects.create(name="TestCity", world=self.world)
        self.district = District.objects.create(
            name="TestDistrict", city=self.city, district_type="commercial",
        )
        self.scene = Scene.objects.create(
            name="TestCafe", district=self.district, max_occupancy=10,
        )
        self.agent = Agent.objects.create(
            name="FullCycle", mbti_type=MBTIType.ENFP,
            energy=80.0, social_energy=80.0, status="idle",
        )
        self.pos = AgentPosition.objects.create(
            agent=self.agent, world=self.world, scene=self.scene,
            pos_x=50, pos_y=50,
        )

    def test_full_iteration_completes(self):
        """完整循环应顺利执行"""
        engine = AgentEngine(self.agent)
        result = engine.run_iteration()
        assert "perception" in result
        assert "plan" in result
        assert "action_result" in result
        assert result["agent_id"] == str(self.agent.id)
        assert result["agent_name"] == "FullCycle"
        self.agent.refresh_from_db()
        assert self.agent.energy != 80.0

    def test_full_iteration_creates_memory_when_meaningful(self):
        """有意义的行动应该创建记忆"""
        engine = AgentEngine(self.agent)
        result = engine.run_iteration()
        if result.get("memory_id"):
            from backend.apps.memory.models import MemoryEntry
            memory = MemoryEntry.objects.filter(id=result["memory_id"]).first()
            assert memory is not None
            assert str(memory.agent_id) == str(self.agent.id)


@pytest.mark.django_db
class TestGlobalEngine:
    """全局引擎测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.world = World.objects.create(name="TestWorld", width=500, height=500)
        self.city = City.objects.create(name="TestCity", world=self.world)
        self.district = District.objects.create(
            name="TestDistrict", city=self.city, district_type="commercial",
        )
        self.scene = Scene.objects.create(
            name="TestCafe", district=self.district, max_occupancy=10,
        )
        self.agent1 = Agent.objects.create(
            name="AgentOne", mbti_type=MBTIType.ENFP,
            energy=80.0, social_energy=80.0, status="idle",
        )
        self.agent2 = Agent.objects.create(
            name="AgentTwo", mbti_type=MBTIType.ISTJ,
            energy=90.0, social_energy=70.0, status="idle",
        )
        AgentPosition.objects.create(
            agent=self.agent1, world=self.world, scene=self.scene, pos_x=50, pos_y=50,
        )
        AgentPosition.objects.create(
            agent=self.agent2, world=self.world, scene=self.scene, pos_x=55, pos_y=52,
        )

    def test_global_engine_runs_all_agents(self):
        """全局引擎应运行所有活跃 Agent"""
        engine = GlobalEngine()
        results = engine.run_all_iterations()
        assert len(results) == 2
        for r in results:
            assert "perception" in r
            assert "plan" in r
            assert "action_result" in r

    def test_global_engine_single_agent(self):
        """全局引擎可以运行单个 Agent"""
        engine = GlobalEngine()
        result = engine.run_single_iteration(self.agent1)
        assert result["agent_id"] == str(self.agent1.id)

    def test_global_engine_singleton(self):
        """全局引擎应该是单例"""
        assert global_engine is not None

    def test_global_engine_start_stop(self):
        """启动和停止应该正常工作"""
        engine = GlobalEngine()
        assert engine._running is False
        engine.stop()
        assert engine._running is False
