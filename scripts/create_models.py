import os

def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Created: {path}")

BASE = "D:/python work space/AI-game/backend/apps/agents"
