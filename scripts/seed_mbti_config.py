import django, os, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.config.settings")
sys.path.insert(0, "D:/python work space/AI-game")
django.setup()

from backend.apps.agents.models import MBTIConfig, MBTIType

# 16种MBTI人格的行为矩阵配置
MBTI_SEED_DATA = {
    MBTIType.ISTJ: {"label": "检查员", "core_drive": "追求效率与秩序", "communication_style": "直接了当，注重事实", "decision_style": "逻辑分析优先",
                     "social_initiative": 0.3, "plan_adherence": 0.9, "curiosity": 0.3, "emotionality": 0.2, "talkativeness": 0.3},
    MBTIType.ISFJ: {"label": "守护者", "core_drive": "维护和谐与帮助他人", "communication_style": "温和体贴，注重细节", "decision_style": "以人为本，考虑周全",
                     "social_initiative": 0.4, "plan_adherence": 0.8, "curiosity": 0.3, "emotionality": 0.6, "talkativeness": 0.4},
    MBTIType.INFJ: {"label": "提倡者", "core_drive": "追求意义与理想", "communication_style": "富有洞察力，善于倾听", "decision_style": "直觉驱动，价值导向",
                     "social_initiative": 0.5, "plan_adherence": 0.6, "curiosity": 0.7, "emotionality": 0.7, "talkativeness": 0.5},
    MBTIType.INTJ: {"label": "建筑师", "core_drive": "构建系统与实现愿景", "communication_style": "简洁直接，注重效率", "decision_style": "战略思维，逻辑至上",
                     "social_initiative": 0.3, "plan_adherence": 0.8, "curiosity": 0.8, "emotionality": 0.2, "talkativeness": 0.3},
    MBTIType.ISTP: {"label": "鉴赏家", "core_drive": "探索与实践操作", "communication_style": "简洁务实，行动导向", "decision_style": "灵活应变，实用主义",
                     "social_initiative": 0.4, "plan_adherence": 0.4, "curiosity": 0.7, "emotionality": 0.3, "talkativeness": 0.3},
    MBTIType.ISFP: {"label": "探险家", "core_drive": "追求美感与体验", "communication_style": "温和谦逊，真诚表达", "decision_style": "价值驱动，灵活开放",
                     "social_initiative": 0.4, "plan_adherence": 0.4, "curiosity": 0.6, "emotionality": 0.7, "talkativeness": 0.4},
    MBTIType.INFP: {"label": "调停者", "core_drive": "追求真实与和谐", "communication_style": "富有同理心，善于表达", "decision_style": "价值观优先，以人为本",
                     "social_initiative": 0.5, "plan_adherence": 0.5, "curiosity": 0.7, "emotionality": 0.8, "talkativeness": 0.6},
    MBTIType.INTP: {"label": "逻辑学家", "core_drive": "追求知识与理解", "communication_style": "分析性强，喜欢深入探讨", "decision_style": "逻辑分析，理性客观",
                     "social_initiative": 0.3, "plan_adherence": 0.5, "curiosity": 0.9, "emotionality": 0.3, "talkativeness": 0.5},
    MBTIType.ESTP: {"label": "企业家", "core_drive": "追求刺激与影响力", "communication_style": "精力充沛，直率坦诚", "decision_style": "灵活务实，机会导向",
                     "social_initiative": 0.8, "plan_adherence": 0.3, "curiosity": 0.8, "emotionality": 0.4, "talkativeness": 0.8},
    MBTIType.ESFP: {"label": "表演者", "core_drive": "追求快乐与分享", "communication_style": "热情洋溢，善于社交", "decision_style": "感性优先，随性而为",
                     "social_initiative": 0.9, "plan_adherence": 0.3, "curiosity": 0.7, "emotionality": 0.8, "talkativeness": 0.9},
    MBTIType.ENFP: {"label": "竞选者", "core_drive": "探索可能性与人际连接", "communication_style": "热情活泼，富有感染力", "decision_style": "直觉驱动，以人为本",
                     "social_initiative": 0.8, "plan_adherence": 0.4, "curiosity": 0.9, "emotionality": 0.8, "talkativeness": 0.8},
    MBTIType.ENTP: {"label": "辩论家", "core_drive": "挑战观念与探索创新", "communication_style": "机智幽默，喜欢辩论", "decision_style": "逻辑分析，灵活应变",
                     "social_initiative": 0.7, "plan_adherence": 0.3, "curiosity": 0.9, "emotionality": 0.4, "talkativeness": 0.8},
    MBTIType.ESTJ: {"label": "总经理", "core_drive": "追求效率与执行力", "communication_style": "直接果断，注重事实", "decision_style": "逻辑分析，结果导向",
                     "social_initiative": 0.6, "plan_adherence": 0.9, "curiosity": 0.3, "emotionality": 0.2, "talkativeness": 0.6},
    MBTIType.ESFJ: {"label": "领事", "core_drive": "服务他人与维护传统", "communication_style": "热情友善，善于合作", "decision_style": "以人为本，注重和谐",
                     "social_initiative": 0.7, "plan_adherence": 0.7, "curiosity": 0.4, "emotionality": 0.7, "talkativeness": 0.7},
    MBTIType.ENFJ: {"label": "主人公", "core_drive": "激励他人与实现理想", "communication_style": "富有魅力，善于引导", "decision_style": "价值导向，同理心强",
                     "social_initiative": 0.8, "plan_adherence": 0.6, "curiosity": 0.7, "emotionality": 0.8, "talkativeness": 0.8},
    MBTIType.ENTJ: {"label": "指挥官", "core_drive": "实现目标与领导团队", "communication_style": "直接有力，战略性强", "decision_style": "逻辑分析，目标导向",
                     "social_initiative": 0.7, "plan_adherence": 0.8, "curiosity": 0.7, "emotionality": 0.3, "talkativeness": 0.7},
}

for mbti_type, data in MBTI_SEED_DATA.items():
    MBTIConfig.objects.update_or_create(
        mbti_type=mbti_type.value,
        defaults=data
    )
    print(f"  OK: {mbti_type.value} ({data['label']})")

print(f"\\nTotal: {MBTIConfig.objects.count()} MBTI configs seeded")
