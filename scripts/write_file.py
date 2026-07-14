import base64, json, sys, os
# Content will be received as base64
data = sys.stdin.read().strip()
content = base64.b64decode(data).decode("utf-8")
path = os.path.join("D:/python work space", "AI-game", "backend", "apps", "agents", "models.py")
with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Written:", len(content), "bytes to", path)
