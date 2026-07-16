import pytest
import math
from django.test import TestCase
from backend.apps.world.models import World, City, District, Scene, AgentPosition, WorldEvent
from backend.apps.agents.models import Agent, MBTIType


@pytest.mark.django_db
class TestSpatialService:
    """?????????????????"""

    @pytest.fixture(autouse=True)
    def setup_world(self):
        from backend.apps.world.services import SpatialService, SceneQuery, EventService
        self.spatial = SpatialService
        self.scene_query = SceneQuery
        self.event_service = EventService

        # ??????
        self.world = World.objects.create(name="????", width=500, height=500)
        self.city = City.objects.create(name="????", world=self.world, pos_x=250, pos_y=250, width=200, height=200)
        self.district = District.objects.create(name="???", city=self.city, district_type="commercial", pos_x=0, pos_y=0, width=100, height=100)
        self.scene = Scene.objects.create(
            name="???", district=self.district,
            description="????????",
            max_occupancy=10, current_occupancy=0,
            function_tags="eat,drink,social",
            pos_x=50, pos_y=50, width=20, height=20,
        )
        self.scene2 = Scene.objects.create(
            name="???", district=self.district,
            max_occupancy=30, current_occupancy=5,
            function_tags="study,read,quiet",
            pos_x=10, pos_y=10, width=30, height=30,
        )

        # ?? Agent
        self.agent_a = Agent.objects.create(name="AgentA", mbti_type=MBTIType.INFP)
        self.agent_b = Agent.objects.create(name="AgentB", mbti_type=MBTIType.ENTJ)
        self.agent_c = Agent.objects.create(name="AgentC", mbti_type=MBTIType.ISTJ)

        # ????
        self.pos_a = AgentPosition.objects.create(
            agent=self.agent_a, world=self.world, scene=self.scene,
            pos_x=50, pos_y=50, heading=0.0,
        )
        self.pos_b = AgentPosition.objects.create(
            agent=self.agent_b, world=self.world, scene=self.scene,
            pos_x=55, pos_y=52, heading=45.0,  # ?? sqrt(25+4)=5.38
        )
        self.pos_c = AgentPosition.objects.create(
            agent=self.agent_c, world=self.world, scene=self.scene2,
            pos_x=20, pos_y=20, heading=90.0,  # ????
        )

    # ========== ???? ==========

    def test_get_nearby_agents_same_scene(self):
        """?????? Agent ?????"""
        nearby = self.spatial.get_nearby_agents(str(self.agent_a.id), radius=10.0)
        agent_ids = [n["agent_id"] for n in nearby]
        assert str(self.agent_b.id) in agent_ids

    def test_get_nearby_agents_excludes_self(self):
        """?????????"""
        nearby = self.spatial.get_nearby_agents(str(self.agent_a.id))
        agent_ids = [n["agent_id"] for n in nearby]
        assert str(self.agent_a.id) not in agent_ids

    def test_get_nearby_agents_different_scene(self):
        """????? Agent ???????"""
        nearby = self.spatial.get_nearby_agents(str(self.agent_a.id), radius=100.0)
        agent_ids = [n["agent_id"] for n in nearby]
        assert str(self.agent_c.id) not in agent_ids

    def test_get_nearby_agents_distance_limit(self):
        """????? Agent ???????"""
        nearby = self.spatial.get_nearby_agents(str(self.agent_a.id), radius=2.0)
        assert len(nearby) == 0  # AgentB??5.38 > 2.0

    def test_get_nearby_agents_empty_when_no_position(self):
        """????? Agent ?????"""
        new_agent = Agent.objects.create(name="NewAgent", mbti_type=MBTIType.INFP)
        nearby = self.spatial.get_nearby_agents(str(new_agent.id))
        assert nearby == []

    # ========== ???? ==========

    def test_get_scenes_by_function_tag(self):
        """?????????"""
        scenes = self.spatial.get_scenes_by_function(str(self.district.id), "eat")
        assert len(scenes) == 1
        assert scenes[0].name == "???"

    def test_get_scenes_by_function_no_match(self):
        """????????"""
        scenes = self.spatial.get_scenes_by_function(str(self.district.id), "swim")
        assert len(scenes) == 0

    def test_get_scene_occupants(self):
        """?????????"""
        occupants = self.spatial.get_scene_occupants(str(self.scene.id))
        agent_names = [o["agent_name"] for o in occupants]
        assert "AgentA" in agent_names
        assert "AgentB" in agent_names
        assert "AgentC" not in agent_names

    # ========== ???? ==========

    def test_move_agent_same_scene(self):
        """???????"""
        success = self.spatial.move_agent(str(self.agent_a.id), 60.0, 60.0)
        assert success
        self.pos_a.refresh_from_db()
        assert self.pos_a.pos_x == 60.0
        assert self.pos_a.pos_y == 60.0

    def test_move_agent_different_scene(self):
        """???????????-1????+1"""
        self.scene.current_occupancy = 2
        self.scene.save()
        self.scene2.current_occupancy = 5
        self.scene2.save()

        success = self.spatial.move_agent(
            str(self.agent_a.id), 15.0, 15.0, scene_id=str(self.scene2.id)
        )
        assert success

        self.scene.refresh_from_db()
        self.scene2.refresh_from_db()
        assert self.scene.current_occupancy == 1  # 2 - 1
        assert self.scene2.current_occupancy == 6  # 5 + 1

    def test_move_agent_no_position_record(self):
        """??????? Agent ?? False"""
        new_agent = Agent.objects.create(name="Ghost", mbti_type=MBTIType.INTJ)
        success = self.spatial.move_agent(str(new_agent.id), 0, 0)
        assert not success

    # ========== ???? ==========

    def test_build_full_path_all_levels(self):
        """??????"""
        path = self.scene_query.build_full_path(
            world_id=str(self.world.id),
            city_id=str(self.city.id),
            district_id=str(self.district.id),
            scene_id=str(self.scene.id),
        )
        assert "????" in path
        assert "????" in path
        assert "???" in path
        assert "???" in path

    def test_build_full_path_partial(self):
        """??????"""
        path = self.scene_query.build_full_path(world_id=str(self.world.id))
        assert "????" in path
        assert "????" not in path

    def test_build_full_path_no_args(self):
        """?????????"""
        path = self.scene_query.build_full_path()
        assert path == "????"

    # ========== ?????? ==========

    def test_find_available_scene(self):
        """????????????????"""
        scene = self.scene_query.find_available_scene(str(self.district.id), "eat")
        assert scene is not None
        assert scene.name == "???"

    def test_find_available_scene_full_occupancy(self):
        """??????? None"""
        self.scene.current_occupancy = 10
        self.scene.max_occupancy = 10
        self.scene.save()
        scene = self.scene_query.find_available_scene(str(self.district.id), "eat")
        assert scene is None

    # ========== ???? ==========

    def test_create_event(self):
        """??????"""
        event = self.event_service.create_event(
            scene_id=str(self.scene.id),
            event_type="fire",
            description="?????????",
            radius=50.0,
            expires_in_hours=1,
        )
        assert event.event_type == "fire"
        assert event.scene_id == self.scene.id
        assert event.expires_at is not None

    def test_get_active_events(self):
        """??????????"""
        import datetime
        from django.utils import timezone
        event = WorldEvent.objects.create(
            scene=self.scene,
            event_type="rain",
            description="???",
            radius=10.0,
        )
        active = self.event_service.get_active_events(str(self.scene.id))
        assert len(active) >= 1
        assert active[0].event_type == "rain"

    def test_get_active_events_expired_excluded(self):
        """????????"""
        import datetime
        from django.utils import timezone
        past = timezone.now() - datetime.timedelta(hours=2)
        WorldEvent.objects.create(
            scene=self.scene,
            event_type="storm",
            description="???",
            radius=10.0,
            expires_at=past,
        )
        active = self.event_service.get_active_events(str(self.scene.id))
        for e in active:
            assert e.event_type != "storm"
