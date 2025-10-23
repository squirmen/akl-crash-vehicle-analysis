#!/usr/bin/env python3
"""
Interactive map: Click crash to highlight its vehicles and dim others.
"""

import csv
import sys
from pathlib import Path
from collections import defaultdict

csv.field_size_limit(sys.maxsize)

print("Loading confirmed matches...")

matches = []
with open('confirmed_crash_vehicles_5min.csv', 'r') as f:
    reader = csv.DictReader(f)
    matches = list(reader)

print(f"Loaded {len(matches)} matches")

# Group by crash
crashes_dict = {}
crash_to_trips = defaultdict(list)

for match in matches:
    crash_id = match['nzta_crash_id']
    trip_id = match['trip_id']

    crash_to_trips[crash_id].append(trip_id)

    if crash_id not in crashes_dict:
        crashes_dict[crash_id] = {
            'crash_id': crash_id,
            'lat': None,
            'lon': None,
            'severity': match['nzta_severity'],
            'location': match['nzta_location'],
            'road': match['nzta_road'],
            'datetime': match['crash_datetime'],
            'vehicles': []
        }
    crashes_dict[crash_id]['vehicles'].append(match)

# Get crash coordinates
from pyproj import Transformer
transformer = Transformer.from_crs("EPSG:2193", "EPSG:4326", always_xy=True)

for crash_id, crash_data in crashes_dict.items():
    match = crash_data['vehicles'][0]
    crash_lon, crash_lat = transformer.transform(
        float(match['crash_x']),
        float(match['crash_y'])
    )
    crash_data['lat'] = crash_lat
    crash_data['lon'] = crash_lon

print(f"Unique crashes: {len(crashes_dict)}")

# Load trip paths
print("\nLoading trip paths...")
vehicle_files = list(Path('data/connected_vehicle').glob('support.NZ_report_withOD-*.csv'))

trip_paths = {}
trips_needed = set([m['trip_id'] for m in matches])

