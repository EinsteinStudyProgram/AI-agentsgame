import os

content = """# memory services placeholder - will be replaced
print("memory services OK")
"""

filepath = "D:/python work space/AI-game/backend/apps/memory/services.py"
with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print(f"Written: {len(content)} bytes")
