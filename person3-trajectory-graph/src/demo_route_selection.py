import json
import math
import networkx as nx
import os

from gis import get_camera_coordinates
from routing import get_road_route

def run_demos():
    nodes = ['C01', 'C02', 'C03', 'C04', 'C07', 'C08', 'C09', 'C10', 'C14', 'C15']
    
    with open('../../docs/contracts/camera_graph.json', 'r') as f:
        graph_data = json.load(f)
        
    G = nx.DiGraph()
    for e in graph_data['edges']:
        u = e['from_camera']
        v = e['to_camera']
        if u in nodes and v in nodes:
            route = get_road_route(u, v)
            if not route:
                continue
                
            osrm_dist = route['routing_distance_meters']
            osrm_dur = route['duration_seconds']
            
            exp_avg = osrm_dur
            exp_min = osrm_dur * 0.7
            exp_max = osrm_dur * 2.5
            
            G.add_edge(u, v, 
                       osrm_distance=osrm_dist, 
                       osrm_duration=osrm_dur,
                       exp_min=exp_min,
                       exp_avg=exp_avg,
                       exp_max=exp_max,
                       geometry=route['geometry'])

    start = 'C01'
    dest = 'C10'
    
    paths = list(nx.all_simple_paths(G, start, dest))
    candidates = []
    
    for p in paths:
        dist = 0
        p_min = 0
        p_avg = 0
        p_max = 0
        
        for i in range(len(p)-1):
            u, v = p[i], p[i+1]
            data = G[u][v]
            dist += data['osrm_distance']
            p_min += data['exp_min']
            p_avg += data['exp_avg']
            p_max += data['exp_max']
            
        candidates.append({
            'sequence': p,
            'distance': dist,
            'min_time': p_min,
            'avg_time': p_avg,
            'max_time': p_max
        })
        
    candidates.sort(key=lambda x: x['distance'])
    shortest_path_seq = candidates[0]['sequence']

    # Demos
    demos = [
        {
            "title": "DEMO 1 - FAST / SHORTEST ROUTE",
            "desc": "Short elapsed time. Shortest physical route selected.",
            "observed_time": 365,
            "filename": "demo1_fast_route.html"
        },
        {
            "title": "DEMO 2 - TEMPORAL DETOUR",
            "desc": "Longer elapsed time. Medium detour route selected.",
            "observed_time": 520,
            "filename": "demo2_detour.html"
        },
        {
            "title": "DEMO 3 - EVEN LONGER TEMPORAL DETOUR",
            "desc": "Extremely long elapsed time. Longest detour route selected.",
            "observed_time": 650,
            "filename": "demo3_long_detour.html"
        }
    ]
    
    for s in demos:
        print(f"================ {s['title']} ================")
        print(f"{s['desc']}")
        print(f"Start Camera: {start} [CONFIRMED]")
        print(f"Destination Camera: {dest} [CONFIRMED]")
        print(f"Observed elapsed time: {s['observed_time']} seconds")
        print("Note: Temporal envelope is [DEMO/SYNTHETIC ASSUMED]\n")
        
        best_candidate = None
        best_error = float('inf')
        
        for i, c in enumerate(candidates):
            error = abs(s['observed_time'] - c['avg_time'])
            
            if c['min_time'] <= s['observed_time'] <= c['max_time']:
                status = "FEASIBLE"
                if error < best_error:
                    best_error = error
                    best_candidate = c
            else:
                status = "INFEASIBLE (Out of bounds)"
                
            print(f"Candidate {i+1}: {' -> '.join(c['sequence'])}")
            print(f"  Distance: {c['distance']:.1f} m")
            print(f"  Expected Time [ASSUMED AVG]: {c['avg_time']:.1f} s")
            print(f"  Temporal Error: {error:.1f} s")
            print(f"  Status: {status}\n")
            
        print("=> SELECTED PATH:")
        if best_candidate:
            seq = " -> ".join(best_candidate['sequence'])
            inferred = best_candidate['sequence'][1:-1]
            print(f"  {seq}")
            print(f"  Why selected: It has the lowest temporal error ({best_error:.1f}s) within feasible bounds.")
            print(f"  Is Shortest Distance Path? {'Yes' if best_candidate['sequence'] == shortest_path_seq else 'No'}")
            print(f"  Confirmed Cameras: {start}, {dest}")
            print(f"  Inferred Cameras: {inferred}\n\n")
            
            generate_html(nodes, G, candidates, s, best_candidate)
        else:
            print("NONE\n\n")

def generate_html(nodes, G, candidates, demo_info, best_candidate):
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{demo_info['title']}</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body {{ margin: 0; padding: 0; font-family: sans-serif; }}
        #map {{ height: 100vh; width: 100%; }}
        #panel {{
            position: absolute; top: 10px; right: 10px; z-index: 1000;
            background: white; padding: 15px; border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
            max-width: 400px;
        }}
    </style>
</head>
<body>
<div id="panel">
    <h3>{demo_info['title']}</h3>
    <p><strong>Observed Time:</strong> {demo_info['observed_time']} seconds</p>
    <p><em>{demo_info['desc']}</em></p>
    <hr>
    <h4>Legend:</h4>
    <div style="color: red; font-weight: bold;">&#9644; Selected Path (Temporally Plausible)</div>
    <div style="color: gray;">&#9644; Alternative Paths</div>
    <div style="color: blue; font-weight: bold;">&#9679; CONFIRMED Camera Nodes</div>
    <div style="color: orange; font-weight: bold;">&#9679; INFERRED Camera Nodes</div>
    <p style="font-size: 0.8em; color: #555;">[DEMO/SYNTHETIC coordinates and times]</p>
</div>
<div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
    var map = L.map('map').setView([12.98, 77.61], 14);
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{ maxZoom: 19 }}).addTo(map);

"""
    
    selected_seq = best_candidate['sequence']
    start = selected_seq[0]
    dest = selected_seq[-1]

    for n in nodes:
        coords = get_camera_coordinates(n)
        if n in [start, dest]:
            color = 'blue'
            label = f"<b>{n}</b> [CONFIRMED]"
        elif n in selected_seq:
            color = 'orange'
            label = f"<b>{n}</b> [INFERRED]"
        else:
            color = 'black'
            label = f"<b>{n}</b>"
            
        html += f"    L.circleMarker([{coords['lat']}, {coords['lon']}], {{color: '{color}', radius: 6, fillOpacity:1}}).addTo(map).bindPopup('{label}');\n"

    for c in candidates:
        if c['sequence'] == selected_seq:
            continue
        geom = []
        for i in range(len(c['sequence'])-1):
            u, v = c['sequence'][i], c['sequence'][i+1]
            for p in G[u][v]['geometry']:
                geom.append([p['lat'], p['lon']])
        html += f"    L.polyline({geom}, {{color: 'gray', weight: 3, opacity: 0.5}}).addTo(map);\n"

    geom = []
    for i in range(len(selected_seq)-1):
        u, v = selected_seq[i], selected_seq[i+1]
        for p in G[u][v]['geometry']:
            geom.append([p['lat'], p['lon']])
    html += f"    L.polyline({geom}, {{color: 'red', weight: 6, opacity: 0.9}}).addTo(map).bindPopup('Selected Path');\n"
    
    html += "</script></body></html>"

    path = f"../map_test/{demo_info['filename']}"
    with open(path, "w") as f:
        f.write(html)
    print(f"Generated visualization: {path}")

if __name__ == '__main__':
    run_demos()