loaded = 0
for vfile in vehicle_files:
    if not trips_needed:
        break

    with open(vfile, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['TripID'] in trips_needed:
                raw_path = row['RawPath'].split(',')
                coords = []
                for point_str in raw_path:
                    parts = point_str.strip().split()
                    if len(parts) == 2:
                        lon, lat = float(parts[0]), float(parts[1])
                        coords.append([lat, lon])

                trip_paths[row['TripID']] = coords
                trips_needed.remove(row['TripID'])
                loaded += 1

                if loaded % 20 == 0:
                    print(f"  Loaded {loaded} trip paths...")

print(f"Loaded {len(trip_paths)} trip paths")

# Create HTML map
print("\nGenerating interactive map...")

all_lats = [c['lat'] for c in crashes_dict.values()]
all_lons = [c['lon'] for c in crashes_dict.values()]
center_lat = sum(all_lats) / len(all_lats)
center_lon = sum(all_lons) / len(all_lons)

severity_colors = {
    'Fatal Crash': '#8B0000',
    'Serious Crash': '#FF4500',
    'Minor Crash': '#FFA500',
    'Non-Injury Crash': '#FFD700'
}

html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Interactive Crash-Vehicle Matches - Auckland 2025</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body {{ margin: 0; padding: 0; }}
        #map {{ height: 100vh; width: 100vw; }}
        .legend {{
            background: white;
            padding: 12px;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            font-size: 13px;
            line-height: 1.6;
        }}
        .legend-title {{
            font-weight: bold;
            margin-bottom: 8px;
            font-size: 15px;
            border-bottom: 2px solid #333;
            padding-bottom: 5px;
        }}
        .severity-dot {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 6px;
            border: 1px solid #333;
        }}
        #clear-selection {{
            position: absolute;
            top: 80px;
            right: 10px;
            z-index: 1000;
            background: white;
            padding: 10px 15px;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            display: none;
        }}
        #clear-selection:hover {{
            background: #f0f0f0;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <div id="clear-selection" onclick="clearSelection()">✕ Clear Selection</div>
    <script>
        var map = L.map('map').setView([{center_lat}, {center_lon}], 11);

        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '© OpenStreetMap contributors © CARTO',
            maxZoom: 20
        }}).addTo(map);

        var selectedCrashId = null;
        var crashMarkers = {{}};
        var pathLayers = {{}};

        // Crash data
        var crashes = [
"""

for crash_id, crash in crashes_dict.items():
    num_vehicles = len(crash['vehicles'])
    color = severity_colors.get(crash['severity'], '#999')
    trip_ids = crash_to_trips[crash_id]

    vehicles_info = []
    for v in crash['vehicles']:
        vehicles_info.append({
            'trip_id': v['trip_id'],
            'vehicle_type': v['vehicle_type'],
            'distance': v['distance_to_crash'],
            'time_diff': v['time_diff_minutes'],
            'score': v['combined_score']
        })

    html += f"""            {{
                lat: {crash['lat']},
                lon: {crash['lon']},
                id: '{crash_id}',
                severity: '{crash['severity']}',
                location: '{crash['location']}',
                road: '{crash['road']}',
                datetime: '{crash['datetime']}',
                color: '{color}',
                num_vehicles: {num_vehicles},
                trip_ids: {trip_ids},
                vehicles: {vehicles_info}
            }},
"""

html += f"""        ];

        // Create crash markers
        crashes.forEach(function(crash) {{
            var marker = L.circleMarker([crash.lat, crash.lon], {{
                radius: 6 + Math.min(crash.num_vehicles * 2, 10),
                fillColor: crash.color,
                color: '#fff',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.8,
                className: 'crash-marker'
            }}).addTo(map);

            var vehicleList = crash.vehicles.map(v =>
                `<li>${{v.vehicle_type}}: ${{v.distance}}m away, ${{v.time_diff}}min diff (score: ${{v.score}})</li>`
            ).join('');

            marker.bindPopup(
                '<div style="min-width: 280px;"><b style="font-size: 15px;">' + crash.severity + '</b><br>' +
                '<b>Location:</b> ' + crash.location + '<br>' +
                '<b>Road:</b> ' + crash.road + '<br>' +
                '<b>Time:</b> ' + crash.datetime + '<br>' +
                '<b>Crash ID:</b> ' + crash.id + '<br>' +
                '<hr><b>Nearby Vehicles (' + crash.num_vehicles + '):</b><ul style="margin: 5px 0; padding-left: 20px;">' +
                vehicleList + '</ul>' +
                '<div style="margin-top: 10px; font-size: 12px; color: #0066cc; cursor: pointer;" ' +
                'onclick="highlightCrash(\\''+crash.id+'\\')">🔍 Highlight vehicles on map</div></div>'
            );

            marker.on('click', function() {{
                highlightCrash(crash.id);
            }});

            crashMarkers[crash.id] = {{
                marker: marker,
                originalStyle: {{
                    fillColor: crash.color,
                    opacity: 1,
                    fillOpacity: 0.8,
                    weight: 2
                }}
            }};
        }});

        // Trip paths
        var tripPaths = {{
"""

for trip_id, coords in trip_paths.items():
    if len(coords) > 0:
        coords_js = str(coords).replace("'", '"')
        html += f"""            '{trip_id}': {coords_js},\n"""

html += f"""        }};

        // Draw paths
        Object.entries(tripPaths).forEach(([tripId, coords]) => {{
            if (coords.length > 1) {{
                var path = L.polyline(coords, {{
                    color: '#0066cc',
                    weight: 2,
                    opacity: 0.2
                }}).addTo(map);

                pathLayers[tripId] = {{
                    layer: path,
                    originalStyle: {{
                        color: '#0066cc',
                        weight: 2,
                        opacity: 0.2
                    }}
                }};
            }}
        }});

        // Highlight crash and its vehicles
        function highlightCrash(crashId) {{
            selectedCrashId = crashId;
            document.getElementById('clear-selection').style.display = 'block';

            var selectedCrash = crashes.find(c => c.id === crashId);
            if (!selectedCrash) return;

            // Dim all crashes
            Object.entries(crashMarkers).forEach(([id, data]) => {{
                if (id === crashId) {{
                    // Highlight selected crash
                    data.marker.setStyle({{
                        fillColor: data.originalStyle.fillColor,
                        opacity: 1,
                        fillOpacity: 1,
                        weight: 4,
                        color: '#fff'
                    }});
                    data.marker.bringToFront();
                }} else {{
                    // Dim other crashes
                    data.marker.setStyle({{
                        fillColor: '#ccc',
                        opacity: 0.3,
                        fillOpacity: 0.3,
                        weight: 1,
                        color: '#999'
                    }});
                }}
            }});

            // Dim all paths
            Object.entries(pathLayers).forEach(([tripId, data]) => {{
                if (selectedCrash.trip_ids.includes(tripId)) {{
                    // Highlight paths for this crash
                    data.layer.setStyle({{
                        color: '#ff00ff',
                        weight: 3,
                        opacity: 0.9
                    }});
                    data.layer.bringToFront();
                }} else {{
                    // Dim other paths
                    data.layer.setStyle({{
                        color: '#ccc',
                        weight: 1,
                        opacity: 0.1
                    }});
                }}
            }});

            // Zoom to crash
            map.setView([selectedCrash.lat, selectedCrash.lon], 14, {{
                animate: true,
                duration: 0.5
            }});
        }}

        // Clear selection
        function clearSelection() {{
            selectedCrashId = null;
            document.getElementById('clear-selection').style.display = 'none';

            // Restore all crashes
            Object.entries(crashMarkers).forEach(([id, data]) => {{
                data.marker.setStyle(data.originalStyle);
            }});

            // Restore all paths
            Object.entries(pathLayers).forEach(([tripId, data]) => {{
                data.layer.setStyle(data.originalStyle);
            }});

            map.setView([{center_lat}, {center_lon}], 11, {{
                animate: true,
                duration: 0.5
            }});
        }}

        // Legend
        var legend = L.control({{position: 'topright'}});
        legend.onAdd = function (map) {{
            var div = L.DomUtil.create('div', 'legend');
            div.innerHTML = '<div class="legend-title">🚗 Interactive Crash Map</div>';
            div.innerHTML += '<b>Total:</b> {len(matches)} vehicle observations<br>';
            div.innerHTML += '<b>Crashes:</b> {len(crashes_dict)} locations<br>';
            div.innerHTML += '<b>Time window:</b> ±5 minutes<br><br>';

            div.innerHTML += '<b>Crash Severity:</b><br>';
            div.innerHTML += '<span class="severity-dot" style="background: #8B0000;"></span> Fatal<br>';
            div.innerHTML += '<span class="severity-dot" style="background: #FF4500;"></span> Serious<br>';
            div.innerHTML += '<span class="severity-dot" style="background: #FFA500;"></span> Minor<br>';
            div.innerHTML += '<span class="severity-dot" style="background: #FFD700;"></span> Non-Injury<br><br>';

            div.innerHTML += '<div style="font-size: 11px; color: #666; border-top: 1px solid #ddd; padding-top: 8px;">';
            div.innerHTML += '<b>✨ Click any crash</b><br>';
            div.innerHTML += '• Highlights vehicle paths<br>';
            div.innerHTML += '• Dims other crashes<br>';
            div.innerHTML += '• Zooms to location<br>';
            div.innerHTML += '<b style="color: #ff00ff;">Magenta</b> = highlighted paths</div>';

            return div;
        }};
        legend.addTo(map);

    </script>
</body>
</html>"""

output_file = 'interactive_crash_map.html'
with open(output_file, 'w') as f:
    f.write(html)

print(f"\n✓ Interactive map created: {output_file}")
print(f"\nFeatures:")
print(f"  • Click any crash marker to highlight its vehicles")
print(f"  • Magenta paths = vehicles for selected crash")
print(f"  • All other crashes/paths dimmed")
print(f"  • Click 'Clear Selection' to reset")
print(f"  • Auto-zooms to selected crash")
print(f"\nOpen in browser and click around!")
