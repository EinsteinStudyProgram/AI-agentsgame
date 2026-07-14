import base64, json

# Part 3: MBTIConfig
part3 = '''
class MBTIConfig(models.Model):
    \"\"\"MBTI\u884c\u4e3a\u77e9\u9635\u914d\u7f6e
    \u4e3a\u6bcf\u79cd MBTI \u4eba\u683c\u5b9a\u4e49\u884c\u4e3a\u53c2\u6570\uff0c\u5305\u62ec\u793e\u4ea4\u503e\u5411\u3001
    \u51b3\u7b56\u7cfb\u6570\u3001System Prompt \u6a21\u677f\u53d8\u91cf\u7b49\u3002
    \"\"\"
    mbti_type = models.CharField(max_length=4, choices=MBTIType.choices, unique=True, verbose_name=\"MBTI\u7c7b\u578b\")
    label = models.CharField(max_length=32, verbose_name=\"\u4eba\u683c\u6807\u7b7e\")

    core_drive = models.CharField(max_length=256, verbose_name=\"\u6838\u5fc3\u9a71\u52a8\u529b\",
                                   help_text=\"\u4f8b\u5982\uff1a\u2018\u8ffd\u6c42\u6548\u7387\u4e0e\u79e9\u5e8f\u2019 / \u2018\u63a2\u7d22\u65b0\u53ef\u80fd\u6027\u2019\")
    communication_style = models.CharField(max_length=256, verbose_name=\"\u6c9f\u901a\u98ce\u683c\",
                                            help_text=\"\u4f8b\u5982\uff1a\u2018\u76f4\u63a5\u4e86\u5f53\uff0c\u6ce8\u91cd\u4e8b\u5b9e\u2019 / \u2018\u59d4\u5a49\u542b\u84c4\uff0c\u5173\u6ce8\u611f\u53d7\u2019\")
    decision_style = models.CharField(max_length=256, verbose_name=\"\u51b3\u7b56\u98ce\u683c\",
                                       help_text=\"\u4f8b\u5982\uff1a\u2018\u903b\u8f91\u5206\u6790\u4f18\u5148\u2019 / \u2018\u4ee5\u4eba\u4e3a\u672c\u2019\")

    social_initiative = models.FloatField(default=0.5, verbose_name=\"\u793e\u4ea4\u4e3b\u52a8\u6027\",
                                          help_text=\"\u4e3b\u52a8\u53d1\u8d77\u793e\u4ea4\u7684\u6982\u7387\u7cfb\u6570\")
    plan_adherence = models.FloatField(default=0.7, verbose_name=\"\u8ba1\u5212\u9075\u5faa\u5ea6\",
                                       help_text=\"\u9075\u5b88\u539f\u5b9a\u8ba1\u5212\u7684\u7a0b\u5ea6\uff0c\u8d8a\u9ad8\u8d8a\u4e0d\u6613\u88ab\u6253\u65ad\")
    curiosity = models.FloatField(default=0.5, verbose_name=\"\u597d\u5947\u5fc3\",
                                   help_text=\"\u63a2\u7d22\u65b0\u4e8b\u7269/\u65b0\u4ea4\u4e92\u7684\u503e\u5411\")
    emotionality = models.FloatField(default=0.5, verbose_name=\"\u60c5\u7eea\u5316\u7a0b\u5ea6\",
                                      help_text=\"\u51b3\u7b56\u53d7\u60c5\u7eea\u5f71\u54cd\u7684\u7a0b\u5ea6\")
    talkativeness = models.FloatField(default=0.5, verbose_name=\"\u5065\u8c08\u7a0b\u5ea6\",
                                       help_text=\"\u5bf9\u8bdd\u4e2d\u751f\u6210\u5185\u5bb9\u7684\u957f\u5ea6\u548c\u4e30\u5bcc\u5ea6\")

    class Meta:
        verbose_name = \"MBTI \u884c\u4e3a\u77e9\u9635\"
        verbose_name_plural = \"MBTI \u884c\u4e3a\u77e9\u9635\"
        ordering = [\"mbti_type\"]

    def __str__(self):
        return f\"{self.mbti_type} - {self.label}\"

    def to_prompt_dict(self):
        return {
            \"personality_type\": self.mbti_type,
            \"core_drive\": self.core_drive,
            \"communication_style\": self.communication_style,
            \"decision_style\": self.decision_style,
            \"social_initiative\": self.social_initiative,
            \"plan_adherence\": self.plan_adherence,
            \"curiosity\": self.curiosity,
            \"talkativeness\": self.talkativeness,
        }
'''

