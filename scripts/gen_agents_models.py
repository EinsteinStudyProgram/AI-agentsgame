import base64, json, sys

# The models.py content
content = '''\"\"\"
\u667a\u80fd\u4f53\u6838\u5fc3\u6a21\u5757 - \u6570\u636e\u6a21\u578b
=========================
\u5305\u542b\uff1aAgent \u6a21\u578b\u3001MBTI \u914d\u7f6e\u3001\u65e5\u7a0b\u89c4\u5212\u3001\u793e\u4ea4\u4ea4\u4e92\u8bb0\u5f55
\"\"\"
import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class MBTIType(models.TextChoices):
    \"\"\"MBTI 16\u578b\u4eba\u683c\u679a\u4e3e\"\"\"
    ISTJ = \"ISTJ\", \"\u5185\u5411-\u5b9e\u611f-\u601d\u8003-\u5224\u65ad (\u68c0\u67e5\u5458)\"
    ISFJ = \"ISFJ\", \"\u5185\u5411-\u5b9e\u611f-\u60c5\u611f-\u5224\u65ad (\u5b88\u62a4\u8005)\"
    INFJ = \"INFJ\", \"\u5185\u5411-\u76f4\u89c9-\u60c5\u611f-\u5224\u65ad (\u63d0\u5021\u8005)\"
    INTJ = \"INTJ\", \"\u5185\u5411-\u76f4\u89c9-\u601d\u8003-\u5224\u65ad (\u5efa\u7b51\u5e08)\"
    ISTP = \"ISTP\", \"\u5185\u5411-\u5b9e\u611f-\u601d\u8003-\u611f\u77e5 (\u9274\u8d4f\u5bb6)\"
    ISFP = \"ISFP\", \"\u5185\u5411-\u5b9e\u611f-\u60c5\u611f-\u611f\u77e5 (\u63a2\u9669\u5bb6)\"
    INFP = \"INFP\", \"\u5185\u5411-\u76f4\u89c9-\u60c5\u611f-\u611f\u77e5 (\u8c03\u505c\u8005)\"
    INTP = \"INTP\", \"\u5185\u5411-\u76f4\u89c9-\u601d\u8003-\u611f\u77e5 (\u903b\u8f91\u5b66\u5bb6)\"
    ESTP = \"ESTP\", \"\u5916\u5411-\u5b9e\u611f-\u601d\u8003-\u611f\u77e5 (\u4f01\u4e1a\u5bb6)\"
    ESFP = \"ESFP\", \"\u5916\u5411-\u5b9e\u611f-\u60c5\u611f-\u611f\u77e5 (\u8868\u6f14\u8005)\"
    ENFP = \"ENFP\", \"\u5916\u5411-\u76f4\u89c9-\u60c5\u611f-\u611f\u77e5 (\u7ade\u9009\u8005)\"
    ENTP = \"ENTP\", \"\u5916\u5411-\u76f4\u89c9-\u601d\u8003-\u611f\u77e5 (\u8fa9\u8bba\u5bb6)\"
    ESTJ = \"ESTJ\", \"\u5916\u5411-\u5b9e\u611f-\u601d\u8003-\u5224\u65ad (\u603b\u7ecf\u7406)\"
    ESFJ = \"ESFJ\", \"\u5916\u5411-\u5b9e\u611f-\u60c5\u611f-\u5224\u65ad (\u9886\u4e8b)\"
    ENFJ = \"ENFJ\", \"\u5916\u5411-\u76f4\u89c9-\u60c5\u611f-\u5224\u65ad (\u4e3b\u4eba\u516c)\"
    ENTJ = \"ENTJ\", \"\u5916\u5411-\u76f4\u89c9-\u601d\u8003-\u5224\u65ad (\u6307\u6325\u5b98)\"
'''

# Add more content sections
content_part2 = '''

class Agent(models.Model):
    \"\"\"\u667a\u80fd\u4f53\u6838\u5fc3\u6a21\u578b
    \u6bcf\u4e2a Agent \u662f\u4e16\u754c\u4e2d\u72ec\u7acb\u884c\u52a8\u7684 AI \u89d2\u8272\uff0c
    \u62e5\u6709 MBTI \u4eba\u683c\u3001\u5f53\u524d\u72b6\u6001\u3001\u4f4d\u7f6e\u548c\u65e5\u7a0b\u89c4\u5212\u3002
    \"\"\"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name=\"Agent ID\")
    name = models.CharField(max_length=64, unique=True, verbose_name=\"\u89d2\u8272\u540d\u79f0\")
    age = models.IntegerField(default=25, validators=[MinValueValidator(1)], verbose_name=\"\u5e74\u9f84\")
    biography = models.TextField(blank=True, default=\"\", verbose_name=\"\u80cc\u666f\u6545\u4e8b\",
                                 help_text=\"\u89d2\u8272\u7684\u80cc\u666f\u6545\u4e8b\u63cf\u8ff0\uff0c\u7528\u4e8e\u521d\u59cb\u5316 System Prompt\")

    mbti_type = models.CharField(
        max_length=4, choices=MBTIType.choices, default=MBTIType.INFP,
        verbose_name=\"MBTI \u4eba\u683c\u7c7b\u578b\",
        help_text=\"16\u578b\u4eba\u683c\uff0c\u5f71\u54cd\u51b3\u7b56\u7cfb\u6570\u548c\u884c\u4e3a\u503e\u5411\"
    )

    STATUS_CHOICES = [
        (\"idle\", \"\u7a7a\u95f2/\u5f85\u547d\"),
        (\"moving\", \"\u79fb\u52a8\u4e2d\"),
        (\"interacting\", \"\u4ea4\u4e92\u4e2d/\u793e\u4ea4\u4e2d\"),
        (\"sleeping\", \"\u7761\u7720\u4e2d\"),
        (\"busy\", \"\u5fd9\u788c\uff08\u6267\u884c\u8ba1\u5212\uff09\"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=\"idle\", verbose_name=\"\u5f53\u524d\u72b6\u6001\")

    energy = models.FloatField(default=100.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
                               verbose_name=\"\u7cbe\u529b\u503c\", help_text=\"0-100\uff0c\u5f71\u54cd\u884c\u52a8\u610f\u613f\u548c\u51b3\u7b56\u503e\u5411\")
    social_energy = models.FloatField(default=100.0, validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
                                      verbose_name=\"\u793e\u4ea4\u80fd\u91cf\", help_text=\"\u793e\u4ea4\u540e\u964d\u4f4e\uff0c\u72ec\u5904\u65f6\u6062\u590d\")

    pos_x = models.FloatField(default=0.0, verbose_name=\"X \u5750\u6807\")
    pos_y = models.FloatField(default=0.0, verbose_name=\"Y \u5750\u6807\")
    pos_z = models.FloatField(default=0.0, verbose_name=\"Z \u5750\u6807\")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=\"\u521b\u5efa\u65f6\u95f4\")
    updated_at = models.DateTimeField(auto_now=True, verbose_name=\"\u66f4\u65b0\u65f6\u95f4\")

    class Meta:
        verbose_name = \"\u667a\u80fd\u4f53\"
        verbose_name_plural = \"\u667a\u80fd\u4f53\"
        ordering = [\"name\"]

    def __str__(self):
        return f\"{self.name} ({self.mbti_type})\"
'''

print(json.dumps({"backend/apps/agents/models.py": base64.b64encode((content + content_part2).encode("utf-8")).decode("ascii")}))
