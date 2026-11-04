import json, datetime

path = r'D:\SIH\monoreposih\docs\contracts\person2_to_person3.json'
with open(path, 'r') as f:
    data = json.load(f)

for obs in data:
    ts = obs.get("timestamp")
    if isinstance(ts, str) and "." in ts:
        # Strip microseconds
        obs["timestamp"] = ts.split(".")[0] + "Z"

with open(path, 'w') as f:
    json.dump(data, f, indent=2)
print('Stripped microseconds in person2_to_person3.json')
