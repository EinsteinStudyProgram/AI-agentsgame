import base64, sys, os, json

def write_files():
    data = json.loads(sys.stdin.read().strip())
    base = "D:/python work space/AI-game"
    for filepath, b64_content in data.items():
        full_path = os.path.join(base, filepath)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        content = base64.b64decode(b64_content).decode("utf-8")
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"OK: {len(content)} bytes -> {filepath}")

if __name__ == "__main__":
    write_files()
