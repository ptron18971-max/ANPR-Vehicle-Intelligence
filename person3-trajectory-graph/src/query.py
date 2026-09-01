import json
import os
from datetime import datetime

# Assuming query.py is run from src/ or imported
# Get the absolute path to the contracts
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRAJECTORIES_PATH = os.path.join(BASE_DIR, "..", "docs", "contracts", "person3_to_person4.json")

def _load_trajectories():
    try:
        with open(TRAJECTORIES_PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def get_vehicle_trajectory(vehicle_id):
    """Returns the full trajectory object for a specific vehicle."""
    trajectories = _load_trajectories()
    for t in trajectories:
        if t["vehicle_id"] == vehicle_id:
            return t
    return None

def get_vehicle_location(vehicle_id, timestamp_str):
    """
    Returns the camera location for a vehicle at a specific timestamp.
    If the timestamp doesn't match an observation exactly, returns None
    (or could be extended to return the closest interpolated segment).
    """
    traj = get_vehicle_trajectory(vehicle_id)
    if not traj:
        return None
        
    for obs in traj.get("observations", []):
        if obs["timestamp"] == timestamp_str:
            return obs
            
    return None

def get_vehicles_at_camera(camera_id):
    """Returns a list of vehicle observations at a specific camera."""
    trajectories = _load_trajectories()
    vehicles = []
    
    for t in trajectories:
        for obs in t.get("observations", []):
            if obs["camera_id"] == camera_id:
                vehicles.append({
                    "vehicle_id": t["vehicle_id"],
                    "timestamp": obs["timestamp"],
                    "status": obs["status"],
                    "confidence": obs["confidence"]
                })
    return vehicles

def get_vehicle_transitions(vehicle_id):
    """Returns the transitions list for a specific vehicle."""
    traj = get_vehicle_trajectory(vehicle_id)
    if not traj:
        return []
    return traj.get("transitions", [])

def get_route_between_cameras(from_camera_id, to_camera_id):
    """
    Returns the routing information between two cameras via the routing module.
    """
    # Import locally to avoid circular dependencies
    from routing import get_road_route
    return get_road_route(from_camera_id, to_camera_id)

if __name__ == "__main__":
    # Test query.py
    print("Test get_vehicle_trajectory('V002'):", get_vehicle_trajectory("V002") is not None)
    print("Test get_vehicles_at_camera('C21'):", len(get_vehicles_at_camera("C21")))
    
    # Test route query
    route = get_route_between_cameras("C17", "C35")
    if route:
        print(f"Test get_route_between_cameras('C17', 'C35'): Found route with {len(route['geometry'])} points")
    else:
        print("Test get_route_between_cameras('C17', 'C35'): No route or API key missing")
