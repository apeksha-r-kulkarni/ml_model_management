import json

with open("/home/apeksha-ssi021/.gemini/antigravity-ide/brain/031620db-80c5-4672-84ba-e0a5fd120bc6/.system_generated/logs/transcript.jsonl", "r") as f:
    for line in f:
        data = json.loads(line)
        content = data.get("content", "")
        if isinstance(content, str) and "Traceback" in content:
            print(f"Step {data.get('step_index')}:")
            print(content[-500:])
            print("-" * 40)
