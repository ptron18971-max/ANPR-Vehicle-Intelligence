import os
import json
import time
import requests

CACHE_FILE = "../data/route_cache.json"

def _load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def _save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

def decode_polyline(polyline_str):
    """Decodes a Google Maps encoded polyline into a list of lat/lon dicts."""
    index, lat, lng = 0, 0, 0
    coordinates = []
    changes = {'latitude': 0, 'longitude': 0}
    while index < len(polyline_str):
        for unit in ['latitude', 'longitude']:
            shift, result = 0, 0
            while True:
                if index >= len(polyline_str):
                    break
                byte = ord(polyline_str[index]) - 63
                index += 1
                result |= (byte & 0x1f) << shift
                shift += 5
                if not byte >= 0x20:
                    break
            if (result & 1):
                changes[unit] = ~(result >> 1)
            else:
                changes[unit] = (result >> 1)
        lat += changes['latitude']
        lng += changes['longitude']
        coordinates.append({'lat': lat / 100000.0, 'lon': lng / 100000.0})
    return coordinates

def _get_google_route(from_camera_id, to_camera_id, origin, dest):
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        print(f"Warning: GOOGLE_MAPS_API_KEY not found in environment. Cannot fetch live Google route.")
        return None
        
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "routes.distanceMeters,routes.duration,routes.polyline.encodedPolyline"
    }
    
    payload = {
        "origin": {"location": {"latLng": {"latitude": origin["lat"], "longitude": origin["lon"]}}},
        "destination": {"location": {"latLng": {"latitude": dest["lat"], "longitude": dest["lon"]}}},
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code != 200:
            error_data = {}
            try:
                error_data = response.json()
            except:
                pass
                
            error_msg = error_data.get("error", {}).get("message", response.text)
            status_text = error_data.get("error", {}).get("status", "")
            
            print(f"Google API Error {response.status_code} ({status_text}): {error_msg}")
            return None
            
        data = response.json()
        routes = data.get("routes", [])
        if not routes:
            return None
            
        route = routes[0]
        distance = route.get("distanceMeters")
        duration_str = route.get("duration", "0s")
        duration = int(duration_str.replace("s", "")) if duration_str.endswith("s") else None
        
        encoded_polyline = route.get("polyline", {}).get("encodedPolyline", "")
        decoded_geometry = decode_polyline(encoded_polyline) if encoded_polyline else []
        
        return {
            "from_camera": from_camera_id,
            "to_camera": to_camera_id,
            "routing_distance_meters": distance,
            "duration_seconds": duration,
            "geometry": decoded_geometry,
            "provider": "google"
        }
    except requests.exceptions.RequestException as e:
        print(f"Google Routing API request failed: {e}")
        return None

def _get_osrm_route(from_camera_id, to_camera_id, origin, dest):
    """
    OSRM fallback provider (no API key required).
    Uses the public demo OSRM server.
    Note: OSRM expects coordinates in lon,lat order.
    """
    url = f"http://router.project-osrm.org/route/v1/driving/{origin['lon']},{origin['lat']};{dest['lon']},{dest['lat']}?overview=full&geometries=polyline"
    
    try:
        # Respect OSRM public API usage guidelines with a small delay and headers
        time.sleep(0.5)
        headers = {"User-Agent": "SIH-Person3-Trajectory/1.0"}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"OSRM API Error {response.status_code}: {response.text}")
            return None
            
        data = response.json()
        if data.get("code") != "Ok" or not data.get("routes"):
            print(f"OSRM No routes found: {data.get('code')}")
            return None
            
        route = data["routes"][0]
        distance = route.get("distance")
        duration = route.get("duration")
        
        encoded_polyline = route.get("geometry", "")
        decoded_geometry = decode_polyline(encoded_polyline) if encoded_polyline else []
        
        return {
            "from_camera": from_camera_id,
            "to_camera": to_camera_id,
            "routing_distance_meters": distance,
            "duration_seconds": duration,
            "geometry": decoded_geometry,
            "provider": "osrm"
        }
    except requests.exceptions.RequestException as e:
        print(f"OSRM API request failed: {e}")
        return None

def get_road_route(from_camera_id, to_camera_id):
    """
    Retrieves the road route between two cameras.
    Uses local cache if available, otherwise calls the configured provider.
    """
    from gis import get_camera_coordinates
    
    if from_camera_id == to_camera_id:
        return None
        
    cache_key = f"{from_camera_id}:{to_camera_id}"
    cache = _load_cache()
    
    if cache_key in cache:
        return cache[cache_key]
        
    origin = get_camera_coordinates(from_camera_id)
    dest = get_camera_coordinates(to_camera_id)
    
    if not origin or not dest:
        raise ValueError(f"Invalid camera coordinates for {from_camera_id} or {to_camera_id}")
        
    provider = os.environ.get("ROUTING_PROVIDER", "osrm").lower()
    
    if provider == "google":
        result = _get_google_route(from_camera_id, to_camera_id, origin, dest)
    else:
        result = _get_osrm_route(from_camera_id, to_camera_id, origin, dest)
        
    if result:
        result["timestamp"] = time.time()
        cache[cache_key] = result
        _save_cache(cache)
        
    return result

def enrich_edge_with_route(from_camera_id, to_camera_id):
    """Gets routing info to optionally enrich a graph edge."""
    return get_road_route(from_camera_id, to_camera_id)

def enrich_camera_graph(graph_path="../../docs/contracts/camera_graph.json"):
    """
    Batch function to enrich the canonical camera graph with road routing data.
    Does not blindly overwrite existing min/avg/max time semantics.
    Adds `routing_distance_meters` to the edge schema as an enrichment layer.
    """
    print(f"Starting batch graph enrichment using Routes API...")
    if not os.path.exists(graph_path):
        print(f"Graph file not found: {graph_path}")
        return
        
    with open(graph_path, "r") as f:
        graph_data = json.load(f)
        
    edges = graph_data.get("edges", [])
    updated = 0
    errors = 0
    
    for edge in edges:
        from_cam = edge.get("from_camera")
        to_cam = edge.get("to_camera")
        
        try:
            route_info = get_road_route(from_cam, to_cam)
            if route_info:
                edge["routing_distance_meters"] = route_info["routing_distance_meters"]
                updated += 1
            else:
                errors += 1
        except Exception as e:
            print(f"Failed to enrich edge {from_cam}->{to_cam}: {e}")
            errors += 1
            
        time.sleep(0.1)  # Throttle
        
    with open(graph_path, "w") as f:
         json.dump(graph_data, f, indent=2)
         
    print(f"Enrichment complete. Updated: {updated}, Errors/Skipped: {errors}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) == 3:
        c1 = sys.argv[1]
        c2 = sys.argv[2]
        
        try:
            route = get_road_route(c1, c2)
            if route:
                print(f"From: {route['from_camera']}")
                print(f"To: {route['to_camera']}")
                print(f"Road distance: {route['routing_distance_meters']} m")
                print(f"Estimated duration: {route['duration_seconds']} sec")
                print(f"Geometry points: {len(route['geometry'])}")
                print(f"Provider: {route['provider']}")
            else:
                print(f"Could not retrieve route for {c1} -> {c2}")
        except Exception as e:
            print(f"Error: {e}")
            
    else:
        print("Usage: python routing.py <FROM_CAMERA> <TO_CAMERA>")
