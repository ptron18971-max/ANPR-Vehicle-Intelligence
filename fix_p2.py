import json, datetime

path = r'D:\SIH\monoreposih\docs\contracts\person2_to_person3.json'
with open(path, 'r') as f:
    data = json.load(f)

for obs in data:
    if isinstance(obs.get("timestamp"), (int, float)):
        obs["timestamp"] = datetime.datetime.utcfromtimestamp(obs["timestamp"]).isoformat() + "Z"

with open(path, 'w') as f:
    json.dump(data, f, indent=2)
print('Fixed timestamps in person2_to_person3.json')
