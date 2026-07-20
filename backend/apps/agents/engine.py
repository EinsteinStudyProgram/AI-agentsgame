
"""
Agent Autonomous Behavior Engine
=================================
Implements the main loop: Perceive -> Plan -> Act -> Memorize
"""
import logging
import random
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from django.utils import timezone as django_timezone

from .models import Agent, MBTIConfig, ScheduleItem, SocialInteraction
from .services import MBTIEngine, Planner, ModelRouter
from backend.apps.world.models import AgentPosition, WorldEvent
from backend.apps.world.services import SpatialService
from backend.apps.memory.services import MemoryManager

logger = logging.getLogger(__name__)


@dataclass
class Perception:
    agent_id: str
    agent_name: str
    current_time: str
    current_scene: Optional[Dict]
    nearby_agents: List[Dict]
    active_events: List[Dict]
    current_schedule_item: Optional[Dict]
    pending_schedule_items: List[Dict]
    energy_level: float
    social_energy: float
    mbti_type: str
    status: str
    scene_occupancy: int = 0
    scene_max_occupancy: int = 0
    world_time_hour: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ActionPlan:
    action_type: str
    target: Optional[str] = None
    description: str = ""
    priority: int = 5
    reason: str = ""
    duration_minutes: int = 15
    parameters: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ActionResult:
    success: bool
    action_type: str
    description: str
    details: Dict = field(default_factory=dict)
    new_energy: float = 0.0
    new_social_energy: float = 0.0
    memory_content: str = ""
    memory_type: str = "episodic"
    memory_importance: float = 0.5
    triggers_interaction: bool = False
    interaction_target: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


