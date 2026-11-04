import json
with open('../../docs/contracts/person3_to_person4.json') as f:
    trajectories = json.load(f)

for t in trajectories:
    cams = t['camera_sequence']
    if 'C17' in cams and 'C35' in cams:
        print('Vehicle', t['vehicle_id'], 'Status:', t['trajectory_status'])
        for obs in t['observations']:
            print('  ', obs['camera_id'], obs['status'])

