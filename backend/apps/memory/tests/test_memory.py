import pytest
import math
import time
from datetime import timedelta
from django.utils import timezone
from backend.apps.agents.models import Agent, MBTIType
from backend.apps.memory.models import MemoryEntry, MemoryStream, MemoryStreamOrder


@pytest.mark.django_db
class TestMemoryEncoder:
    """???????"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from backend.apps.memory.services import MemoryEncoder
        self.encoder = MemoryEncoder()

    def test_fallback_encode_returns_list(self):
        """fallback ????????"""
        vec = self.encoder._fallback_encode("Hello world")
        assert isinstance(vec, list)

    def test_fallback_encode_dimension(self):
        """fallback ???? 1536"""
        vec = self.encoder._fallback_encode("test")
        assert len(vec) == 1536

    def test_fallback_encode_normalized(self):
        """fallback ????????"""
        vec = self.encoder._fallback_encode("Hello world")
        norm = math.sqrt(sum(v * v for v in vec))
        assert abs(norm - 1.0) < 1e-6, f"Norm={norm} != 1.0"

    def test_fallback_encode_different_texts(self):
        """??????????"""
        v1 = self.encoder._fallback_encode("??????")
        v2 = self.encoder._fallback_encode("????")
        # ????????
        assert v1 != v2

    def test_fallback_encode_same_text(self):
        """??????????"""
        v1 = self.encoder._fallback_encode("????")
        v2 = self.encoder._fallback_encode("????")
        assert v1 == v2

    def test_fallback_encode_empty_string(self):
        """????????"""
        vec = self.encoder._fallback_encode("")
        assert len(vec) == 1536


@pytest.mark.django_db
class TestMemoryManager:
    """???????"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from backend.apps.memory.services import MemoryManager
        self.manager = MemoryManager()
        self.agent = Agent.objects.create(name="????Agent", mbti_type=MBTIType.INFP)

    def test_create_memory(self):
        """??????"""
        memory = self.manager.create_memory(
            agent_id=str(self.agent.id),
            content="Ate lunch at the cafe, met a friend",
            memory_type="episodic",
        )
        assert memory is not None
        assert str(memory.agent_id) == str(self.agent.id)
        assert memory.memory_type == "episodic"

    def test_create_memory_default_importance(self):
        """???????? 0"""
        memory = self.manager.create_memory(
            agent_id=str(self.agent.id),
            content="Just some random thought",
        )
        assert 0.0 < memory.importance <= 1.0

    def test_create_memory_high_importance_keywords(self):
        """??????????????"""
        low = self.manager.create_memory(
            agent_id=str(self.agent.id),
            content="had breakfast today",
        )
        high = self.manager.create_memory(
            agent_id=str(self.agent.id),
            content="critical dangerous emergency decision promise important never forget",
        )
        assert high.importance > low.importance, f"{high.importance} <= {low.importance}"

    def test_create_memory_with_tags(self):
        """??????"""
        memory = self.manager.create_memory(
            agent_id=str(self.agent.id),
            content="Just some random thought",
            tags=["social", "eat"],
        )
        assert "social" in memory.tags
        assert "eat" in memory.tags

    def test_create_memory_with_custom_importance(self):
        """??????"""
        memory = self.manager.create_memory(
            agent_id=str(self.agent.id),
            content="test",
            importance=0.95,
        )
        assert memory.importance == 0.95

    def test_create_memory_failure_handled(self):
        """?????? None"""
        memory = self.manager.create_memory(
            agent_id="non-existent-id",
            content="test",
        )
        assert memory is None

    def test_create_different_memory_types(self):
        """?????????"""
        for mtype in ["episodic", "semantic", "reflective", "procedural"]:
            memory = self.manager.create_memory(
                agent_id=str(self.agent.id),
                content=f"??{mtype}???",
                memory_type=mtype,
            )
            assert memory.memory_type == mtype