class AgentEngine:
    def __init__(self, agent: Agent):
        self.agent = agent
        self.agent_id = str(agent.id)
        self.mbti_engine = MBTIEngine()
        self.planner = Planner()
        self.memory_manager = MemoryManager()
        self.model_router = ModelRouter()
        self.loop_count = 0

    ENERGY_COST = {
        "move": 5.0,
        "social": 8.0,
        "rest": -15.0,
        "execute_schedule": 6.0,
        "explore": 10.0,
        "wait": -2.0,
        "sleep": -30.0,
    }

    SOCIAL_ENERGY_COST = {
        "move": 0.0,
        "social": 12.0,
        "rest": 5.0,
        "execute_schedule": 3.0,
        "explore": 2.0,
        "wait": 3.0,
        "sleep": 10.0,
    }

    def run_iteration(self) -> Dict[str, Any]:
        self.loop_count += 1
        log = {
            "timestamp": django_timezone.now().isoformat(),
            "agent_id": self.agent_id,
            "agent_name": self.agent.name,
            "loop": self.loop_count,
        }
        try:
            p = self._perceive()
            log["perception"] = p.to_dict()

            plan = self._plan(p)
            log["plan"] = plan.to_dict()

            r = self._act(plan)
            log["action_result"] = r.to_dict()

            log["memory_id"] = self._memorize(r)
            self._update_agent_state(r)

            return log
        except Exception as e:
            logger.error(f"Agent {self.agent_id} error: {e}", exc_info=True)
            log["error"] = str(e)
            return log

    def _perceive(self) -> Perception:
        now = django_timezone.localtime()
        cs = None
        so = 0
        smo = 0

        try:
            pos = AgentPosition.objects.get(agent_id=self.agent_id)
            if pos.scene:
                cs = {
                    "id": str(pos.scene.id),
                    "name": pos.scene.name,
                    "description": pos.scene.description,
                    "district": str(pos.scene.district.name),
                    "function_tags": pos.scene.function_tags,
                }
                so = pos.scene.current_occupancy
                smo = pos.scene.max_occupancy
        except AgentPosition.DoesNotExist:
            pass

        nearby = SpatialService.get_nearby_agents(self.agent_id, radius=15.0)

        events = []
        if cs:
            try:
                for e in WorldEvent.objects.filter(
                    scene_id=cs["id"]
                ).order_by("-created_at")[:5]:
                    if e.expires_at is None or e.expires_at > now:
                        events.append(
                            {
                                "id": str(e.id),
                                "type": e.event_type,
                                "description": e.description,
                                "radius": e.radius,
                            }
                        )
            except Exception:
                pass

        sched = self.planner.get_current_schedule(self.agent)
        ci = None
        pi = []

        if sched:
            nt = now.time()
            qs = ScheduleItem.objects.filter(
                schedule=sched,
                start_time__lte=nt,
                end_time__gte=nt,
                status__in=["pending", "in_progress"],
            ).order_by("start_time")
            if qs.exists():
                i = qs.first()
                ci = {
                    "id": str(i.id),
                    "activity": i.activity,
                    "location": i.location,
                    "start_time": i.start_time.strftime("%H:%M"),
                    "end_time": i.end_time.strftime("%H:%M"),
                }
            for i in ScheduleItem.objects.filter(
                schedule=sched, status="pending", start_time__gte=nt
            ).order_by("start_time")[:5]:
                pi.append(
                    {
                        "id": str(i.id),
                        "activity": i.activity,
                        "location": i.location,
                        "start_time": i.start_time.strftime("%H:%M"),
                    }
                )

        self.agent.refresh_from_db()

        return Perception(
            agent_id=self.agent_id,
            agent_name=self.agent.name,
            current_time=now.strftime("%Y-%m-%d %H:%M"),
            current_scene=cs,
            nearby_agents=nearby,
            active_events=events,
            current_schedule_item=ci,
            pending_schedule_items=pi,
            energy_level=self.agent.energy,
            social_energy=self.agent.social_energy,
            mbti_type=self.agent.mbti_type,
            status=self.agent.status,
            scene_occupancy=so,
            scene_max_occupancy=smo,
            world_time_hour=now.hour,
        )

    def _plan(self, pp: Perception) -> ActionPlan:
        config = self._get_mbti_config()

        if pp.energy_level < 20.0:
            return ActionPlan(
                action_type="rest",
                description=f"Energy low ({pp.energy_level:.0f}%)",
                priority=10,
                reason="energy_low",
                duration_minutes=30,
            )

        h = pp.world_time_hour
        if h >= 23 or h < 6:
            return ActionPlan(
                action_type="sleep",
                description=f"Night time ({h}:00), sleeping",
                priority=9,
                reason="night_time",
                duration_minutes=60,
            )

        if pp.social_energy < 15.0 and pp.energy_level > 30.0:
            return ActionPlan(
                action_type="rest",
                description=f"Social depleted ({pp.social_energy:.0f}%)",
                priority=8,
                reason="social_energy_low",
                duration_minutes=20,
            )

        if pp.current_schedule_item:
            return ActionPlan(
                action_type="execute_schedule",
                target=pp.current_schedule_item.get("location"),
                description=pp.current_schedule_item["activity"],
                priority=7,
                reason="schedule_item",
                parameters={
                    "schedule_item_id": pp.current_schedule_item["id"]
                },
            )

        if self._should_socialize(pp, config):
            ns = sorted(
                pp.nearby_agents, key=lambda x: x.get("distance", 999)
            )
            if ns:
                t = ns[0]
                return ActionPlan(
                    action_type="social",
                    target=t.get("agent_id"),
                    description=f"Chat with {t.get('agent_name','someone')}",
                    priority=6,
                    reason="social_initiative",
                    duration_minutes=random.randint(15, 30),
                    parameters={"target_name": t.get("agent_name")},
                )

        if self._should_explore(pp, config):
            return ActionPlan(
                action_type="explore",
                description="Explore surroundings",
                priority=4,
                reason="curiosity",
                duration_minutes=random.randint(20, 40),
            )

        if pp.energy_level < 50.0:
            return ActionPlan(
                action_type="wait",
                description="Resting, observing",
                priority=3,
                reason="moderate_energy",
                duration_minutes=10,
            )

        if pp.pending_schedule_items:
            nxt = pp.pending_schedule_items[0]
            return ActionPlan(
                action_type="move",
                target=nxt.get("location"),
                description=f"Head to: {nxt['activity']}",
                priority=5,
                reason="prepare_schedule",
                duration_minutes=10,
            )

        return ActionPlan(
            action_type="wait",
            description="Loitering",
            priority=2,
            reason="idle",
            duration_minutes=5,
        )

    def _should_socialize(self, pp, config) -> bool:
        if not pp.nearby_agents or pp.social_energy < 20.0 or pp.energy_level < 30.0:
            return False
        p = (
            config.get("social_initiative", 0.5) * 0.6
            + (pp.social_energy / 100.0) * 0.4
            + min(0.2, len(pp.nearby_agents) * 0.05)
        )
        return random.random() < min(0.95, p)

    def _should_explore(self, pp, config) -> bool:
        if pp.energy_level < 40.0:
            return False
        p = config.get("curiosity", 0.5)
        if pp.mbti_type[0] == "I" and pp.scene_occupancy > 5:
            p += 0.2
        return random.random() < p

    def _get_mbti_config(self) -> dict:
        try:
            return MBTIConfig.objects.get(
                mbti_type=self.agent.mbti_type
            ).to_prompt_dict()
        except MBTIConfig.DoesNotExist:
            return {
                "social_initiative": 0.5,
                "plan_adherence": 0.5,
                "curiosity": 0.5,
                "emotionality": 0.5,
            }

    def _act(self, plan: ActionPlan) -> ActionResult:
        m = {
            "execute_schedule": self._act_execute_schedule,
            "move": self._act_move,
            "social": self._act_social,
            "explore": self._act_explore,
            "rest": self._act_rest,
            "sleep": self._act_sleep,
        }
        return m.get(plan.action_type, self._act_wait)(plan)

    def _act_execute_schedule(self, plan: ActionPlan) -> ActionResult:
        self._set_agent_status("busy")
        sid = plan.parameters.get("schedule_item_id")
        if sid:
            try:
                ScheduleItem.objects.filter(id=sid).update(status="in_progress")
            except Exception:
                pass
        return ActionResult(
            success=True,
            action_type="execute_schedule",
            description=plan.description,
            new_energy=self.agent.energy - self.ENERGY_COST["execute_schedule"],
            new_social_energy=self.agent.social_energy
            - self.SOCIAL_ENERGY_COST["execute_schedule"],
            memory_content=f"Did: {plan.description}",
            memory_importance=0.4,
        )

    def _act_move(self, plan: ActionPlan) -> ActionResult:
        self._set_agent_status("moving")
        try:
            pos = AgentPosition.objects.get(agent_id=self.agent_id)
            SpatialService.move_agent(
                self.agent_id,
                pos.pos_x + random.uniform(-5, 5),
                pos.pos_y + random.uniform(-5, 5),
            )
        except Exception:
            pass
        return ActionResult(
            success=True,
            action_type="move",
            description=plan.description,
            new_energy=self.agent.energy - self.ENERGY_COST["move"],
            new_social_energy=self.agent.social_energy,
            memory_content="Moved to a new spot",
            memory_importance=0.3,
        )

    def _act_social(self, plan: ActionPlan) -> ActionResult:
        self._set_agent_status("interacting")
        tid = plan.target
        iid = None
        if tid:
            try:
                si = SocialInteraction.objects.create(
                    initiator=self.agent,
                    target_id=tid,
                    interaction_type="conversation",
                    trigger_context=plan.reason,
                    summary="Met and chatted",
                    duration_minutes=plan.duration_minutes,
                )
                iid = str(si.id)
            except Exception as e:
                logger.warning(f"Social creation failed: {e}")
        return ActionResult(
            success=True,
            action_type="social",
            description=plan.description,
            details={"interaction_id": iid, "target_id": tid},
            new_energy=self.agent.energy - self.ENERGY_COST["social"],
            new_social_energy=min(
                100, self.agent.social_energy - self.SOCIAL_ENERGY_COST["social"]
            ),
            memory_content=f"Socialized w/ {plan.parameters.get('target_name','someone')}",
            memory_importance=0.6,
            triggers_interaction=True,
            interaction_target=tid,
        )

    def _act_explore(self, plan: ActionPlan) -> ActionResult:
        self._set_agent_status("moving")
        try:
            pos = AgentPosition.objects.get(agent_id=self.agent_id)
            SpatialService.move_agent(
                self.agent_id,
                pos.pos_x + random.uniform(-15, 15),
                pos.pos_y + random.uniform(-15, 15),
            )
        except Exception:
            pass
        return ActionResult(
            success=True,
            action_type="explore",
            description=plan.description,
            new_energy=self.agent.energy - self.ENERGY_COST["explore"],
            new_social_energy=self.agent.social_energy
            + self.SOCIAL_ENERGY_COST["explore"],
            memory_content="Explored the area",
            memory_importance=0.5,
        )

    def _act_rest(self, plan: ActionPlan) -> ActionResult:
        self._set_agent_status("idle")
        return ActionResult(
            success=True,
            action_type="rest",
            description=plan.description,
            new_energy=min(100, self.agent.energy - self.ENERGY_COST["rest"]),
            new_social_energy=min(
                100, self.agent.social_energy + self.SOCIAL_ENERGY_COST["rest"]
            ),
            memory_content="Took a rest",
            memory_importance=0.2,
        )

    def _act_sleep(self, plan: ActionPlan) -> ActionResult:
        self._set_agent_status("sleeping")
        return ActionResult(
            success=True,
            action_type="sleep",
            description=plan.description,
            new_energy=min(100, self.agent.energy - self.ENERGY_COST["sleep"]),
            new_social_energy=min(
                100, self.agent.social_energy + self.SOCIAL_ENERGY_COST["sleep"]
            ),
            memory_content="Slept well",
            memory_importance=0.3,
        )

    def _act_wait(self, plan: ActionPlan) -> ActionResult:
        self._set_agent_status("idle")
        return ActionResult(
            success=True,
            action_type="wait",
            description=plan.description,
            new_energy=min(100, self.agent.energy - self.ENERGY_COST["wait"]),
            new_social_energy=min(
                100, self.agent.social_energy + self.SOCIAL_ENERGY_COST["wait"]
            ),
            memory_content="",
            memory_importance=0.1,
        )

    def _memorize(self, result: ActionResult) -> Optional[str]:
        if not result.memory_content:
            return None
        try:
            m = self.memory_manager.create_memory(
                agent_id=self.agent_id,
                content=result.memory_content,
                memory_type=result.memory_type,
                importance=result.memory_importance,
                source=f"action_engine_{result.action_type}",
            )
            return str(m.id) if m else None
        except Exception as e:
            logger.warning(f"Memory creation failed: {e}")
            return None

    def _set_agent_status(self, status: str):
        try:
            Agent.objects.filter(id=self.agent_id).update(status=status)
            self.agent.refresh_from_db()
        except Exception:
            pass

    def _update_agent_state(self, result: ActionResult):
        try:
            Agent.objects.filter(id=self.agent_id).update(
                energy=max(0.0, min(100.0, result.new_energy)),
                social_energy=max(0.0, min(100.0, result.new_social_energy)),
            )
        except Exception as e:
            logger.warning(f"State update failed: {e}")


class GlobalEngine:
    def __init__(self):
        self.engines: Dict[str, AgentEngine] = {}
        self._running = False

    def get_engine(self, agent: Agent) -> AgentEngine:
        aid = str(agent.id)
        if aid not in self.engines:
            self.engines[aid] = AgentEngine(agent)
        return self.engines[aid]

    def run_single_iteration(self, agent: Agent) -> Dict[str, Any]:
        return self.get_engine(agent).run_iteration()

    def run_all_iterations(self) -> List[Dict[str, Any]]:
        results = []
        agents = Agent.objects.filter(
            status__in=["idle", "moving", "interacting"]
        )
        for agent in agents:
            results.append(self.run_single_iteration(agent))
        return results

    def stop(self):
        self._running = False


global_engine = GlobalEngine()
