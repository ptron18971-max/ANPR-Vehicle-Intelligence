import json
import math
import os
import sys

from gis import get_camera_coordinates
from routing import get_road_route

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000 # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0)**2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0)**2
        
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def validate_graph():
    graph_path = "../../docs/contracts/camera_graph.json"
    if not os.path.exists(graph_path):
        print(f"Error: {graph_path} not found.")
        return

    with open(graph_path, "r") as f:
        graph = json.load(f)

    edges = graph.get("edges", [])
    print(f"Loaded {len(edges)} edges for validation.\n")
    print("-" * 110)
    print(f"{'Edge':<10} | {'SL Dist':<10} | {'OSRM Dist':<10} | {'Graph Dist':<10} | {'OSRM Time':<10} | {'Graph [Min, Avg, Max]':<25} | {'Status'}")
    print("-" * 110)

    total_edges = len(edges)
    dist_violations = 0
    time_violations = 0
    missing_routes = 0

    for edge in edges:
        u = edge["from_camera"]
        v = edge["to_camera"]
        
        g_dist = edge.get("distance_meters")
        g_min = edge.get("min_travel_time_sec")
        g_avg = edge.get("avg_travel_time_sec")
        g_max = edge.get("max_travel_time_sec")

        coord_u = get_camera_coordinates(u)
        coord_v = get_camera_coordinates(v)

        if not coord_u or not coord_v:
            print(f"{u}->{v:<5} | Missing coordinates")
            continue
            
        sl_dist = haversine(coord_u["lat"], coord_u["lon"], coord_v["lat"], coord_v["lon"])
        
        route = get_road_route(u, v)
        if not route:
            missing_routes += 1
            print(f"{u}->{v:<5} | Routing failed")
            continue

        o_dist = route.get("routing_distance_meters", 0)
        o_time = route.get("duration_seconds", 0)

        # Distance Check: OSRM distance should be >= Straight-Line distance (with small margin for float errors)
        dist_ok = o_dist >= (sl_dist * 0.98)
        if not dist_ok:
            dist_violations += 1

        # Time Check: OSRM duration vs Graph temporal bounds
        time_ok = (g_min <= o_time <= g_max)
        if not time_ok:
            time_violations += 1

        status_flags = []
        if not dist_ok:
            status_flags.append("DIST_ERR")
        if not time_ok:
            if o_time < g_min:
                status_flags.append("TIME_TOO_FAST")
            else:
                status_flags.append("TIME_TOO_SLOW")

        status_str = ", ".join(status_flags) if status_flags else "OK"
        
        # Formatting
        sl_str = f"{sl_dist:.0f}m"
        o_dist_str = f"{o_dist:.0f}m"
        g_dist_str = f"{g_dist}m"
        o_time_str = f"{o_time}s"
        g_time_str = f"[{g_min}, {g_avg}, {g_max}]"

        print(f"{u}->{v:<5} | {sl_str:<10} | {o_dist_str:<10} | {g_dist_str:<10} | {o_time_str:<10} | {g_time_str:<25} | {status_str}")

    print("-" * 110)
    print(f"Validation Summary:")
    print(f"Total Edges Evaluated : {total_edges - missing_routes}")
    print(f"Distance Violations   : {dist_violations} (OSRM distance < Straight Line)")
    print(f"Temporal Violations   : {time_violations} (OSRM duration outside Graph [min, max])")
    print(f"Routing Failures      : {missing_routes}")

if __name__ == "__main__":
    validate_graph()
