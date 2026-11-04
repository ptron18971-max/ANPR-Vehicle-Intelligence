with open('run_new_e2e.py', 'r') as f: code = f.read()
target = 'obs["vehicle_crop"] = obs.pop("vehicle_crop_ref")'
replacement = target + '''
        if isinstance(obs.get("timestamp"), (int, float)):
            import datetime
            obs["timestamp"] = datetime.datetime.utcfromtimestamp(obs["timestamp"]).isoformat() + "Z"'''
code = code.replace(target, replacement)
with open('run_new_e2e.py', 'w') as f: f.write(code)
