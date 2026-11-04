from query import get_vehicle_trajectory

def get_camera_coordinates(camera_id):
    """
    Returns the geographical coordinates for a given camera ID.
    Uses a deterministic 6x6 mock grid based in Bangalore.
    """
    try:
        idx = int(camera_id.replace("C", "")) - 1
        if not (0 <= idx <= 35):
            return None
            
        row = idx // 6
        col = idx % 6
        
        # Base coordinates
        base_lat = 12.9716
        base_lon = 77.5946
        
        # Grid offset
        lat = base_lat + (row * 0.005)
        lon = base_lon + (col * 0.005)
        
        return {"lat": round(lat, 5), "lon": round(lon, 5)}
    except (ValueError, TypeError):
        return None

def get_trajectory_coordinates(vehicle_id):
    """
    Returns an ordered list of geographical coordinates for a vehicle's trajectory.
    """
    traj = get_vehicle_trajectory(vehicle_id)
    if not traj:
        return []
        
    coords = []
    for cam in traj.get("camera_sequence", []):
        location = get_camera_coordinates(cam)
        if location:
            coords.append({
                "camera_id": cam,
                "lat": location["lat"],
                "lon": location["lon"]
            })
            
    return coords

def get_road_route_coordinates(from_camera_id, to_camera_id):
    """
    Returns the road route geometry (lat/lon points) between two cameras.
    """
    # Import locally to avoid circular dependencies
    from routing import get_road_route
    
    route = get_road_route(from_camera_id, to_camera_id)
    if route and route.get("geometry"):
        return route["geometry"]
    return []

def get_trajectory_route_geometry(vehicle_id):
    """
    Returns the full road route geometry for a vehicle's trajectory by 
    fetching the route geometry per consecutive camera pair in the sequence.
    """
    traj = get_vehicle_trajectory(vehicle_id)
    if not traj:
        return []
        
    cams = traj.get("camera_sequence", [])
    if len(cams) < 2:
        return []
        
    full_geometry = []
    for i in range(len(cams) - 1):
        segment_geom = get_road_route_coordinates(cams[i], cams[i+1])
        full_geometry.extend(segment_geom)
        
    return full_geometry

if __name__ == "__main__":
    # Test gis.py
    print("Coordinates for C17:", get_camera_coordinates("C17"))
    import json
    print("\nTrajectory for V002:")
    print(json.dumps(get_trajectory_coordinates("V002"), indent=2))
    
    # Test route geometry
    print("\nRoad route geometry C17 -> C35 (points):", len(get_road_route_coordinates("C17", "C35")))
