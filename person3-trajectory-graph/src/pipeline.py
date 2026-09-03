import json
from datetime import datetime
from collections import defaultdict
from trajectory import reconstruct_trajectory
from graph import G
from routing import get_road_route


def process_vehicle(v_id, observations, graph):
    traj_steps, trans_steps = reconstruct_trajectory(observations, graph, use_spatiotemporal=True)
    
    if not traj_steps:
        return None
    
    trajectory_status = "VALID"
    for step in traj_steps:
        if step.get("unreachable"):
            trajectory_status = "UNREACHABLE"
            break
        if step.get("valid_transition") is False:
            trajectory_status = "INVALID_TIME"
            break
            
    if trajectory_status == "VALID" and any(s.get("interpolated") for s in traj_steps):
        trajectory_status = "RECOVERED"
        
    start_time = traj_steps[0]["timestamp"]
    end_time = traj_steps[-1]["timestamp"]
    
    camera_sequence = []
    timestamps = []
    out_observations = []
    
    # TASK 6 - Validation
    last_time = None
    min_confidence = 1.0
    
    for i, step in enumerate(traj_steps):
        cam = step["camera_id"]
        t = step["timestamp"]
        # Use trajectory's confidence score!
        conf = step.get("identity_confidence", 1.0)
        
        if last_time and t < last_time:
            print(f"Warning: Non-chronological timestamps for {v_id}")
            
        # First/last observed cameras remain CONFIRMED, others INFERRED if interpolated
        if step.get("interpolated") and i != 0 and i != len(traj_steps) - 1:
            status = "INFERRED"
        else:
            status = "CONFIRMED"
            
        camera_sequence.append(cam)
        timestamps.append(t.strftime("%Y-%m-%dT%H:%M:%S"))
        
        out_observations.append({
            "camera_id": cam,
            "timestamp": t.strftime("%Y-%m-%dT%H:%M:%S"),
            "status": status,
            "confidence": conf
        })
        
        if conf < min_confidence:
            min_confidence = conf
            
        last_time = t

    out_transitions = []
    total_distance = 0
    has_full_distance = True

    # Build transitions using the graph for actual distance
    for i in range(len(traj_steps) - 1):
        step = traj_steps[i]
        next_step = traj_steps[i+1]
        
        u = step["camera_id"]
        v = next_step["camera_id"]
        
        t_delta = (next_step["timestamp"] - step["timestamp"]).total_seconds()
        status = "INFERRED" if (step.get("interpolated") or next_step.get("interpolated")) else "CONFIRMED"
        
        # Determine distance from graph
        edge_distance = None
        if graph.has_edge(u, v):
            edge_distance = graph[u][v].get("distance_meters")
            
        if edge_distance is not None:
            total_distance += edge_distance
        else:
            has_full_distance = False
            
        out_transitions.append({
            "from_camera_id": u,
            "to_camera_id": v,
            "travel_time_sec": t_delta,
            "distance_meters": edge_distance,
            "status": status,
            "confidence": round((step.get("identity_confidence", 1) + next_step.get("identity_confidence", 1)) / 2, 2)
        })

    duration = (end_time - start_time).total_seconds()
    
    route_geometry = []
    if trajectory_status in ["VALID", "RECOVERED"]:
        for i in range(len(traj_steps) - 1):
            u = traj_steps[i]["camera_id"]
            v = traj_steps[i+1]["camera_id"]
            route = get_road_route(u, v)
            if route and 'geometry' in route:
                route_geometry.append({
                    "from_camera_id": u,
                    "to_camera_id": v,
                    "distance_meters": route.get("routing_distance_meters"),
                    "points": route["geometry"]
                })
    
    return {
        "vehicle_id": v_id,
        "trajectory_status": trajectory_status,
        "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "end_time": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "camera_sequence": camera_sequence,
        "timestamps": timestamps,
        "observations": out_observations,
        "transitions": out_transitions,
        "route_geometry": route_geometry,
        "distance_meters": total_distance if has_full_distance and out_transitions else None,
        "duration_sec": duration,
        "trajectory_confidence": round(min_confidence, 2)
    }

def export_trajectories_for_person4(vehicle_obs, graph, output_path="../../docs/contracts/person3_to_person4.json"):
    results = []
    stats = {"VALID": 0, "RECOVERED": 0, "INVALID_TIME": 0, "UNREACHABLE": 0}
    
    for v_id, obs in vehicle_obs.items():
        res = process_vehicle(v_id, obs, graph)
        if res:
            results.append(res)
            stats[res["trajectory_status"]] = stats.get(res["trajectory_status"], 0) + 1
            
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
        
    # Check if JSON can be loaded back
    try:
        with open(output_path, "r") as f:
            json.load(f)
    except Exception as e:
        print(f"Validation failed: output JSON is invalid. Error: {e}")
        
    return results, stats, len(vehicle_obs)

def run_person3_pipeline():
    print("Running Person 3 Pipeline...")
    with open("../../docs/contracts/person2_to_person3.json", "r") as f:
        obs_data = json.load(f)

    vehicle_obs = defaultdict(list)
    for obs in obs_data:
        # Support timestamps that already have the 'Z' appended from P1/P2
        ts_str = obs["timestamp"].replace("Z", "")
        obs["timestamp"] = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S")
        vehicle_obs[obs["vehicle_id"]].append(obs)

    results, stats, total_input_vehicles = export_trajectories_for_person4(vehicle_obs, G)
    
    output_vehicle_ids = [r["vehicle_id"] for r in results]
    missing_vehicles = set(vehicle_obs.keys()) - set(output_vehicle_ids)
    duplicate_vehicles = [vid for vid in set(output_vehicle_ids) if output_vehicle_ids.count(vid) > 1]
    
    print("\n================ VALIDATION REPORT ================")
    print(f"Input vehicles: {total_input_vehicles}")
    print(f"Output vehicles: {len(results)}")
    
    if missing_vehicles:
        print(f"Missing vehicles: {len(missing_vehicles)} -> {missing_vehicles}")
    else:
        print("Missing vehicles: 0")
        
    if duplicate_vehicles:
        print(f"Duplicate vehicles: {len(duplicate_vehicles)} -> {duplicate_vehicles}")
    else:
        print("Duplicate vehicles: 0")
        
    if len(results) == total_input_vehicles:
        print("Status: SUCCESS (input_count == output_count)")
    else:
        print("Status: FAILED (input_count != output_count)")
    
    # Validate canonical graph loaded
    try:
        if len(G.nodes) > 0:
            print("Graph check: SUCCESS (Canonical graph loaded successfully)")
        else:
            print("Graph check: FAILED (Graph is empty)")
    except Exception as e:
        print(f"Graph check: FAILED ({e})")
    
    print("===================================================\n")
    
    print("Person 3 pipeline complete")
    print(f"Valid trajectories: {stats.get('VALID', 0)}")
    print(f"Recovered trajectories: {stats.get('RECOVERED', 0)}")
    print(f"Invalid-time cases: {stats.get('INVALID_TIME', 0)}")
    print(f"Unreachable cases: {stats.get('UNREACHABLE', 0)}")
    print("Output: ../../docs/contracts/person3_to_person4.json")

if __name__ == "__main__":
    run_person3_pipeline()