# Part 4: DailySchedule and ScheduleItem
part4 = '''
class DailySchedule(models.Model):
    \"\"\"\u6bcf\u65e5\u65e5\u7a0b\u8868
    \u5b58\u50a8 Agent \u7684\u57fa\u7840\u65e5\u7a0b\u8ba1\u5212\u3002\u7cfb\u7edf\u4f1a\u5148\u751f\u6210\u4e00\u4e2a\u57fa\u7840\u8ba1\u5212\uff0c
    \u7136\u540e LLM \u53ef\u4ee5\u52a8\u6001\u8986\u76d6/\u63d2\u5165\u65b0\u7684\u8ba1\u5212\u9879\u3002
    \"\"\"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name=\"schedules\", verbose_name=\"\u5173\u8054 Agent\")
    date = models.DateField(verbose_name=\"\u8ba1\u5212\u65e5\u671f\")

    GENERATION_CHOICES = [(\"base\", \"\u57fa\u7840\u65e5\u7a0b\"), (\"llm_dynamic\", \"LLM \u52a8\u6001\u8986\u76d6\"), (\"player_intervention\", \"\u73a9\u5bb6\u5e72\u9884\")]
    generation_type = models.CharField(max_length=20, choices=GENERATION_CHOICES, default=\"base\", verbose_name=\"\u751f\u6210\u65b9\u5f0f\")

    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, verbose_name=\"\u662f\u5426\u751f\u6548\")

    class Meta:
        verbose_name = \"\u6bcf\u65e5\u65e5\u7a0b\u8868\"
        verbose_name_plural = \"\u6bcf\u65e5\u65e5\u7a0b\u8868\"
        unique_together = [\"agent\", \"date\", \"generation_type\"]
        ordering = [\"-date\"]

    def __str__(self):
        return f\"{self.agent.name} - {self.date}\"
'''

# Part 5: ScheduleItem
part5 = '''
class ScheduleItem(models.Model):
    \"\"\"\u65e5\u7a0b\u9879\uff1a\u65e5\u7a0b\u8868\u4e2d\u7684\u5177\u4f53\u6761\u76ee\"\"\"
    schedule = models.ForeignKey(DailySchedule, on_delete=models.CASCADE, related_name=\"items\", verbose_name=\"\u6240\u5c5e\u65e5\u7a0b\")
    start_time = models.TimeField(verbose_name=\"\u5f00\u59cb\u65f6\u95f4\")
    end_time = models.TimeField(verbose_name=\"\u7ed3\u675f\u65f6\u95f4\")
    activity = models.CharField(max_length=256, verbose_name=\"\u6d3b\u52a8\u63cf\u8ff0\")
    location = models.CharField(max_length=128, blank=True, default=\"\", verbose_name=\"\u6d3b\u52a8\u5730\u70b9\")

    STATUS_CHOICES = [(\"pending\", \"\u5f85\u6267\u884c\"), (\"in_progress\", \"\u6267\u884c\u4e2d\"), (\"completed\", \"\u5df2\u5b8c\u6210\"), (\"interrupted\", \"\u88ab\u6253\u65ad\"), (\"cancelled\", \"\u5df2\u53d6\u6d88\")]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=\"pending\", verbose_name=\"\u72b6\u6001\")

    interrupted_by = models.ForeignKey(Agent, on_delete=models.SET_NULL, null=True, blank=True, related_name=\"interruptions\", verbose_name=\"\u6253\u65ad\u8005\")
    interruption_reason = models.TextField(blank=True, default=\"\", verbose_name=\"\u6253\u65ad\u539f\u56e0\")
    order = models.IntegerField(default=0, verbose_name=\"\u6392\u5e8f\")

    class Meta:
        verbose_name = \"\u65e5\u7a0b\u9879\"
        verbose_name_plural = \"\u65e5\u7a0b\u9879\"
        ordering = [\"schedule\", \"start_time\"]

    def __str__(self):
        return f\"{self.start_time.strftime('%H:%M')} - {self.activity}\"
'''

# Part 6: SocialInteraction
part6 = '''
class SocialInteraction(models.Model):
    \"\"\"\u793e\u4ea4\u4ea4\u4e92\u8bb0\u5f55\"\"\"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    initiator = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name=\"initiated_interactions\", verbose_name=\"\u53d1\u8d77\u65b9\")
    target = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name=\"received_interactions\", verbose_name=\"\u63a5\u6536\u65b9\")

    INTERACTION_TYPES = [(\"greeting\", \"\u6253\u62db\u547c\"), (\"conversation\", \"\u5bf9\u8bdd\"), (\"joint_activity\", \"\u5171\u540c\u6d3b\u52a8\"), (\"conflict\", \"\u51b2\u7a81\")]
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES, verbose_name=\"\u4ea4\u4e92\u7c7b\u578b\")

    trigger_context = models.TextField(blank=True, default=\"\", verbose_name=\"\u89e6\u53d1\u4e0a\u4e0b\u6587\")
    summary = models.TextField(blank=True, default=\"\", verbose_name=\"\u4ea4\u4e92\u6458\u8981\")
    interrupted_initiator_plan = models.BooleanField(default=False, verbose_name=\"\u662f\u5426\u6253\u65ad\u53d1\u8d77\u65b9\u8ba1\u5212\")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=\"\u4ea4\u4e92\u65f6\u95f4\")
    duration_minutes = models.IntegerField(default=0, verbose_name=\"\u6301\u7eed\u5206\u949f\u6570\")

    class Meta:
        verbose_name = \"\u793e\u4ea4\u4ea4\u4e92\u8bb0\u5f55\"
        verbose_name_plural = \"\u793e\u4ea4\u4ea4\u4e92\u8bb0\u5f55\"
        ordering = [\"-created_at\"]

    def __str__(self):
        return f\"{self.initiator.name} -> {self.target.name}\"
'''

# Read existing models.py and append new parts
filepath = "D:/python work space/AI-game/backend/apps/agents/models.py"
with open(filepath, "r", encoding="utf-8") as f:
    existing = f.read()

full_content = existing + part3 + part4 + part5 + part6

# Write back
with open(filepath, "w", encoding="utf-8") as f:
    f.write(full_content)

print(f"Written {len(full_content)} bytes to models.py")
