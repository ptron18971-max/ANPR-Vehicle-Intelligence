from datetime import datetime, timedelta
import networkx as nx
from graph import G
from validator import validate_transition

import sys
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
def get_candidate_paths(graph, source, target, cutoff=6):
    """1. Candidate path generation using nx.all_simple_paths"""
    try:
        return list(nx.all_simple_paths(graph, source=source, target=target, cutoff=cutoff))
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []

def evaluate_path_feasibility(path, graph, observed_time_sec):
    """2. Path temporal feasibility & 3. Path ranking (time error)"""
    min_time, max_time, avg_time = 0, 0, 0
    for j in range(len(path) - 1):
        edge = graph[path[j]][path[j+1]]
        min_time += edge.get("min_travel_time_sec", 0)
        max_time += edge.get("max_travel_time_sec", float("inf"))
        avg_time += edge.get("avg_travel_time_sec", (min_time + max_time)/2 if max_time != float("inf") else min_time)
        
    is_feasible = min_time <= observed_time_sec <= max_time
    time_error = abs(avg_time - observed_time_sec)
    
    return is_feasible, time_error

def find_best_path(graph, source, target, observed_time_sec, cutoff=6):
    """4. Select best path"""
    candidates = get_candidate_paths(graph, source, target, cutoff)
    best_path = None
    best_error = float("inf")
    
    for path in candidates:
        is_feasible, time_error = evaluate_path_feasibility(path, graph, observed_time_sec)
        if is_feasible and time_error < best_error:
            best_error = time_error
            best_path = path
            
    return best_path, best_error

def compute_inferred_confidence(start_conf, end_conf, time_error, observed_time_sec):
    """6. Confidence score for inferred nodes"""
    base = (start_conf + end_conf) / 2
    degrade = (time_error / observed_time_sec) * 0.15 if observed_time_sec > 0 else 0
    return max(0.0, round(base - degrade, 2))

def reconstruct_trajectory(observations, graph, use_spatiotemporal=True):
    """
    Reconstructs a continuous camera trajectory.
    Can use spatio-temporal constraints or ordinary shortest-path.
    """
    if not observations:
        return [], []

    sorted_obs = sorted(observations, key=lambda x: x["timestamp"])
    reconstructed = [sorted_obs[0]]
    transitions = []

    for i in range(len(sorted_obs) - 1):
        curr_obs = sorted_obs[i]
        next_obs = sorted_obs[i + 1]

        u = curr_obs["camera_id"]
        v = next_obs["camera_id"]

        if u == v:
            reconstructed.append(next_obs)
            continue

        t_start = curr_obs["timestamp"]
        t_end = next_obs["timestamp"]
        observed_time_sec = (t_end - t_start).total_seconds()

        if graph.has_edge(u, v):
            is_valid = validate_transition(graph[u][v], observed_time_sec)
            next_obs_copy = dict(next_obs)
            next_obs_copy["valid_transition"] = is_valid
            reconstructed.append(next_obs_copy)
            
            transitions.append({
                "from": u, "to": v,
                "travel_time_sec": observed_time_sec,
                "is_valid": is_valid, "method": "DIRECT"
            })
        else:
            unreachable = False
            if use_spatiotemporal:
                path, time_error = find_best_path(graph, u, v, observed_time_sec)
                is_valid = path is not None
                if not is_valid:
                    try:
                        # Check if it's truly unreachable
                        nx.shortest_path(graph, source=u, target=v)
                    except (nx.NetworkXNoPath, nx.NodeNotFound):
                        unreachable = True
            else:
                try:
                    path = nx.shortest_path(graph, source=u, target=v)
                    is_feasible, time_error = evaluate_path_feasibility(path, graph, observed_time_sec)
                    is_valid = is_feasible
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    path = None
                    is_valid = False
                    unreachable = True
            
            if path and is_valid:
                # 5. Assign inferred timestamps
                total_avg_time = 0
                edge_avg_times = []
                for j in range(len(path) - 1):
                    edge = graph[path[j]][path[j+1]]
                    avg_t = edge.get("avg_travel_time_sec", 1)
                    total_avg_time += avg_t
                    edge_avg_times.append(avg_t)

                current_time = t_start
                observed_total_time = (t_end - t_start).total_seconds()
                
                start_conf = curr_obs.get("identity_confidence", 1.0)
                end_conf = next_obs.get("identity_confidence", 1.0)
                inferred_conf = compute_inferred_confidence(start_conf, end_conf, time_error, observed_time_sec)

                for step_idx, node in enumerate(path[1:-1]):
                    fraction = edge_avg_times[step_idx] / total_avg_time if total_avg_time > 0 else (1/len(edge_avg_times))
                    step_time = observed_total_time * fraction
                    current_time += timedelta(seconds=step_time)
                    
                    reconstructed.append({
                        "vehicle_id": curr_obs.get("vehicle_id"),
                        "camera_id": node,
                        "timestamp": current_time,
                        "interpolated": True,
                        "identity_confidence": inferred_conf
                    })

                next_obs_copy = dict(next_obs)
                next_obs_copy["valid_transition"] = True
                reconstructed.append(next_obs_copy)
                
                transitions.append({
                    "from": u, "to": v,
                    "travel_time_sec": observed_time_sec,
                    "is_valid": True, "method": "SPATIOTEMPORAL" if use_spatiotemporal else "SHORTEST_PATH",
                    "path_used": path
                })
            else:
                next_obs_copy = dict(next_obs)
                if unreachable:
                    next_obs_copy["unreachable"] = True
                else:
                    next_obs_copy["valid_transition"] = False
                reconstructed.append(next_obs_copy)
                
                transitions.append({
                    "from": u, "to": v,
                    "travel_time_sec": observed_time_sec,
                    "is_valid": False, "method": "FAILED"
                })

    return reconstructed, transitions

