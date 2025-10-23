#!/usr/bin/env python3
"""
Map all 188 confirmed crash-involved/witness vehicles on a single map.
Light basemap with crash markers and vehicle paths.
"""

import csv
import sys
from pathlib import Path
from collections import defaultdict

csv.field_size_limit(sys.maxsize)

print("Loading confirmed matches...")

# Load all confirmed matches
matches = []
with open('confirmed_crash_vehicles_5min.csv', 'r') as f:
    reader = csv.DictReader(f)
    matches = list(reader)

print(f"Loaded {len(matches)} matches")

# Group by crash
crashes_dict = {}
for match in matches:
    crash_id = match['nzta_crash_id']
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

# Get crash coordinates (need to convert NZTM to WGS84)
from pyproj import Transformer
transformer = Transformer.from_crs("EPSG:2193", "EPSG:4326", always_xy=True)

for crash_id, crash_data in crashes_dict.items():
    # Use first match to get crash coords
    match = crash_data['vehicles'][0]
    crash_lon, crash_lat = transformer.transform(
        float(match['crash_x']),
        float(match['crash_y'])
    )
    crash_data['lat'] = crash_lat
    crash_data['lon'] = crash_lon

print(f"Unique crashes: {len(crashes_dict)}")

# Load trip data for paths
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
                # Parse path
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
                    print(f"  Loaded {loaded}/{len(trip_paths)} trip paths...")

print(f"Loaded {len(trip_paths)} trip paths")

# Create HTML map
print("\nGenerating map...")

# Calculate center point
all_lats = [c['lat'] for c in crashes_dict.values()]
all_lons = [c['lon'] for c in crashes_dict.values()]
center_lat = sum(all_lats) / len(all_lats)
center_lon = sum(all_lons) / len(all_lons)

# Color by severity
severity_colors = {
    'Fatal Crash': '#8B0000',
    'Serious Crash': '#FF4500',
    'Minor Crash': '#FFA500',
    'Non-Injury Crash': '#FFD700'
}

html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Confirmed Crash-Vehicle Matches - Auckland 2025</title>
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
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        // Light basemap
        var map = L.map('map').setView([{center_lat}, {center_lon}], 11);

        // CartoDB Positron - light, clean basemap with good street info
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '© OpenStreetMap contributors © CARTO',
            maxZoom: 20
        }}).addTo(map);

        // Crash data
        var crashes = [
"""

for crash_id, crash in crashes_dict.items():
    num_vehicles = len(crash['vehicles'])
    color = severity_colors.get(crash['severity'], '#999')

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
                vehicles: {vehicles_info}
            }},
"""

html += f"""        ];

        // Add crash markers
        crashes.forEach(function(crash) {{
            var marker = L.circleMarker([crash.lat, crash.lon], {{
                radius: 6 + Math.min(crash.num_vehicles * 2, 10),
                fillColor: crash.color,
                color: '#fff',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.8
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
                vehicleList + '</ul></div>'
            );
        }});

        // Add trip paths
        var tripPaths = {{
"""

for trip_id, coords in trip_paths.items():
    if len(coords) > 0:
        coords_js = str(coords).replace("'", '"')
        html += f"""            '{trip_id}': {coords_js},\n"""

html += f"""        }};

        // Draw paths with low opacity
        Object.entries(tripPaths).forEach(([tripId, coords]) => {{
            if (coords.length > 1) {{
                L.polyline(coords, {{
                    color: '#0066cc',
                    weight: 1,
                    opacity: 0.15
                }}).addTo(map);
            }}
        }});

        // Add legend
        var legend = L.control({{position: 'topright'}});
        legend.onAdd = function (map) {{
            var div = L.DomUtil.create('div', 'legend');
            div.innerHTML = '<div class="legend-title">🚗 Confirmed Crash-Vehicle Matches</div>';
            div.innerHTML += '<b>Total:</b> {len(matches)} vehicle observations<br>';
            div.innerHTML += '<b>Crashes:</b> {len(crashes_dict)} locations<br>';
            div.innerHTML += '<b>Time window:</b> ±5 minutes<br><br>';

            div.innerHTML += '<b>Crash Severity:</b><br>';
            div.innerHTML += '<span class="severity-dot" style="background: #8B0000;"></span> Fatal<br>';
            div.innerHTML += '<span class="severity-dot" style="background: #FF4500;"></span> Serious<br>';
            div.innerHTML += '<span class="severity-dot" style="background: #FFA500;"></span> Minor<br>';
            div.innerHTML += '<span class="severity-dot" style="background: #FFD700;"></span> Non-Injury<br><br>';

            div.innerHTML += '<div style="font-size: 11px; color: #666;">Marker size = # of vehicles<br>';
            div.innerHTML += 'Blue lines = vehicle paths<br>';
            div.innerHTML += 'Click markers for details</div>';

            return div;
        }};
        legend.addTo(map);

        // Click to zoom
        map.on('click', function(e) {{
            // Optional: add functionality
        }});

    </script>
</body>
</html>"""

output_file = 'all_confirmed_crashes_map.html'
with open(output_file, 'w') as f:
    f.write(html)

print(f"\n✓ Map created: {output_file}")
print(f"\nMap features:")
print(f"  • Light CartoDB basemap with street details")
print(f"  • {len(crashes_dict)} crash markers (color-coded by severity)")
print(f"  • {len(trip_paths)} vehicle path traces (semi-transparent blue)")
print(f"  • Marker size shows number of vehicles")
print(f"  • Click any crash for vehicle details")
print(f"\nOpen in browser to explore!")
