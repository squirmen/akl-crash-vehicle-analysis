#!/usr/bin/env python3
"""Map the LCV that stayed at crash scene for 13 minutes"""

import csv
import sys
from datetime import datetime

csv.field_size_limit(sys.maxsize)

trip_id = "rLIyF5Bi7LvXW+GZSDgtXA=="
crash_id = "2025315483"

print(f"Loading trip {trip_id}...")

# Find the trip in vehicle data files
from pathlib import Path
vehicle_files = list(Path('data/connected_vehicle').glob('support.NZ_report_withOD-*.csv'))

trip_data = None
for vfile in vehicle_files:
    with open(vfile, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['TripID'] == trip_id:
                trip_data = row
                break
    if trip_data:
        break

if not trip_data:
    print("Trip not found!")
    sys.exit(1)

# Get crash data
with open('crash_WITNESSES.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['trip_id'] == trip_id:
            crash_data = row
            break

# Parse paths
timestamps = trip_data['TimestampPath'].split(',')
raw_path = trip_data['RawPath'].split(',')
speeds = trip_data['SpeedPath'].split(',')

# Parse coordinates
coords = []
for point_str in raw_path:
    parts = point_str.strip().split()
    if len(parts) == 2:
        lon, lat = float(parts[0]), float(parts[1])
        coords.append((lat, lon))

# Get crash location
from pyproj import Transformer
transformer_to_wgs = Transformer.from_crs("EPSG:2193", "EPSG:4326", always_xy=True)
transformer_to_nztm = Transformer.from_crs("EPSG:4326", "EPSG:2193", always_xy=True)

crash_lon_wgs, crash_lat_wgs = transformer_to_wgs.transform(
    float(crash_data['crash_x']),
    float(crash_data['crash_y'])
)

# Find crash point index
crash_idx = int(crash_data['closest_point_idx'])
crash_time = datetime.strptime(crash_data['crash_datetime'], "%Y-%m-%d %H:%M")

# Find points near crash (within 50m, around crash time ±15 min)
crash_scene_points = []
for i in range(min(len(coords), len(timestamps))):
    try:
        ts = datetime.strptime(timestamps[i].split('.')[0], "%Y-%m-%d %H:%M:%S")
        time_diff_min = abs((ts - crash_time).total_seconds() / 60)

        # Within ±15 minutes of crash
        if time_diff_min <= 15:
            # Calculate distance using WGS84 to NZTM
            # coords are (lat, lon) but transform expects (lon, lat)
            px, py = transformer_to_nztm.transform(coords[i][1], coords[i][0])
            crash_x = float(crash_data['crash_x'])
            crash_y = float(crash_data['crash_y'])
            dist = ((px - crash_x)**2 + (py - crash_y)**2)**0.5

            if dist < 50:
                crash_scene_points.append(i)
    except:
        pass

print(f"Creating map with {len(coords)} GPS points...")
print(f"Found {len(crash_scene_points)} points at crash scene (±15min of crash)")

# Create HTML map
html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Crash-Involved Vehicle - Trip {trip_id[:10]}</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body {{ margin: 0; padding: 0; }}
        #map {{ height: 100vh; width: 100vw; }}
        .legend {{
            background: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 0 15px rgba(0,0,0,0.2);
            font-size: 12px;
        }}
        .legend-title {{ font-weight: bold; margin-bottom: 5px; font-size: 14px; }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        var map = L.map('map').setView([{coords[crash_idx][0]}, {coords[crash_idx][1]}], 16);

        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors'
        }}).addTo(map);

        function getColor(speed, atCrashScene) {{
            if (atCrashScene) return '#ff00ff';  // Magenta for crash scene points
            var kmh = speed * 1.60934;
            return kmh > 100 ? '#00ff00' :
                   kmh > 80  ? '#66ff33' :
                   kmh > 60  ? '#ccff33' :
                   kmh > 40  ? '#ffff00' :
                   kmh > 20  ? '#ffcc00' :
                   kmh > 10  ? '#ff6600' :
                                '#ff0000';
        }}

        var crashSceneIndices = {crash_scene_points};

        var points = [
"""

# Add GPS points
for i, ((lat, lon), ts, speed) in enumerate(zip(coords, timestamps, speeds)):
    try:
        speed_val = float(speed) if speed and speed != 'null' else 0
    except:
        speed_val = 0
    at_scene = 'true' if i in crash_scene_points else 'false'
    html += f"""            {{lat: {lat}, lon: {lon}, time: '{ts}', speed: {speed_val}, idx: {i}, atScene: {at_scene}}},\n"""

html += f"""        ];

        points.forEach(function(point, idx) {{
            var color = getColor(point.speed, point.atScene);
            var radius = point.atScene ? 8 : 4;  // Larger for crash scene points
            var marker = L.circleMarker([point.lat, point.lon], {{
                radius: radius,
                fillColor: color,
                color: point.atScene ? '#ff00ff' : '#000',
                weight: point.atScene ? 2 : 1,
                opacity: 1,
                fillOpacity: point.atScene ? 1 : 0.8
            }}).addTo(map);

            var crashInfo = point.atScene ? '<br><b style="color: #ff00ff;">AT CRASH SCENE</b>' : '';
            marker.bindPopup(
                '<b>Point ' + point.idx + '</b>' + crashInfo + '<br>' +
                'Time: ' + point.time + '<br>' +
                'Speed: ' + point.speed + ' mph (' + (point.speed * 1.60934).toFixed(1) + ' km/h)'
            );

            if (point.atScene) {{
                marker.bindTooltip('At crash scene', {{permanent: false, direction: 'top'}});
            }}
        }});

        // Draw path
        var latlngs = points.map(p => [p.lat, p.lon]);
        var polyline = L.polyline(latlngs, {{color: 'blue', weight: 2, opacity: 0.5}}).addTo(map);

        // Add crash marker
        var crashMarker = L.marker([{crash_lat_wgs}, {crash_lon_wgs}], {{
            icon: L.icon({{
                iconUrl: 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIzMiIgaGVpZ2h0PSIzMiIgdmlld0JveD0iMCAwIDI0IDI0Ij48cGF0aCBmaWxsPSJyZWQiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMSIgZD0iTTEyIDJDOC4xMyAyIDUgNS4xMyA1IDljMCA1LjI1IDcgMTMgNyAxM3M3LTcuNzUgNy0xM2MwLTMuODctMy4xMy03LTctN3ptMCA5LjVjLTEuMzggMC0yLjUtMS4xMi0yLjUtMi41czEuMTItMi41IDIuNS0yLjUgMi41IDEuMTIgMi41IDIuNS0xLjEyIDIuNS0yLjUgMi41eiIvPjwvc3ZnPg==',
                iconSize: [40, 40],
                iconAnchor: [20, 40],
                popupAnchor: [0, -40]
            }})
        }}).addTo(map);

        crashMarker.bindPopup(
            '<div style="min-width: 250px;"><b style="font-size: 16px;">🚗 CRASH LOCATION</b><br><hr>' +
            '<b>Crash ID:</b> {crash_id}<br>' +
            '<b>Time:</b> {crash_data["crash_datetime"]}<br>' +
            '<b>Severity:</b> {crash_data["nzta_severity"]}<br>' +
            '<b>Location:</b> {crash_data["nzta_location"]}<br>' +
            '<b>Road:</b> {crash_data["nzta_road"]}<br>' +
            '<hr><b style="color: #ff00ff;">VEHICLE INVOLVEMENT:</b><br>' +
            'Type: LCV<br>' +
            'Distance: {crash_data["distance_to_crash"]}m<br>' +
            'Time at scene: <b>{crash_data["time_at_scene_minutes"]} minutes</b><br>' +
            'GPS points at scene: <b>{crash_data["num_points_at_scene"]}</b><br>' +
            'Avg speed at scene: <b>{crash_data["avg_speed_at_scene"]} mph</b><br>' +
            '<hr><b>⚠️ Vehicle likely INVOLVED or stopped to assist</b></div>'
        ).openPopup();

        // Add legend
        var legend = L.control({{position: 'topright'}});
        legend.onAdd = function (map) {{
            var div = L.DomUtil.create('div', 'legend');
            div.innerHTML = '<div class="legend-title">🚗 Crash-Involved Vehicle</div><hr>';
            div.innerHTML += '<div style="background: #ff00ff; width: 16px; height: 16px; border-radius: 50%; display: inline-block; border: 2px solid #ff00ff;"></div> <b>At crash scene ({len(crash_scene_points)} points)</b><br><br>';
            div.innerHTML += '<div class="legend-title">Speed (km/h)</div>';
            div.innerHTML += '<div style="background: #00ff00; width: 15px; height: 15px; display: inline-block;"></div> > 100<br>';
            div.innerHTML += '<div style="background: #ccff33; width: 15px; height: 15px; display: inline-block;"></div> 60-80<br>';
            div.innerHTML += '<div style="background: #ffff00; width: 15px; height: 15px; display: inline-block;"></div> 40-60<br>';
            div.innerHTML += '<div style="background: #ffcc00; width: 15px; height: 15px; display: inline-block;"></div> 20-40<br>';
            div.innerHTML += '<div style="background: #ff0000; width: 15px; height: 15px; display: inline-block;"></div> < 10<br>';
            div.innerHTML += '<hr><b>Trip Summary:</b><br>';
            div.innerHTML += 'Duration: {trip_data["TravelTimeMinutes"]} min<br>';
            div.innerHTML += 'Distance: {float(trip_data["TravelDistanceMiles"]):.1f} miles<br>';
            div.innerHTML += 'Max speed: {trip_data["SpeedMax"]} mph<br>';
            div.innerHTML += '<br><b style="color: red;">⚠️ Stopped at crash scene<br>for {crash_data["time_at_scene_minutes"]} minutes</b>';
            return div;
        }};
        legend.addTo(map);

        // Add start/end markers
        L.marker([{coords[0][0]}, {coords[0][1]}], {{
            icon: L.icon({{
                iconUrl: 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCI+PGNpcmNsZSBjeD0iMTIiIGN5PSIxMiIgcj0iOCIgZmlsbD0iZ3JlZW4iIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIvPjx0ZXh0IHg9IjEyIiB5PSIxNiIgZm9udC1zaXplPSIxMiIgZmlsbD0id2hpdGUiIHRleHQtYW5jaG9yPSJtaWRkbGUiPnM8L3RleHQ+PC9zdmc+',
                iconSize: [24, 24],
                iconAnchor: [12, 12]
            }})
        }}).addTo(map).bindPopup('<b>START</b><br>Time: {timestamps[0]}');

        L.marker([{coords[-1][0]}, {coords[-1][1]}], {{
            icon: L.icon({{
                iconUrl: 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCI+PGNpcmNsZSBjeD0iMTIiIGN5PSIxMiIgcj0iOCIgZmlsbD0iYmxhY2siIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIvPjx0ZXh0IHg9IjEyIiB5PSIxNiIgZm9udC1zaXplPSIxMiIgZmlsbD0id2hpdGUiIHRleHQtYW5jaG9yPSJtaWRkbGUiPmU8L3RleHQ+PC9zdmc+',
                iconSize: [24, 24],
                iconAnchor: [12, 12]
            }})
        }}).addTo(map).bindPopup('<b>END</b><br>Time: {timestamps[-1]}');

        // Fit to crash scene
        var crashSceneBounds = L.latLngBounds(
            points.filter(p => p.atScene).map(p => [p.lat, p.lon])
        );
        if (crashSceneBounds.isValid()) {{
            map.fitBounds(crashSceneBounds.pad(0.3));
        }}

    </script>
</body>
</html>"""

# Write HTML file
output_file = f'crash_involved_LCV_{trip_id[:10]}.html'
with open(output_file, 'w') as f:
    f.write(html)

print(f"\n✓ Map created: {output_file}")
print(f"\nMap features:")
print(f"  • {len(coords)} total GPS points")
print(f"  • {len(crash_scene_points)} MAGENTA points = at crash scene")
print(f"  • Red crash marker with involvement details")
print(f"  • Vehicle stayed at scene for {crash_data['time_at_scene_minutes']} minutes")
print(f"\n⚠️  This vehicle shows strong evidence of crash involvement!")
