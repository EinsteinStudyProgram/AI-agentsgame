import math, logging, base64
from typing import List, Optional
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from pgvector.django import CosineDistance
from .models import MemoryEntry, MemoryStream

logger = logging.getLogger(__name__)


class MemoryEncoder:
    def __init__(self):
        self.model = settings.LLM_CONFIG.get('embedding_model', 'text-embedding-ada-002')
        self.client = None

    def _fallback_encode(self, text):
        import hashlib
        dim = 1536
        v = [0.0] * dim
        for word in text.lower().split()[:100]:
            idx = int(hashlib.md5(word.encode()).hexdigest()[:8], 16) % dim
            v[idx] += 1.0
        norm = math.sqrt(sum(x*x for x in v))
        return [x/norm for x in v] if norm > 0 else v


class MemoryRetriever:
    def __init__(self):
        c = settings.MEMORY_CONFIG
        self.rw = c.get('recency_weight', 0.3)
        self.iw = c.get('importance_weight', 0.3)
        self.lw = c.get('relevance_weight', 0.4)
        self.k = c.get('retrieval_count', 10)
        self.enc = MemoryEncoder()

    def retrieve(self, agent_id, query=None, query_embedding=None, memory_type=None, tags=None, top_k=None, min_imp=0.0):
        top_k = top_k or self.k
        qs = MemoryEntry.objects.filter(agent_id=agent_id, status__in=['active', 'decaying'])
        if memory_type:
            qs = qs.filter(memory_type=memory_type)
        if query_embedding or query:
            if query_embedding is None:
                query_embedding = self.enc._fallback_encode(query or '')
            if query_embedding:
                qs = qs.alias(distance=CosineDistance('embedding', query_embedding)).order_by('distance')
                results = list(qs[:top_k*2])
            else:
                results = list(qs.order_by('-importance')[:top_k*2])
        else:
            results = list(qs.order_by('-importance', '-recency_score')[:top_k*2])
        scored = []
        for m in results:
            rel = 0.0
            if hasattr(m, 'distance') and m.distance is not None:
                rel = 1.0 - float(m.distance)
            total = self.lw * rel + self.rw * m.recency_score + self.iw * m.importance
            if m.importance >= min_imp:
                scored.append({'memory': m, 'score': round(total, 4), 'relevance': round(rel, 4), 'recency': round(m.recency_score, 4), 'importance': round(m.importance, 4)})
        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:top_k]

    def get_high_importance(self, agent_id, threshold=0.7, limit=5):
        return list(MemoryEntry.objects.filter(agent_id=agent_id, importance__gte=threshold, status='active').order_by('-importance')[:limit])

    def retrieve_by_time_window(self, agent_id, hours_back=24, top_k=20):
        cutoff = timezone.now() - timedelta(hours=hours_back)
        return list(MemoryEntry.objects.filter(agent_id=agent_id, created_at__gte=cutoff).order_by('-created_at')[:top_k])


class MemoryManager:
    def __init__(self):
        self.enc = MemoryEncoder()

    def create_memory(self, agent_id, content, memory_type='episodic', importance=None, summary=None, scene_id=None, tags=None, source=None):
        try:
            if importance is None:
                keywords = ['??','??','??','??','??','??','?','?','important','critical','danger','decision','promise','conflict']
                matches = sum(1 for kw in keywords if kw in content.lower())
                importance = min(0.95, 0.3 + matches * 0.1)
            embedding = self.enc._fallback_encode(content)
            memory = MemoryEntry.objects.create(agent_id=agent_id, content=content, summary=summary or content[:200], memory_type=memory_type, importance=importance, recency_score=1.0, embedding=embedding, scene_id=scene_id, tags=tags or [], source=source or 'unknown')
            return memory
        except Exception as e:
            logger.error(f'Failed to create memory: {e}')
            return None

    def decay_all_memories(self, agent_id=None):
        qs = MemoryEntry.objects.filter(status__in=['active', 'decaying'])
        if agent_id:
            qs = qs.filter(agent_id=agent_id)
        count = 0
        for m in qs.iterator(chunk_size=100):
            m.decay()
            MemoryEntry.objects.filter(id=m.id).update(recency_score=m.recency_score)
            count += 1
        return count

    def archive_old_memories(self, agent_id=None, days=7, imp=0.3):
        cutoff = timezone.now() - timedelta(days=days)
        qs = MemoryEntry.objects.filter(created_at__lte=cutoff, importance__lt=imp, status='active')
        if agent_id:
            qs = qs.filter(agent_id=agent_id)
        return qs.update(status='archived')