@pytest.mark.django_db
class TestMemoryRetriever:
    """???????"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from backend.apps.memory.services import MemoryRetriever, MemoryManager
        self.retriever = MemoryRetriever()
        self.manager = MemoryManager()
        self.agent = Agent.objects.create(name="????Agent", mbti_type=MBTIType.ENFP)

        # ????????????
        self.memories = []
        for i, (content, importance, mtype) in enumerate([
            ("Went to the park for a walk", 0.3, "episodic"),
            ("Critical emergency meeting with the boss", 0.8, "episodic"),
            ("The sky is blue", 0.5, "semantic"),
            ("I should be more patient with others", 0.7, "reflective"),
            ("How to make coffee step by step", 0.4, "procedural"),
            ("Saw a bird outside window", 0.2, "episodic"),
            ("A life-changing important promise I made", 0.9, "episodic"),
            ("Water boils at 100 degrees Celsius", 0.6, "semantic"),
        ]):
            m = self.manager.create_memory(
                agent_id=str(self.agent.id),
                content=content,
                memory_type=mtype,
                importance=importance,
                tags=["tag_a"] if i % 2 == 0 else ["tag_b"],
            )
            if m:
                self.memories.append(m)

    # ========== ???? ==========

    def test_retrieve_basic(self):
        """????????"""
        results = self.retriever.retrieve(agent_id=str(self.agent.id))
        assert len(results) > 0
        assert len(results) <= 10  # ?? top_k=10

    def test_retrieve_orders_by_score(self):
        """???????????"""
        results = self.retriever.retrieve(agent_id=str(self.agent.id), top_k=10)
        scores = [r["score"] for r in results]
        assert all(scores[i] >= scores[i+1] for i in range(len(scores)-1))

    def test_retrieve_returns_required_fields(self):
        """????????????"""
        results = self.retriever.retrieve(agent_id=str(self.agent.id), top_k=1)
        assert len(results) == 1
        r = results[0]
        assert "memory" in r
        assert "score" in r
        assert "relevance" in r
        assert "recency" in r
        assert "importance" in r

    # ========== ???? ==========

    def test_retrieve_by_type(self):
        """???????"""
        results = self.retriever.retrieve(
            agent_id=str(self.agent.id),
            memory_type="reflective",
            top_k=10,
        )
        for r in results:
            assert r["memory"].memory_type == "reflective"

    def test_retrieve_by_type_no_match(self):
        """??????????????"""
        results = self.retriever.retrieve(
            agent_id=str(self.agent.id),
            memory_type="episodic",
            top_k=10,
        )
        assert len(results) > 0  # ??? episotic ??

    # ========== ????? ==========

    def test_retrieve_min_importance(self):
        """???????"""
        results = self.retriever.retrieve(
            agent_id=str(self.agent.id),
            min_imp=0.7,
            top_k=10,
        )
        for r in results:
            assert r["importance"] >= 0.7

    def test_retrieve_min_importance_none_passing(self):
        """???????????"""
        results = self.retriever.retrieve(
            agent_id=str(self.agent.id),
            min_imp=1.0,  # ??????? >= 1.0
            top_k=10,
        )
        assert len(results) == 0

    # ========== top_k ?? ==========

    def test_retrieve_top_k_limit(self):
        """top_k ????????"""
        results = self.retriever.retrieve(
            agent_id=str(self.agent.id),
            top_k=3,
        )
        assert len(results) <= 3

    def test_retrieve_top_k_zero(self):
        """top_k=0 ?????"""
        results = self.retriever.retrieve(
            agent_id=str(self.agent.id),
            top_k=0,
        )
        assert len(results) > 0  # ???? 10

    # ========== ?????? ==========

    def test_get_high_importance(self):
        """????????"""
        results = self.retriever.get_high_importance(
            agent_id=str(self.agent.id),
            threshold=0.7,
        )
        for m in results:
            assert m.importance >= 0.7

    def test_retrieve_by_time_window(self):
        """??????"""
        results = self.retriever.retrieve_by_time_window(
            agent_id=str(self.agent.id),
            hours_back=24,
        )
        assert len(results) > 0

    # ========== ??? ==========

    def test_memory_stream_creation(self):
        """?????"""
        stream = MemoryStream.objects.create(
            agent=self.agent,
            name="???????",
            description="???",
        )
        assert stream.name == "???????"
        assert stream.agent_id == self.agent.id

    def test_memory_stream_order(self):
        """???????"""
        stream = MemoryStream.objects.create(agent=self.agent, name="???")
        memory = self.memories[0]
        order_entry = MemoryStreamOrder.objects.create(
            stream=stream,
            memory=memory,
            order=1,
        )
        assert order_entry.order == 1
        assert order_entry.memory.id == memory.id
        assert stream.memories.count() == 1
