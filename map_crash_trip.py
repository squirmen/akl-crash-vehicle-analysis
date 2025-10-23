#!/usr/bin/env python3
"""Map trip with crash location"""

import csv
import sys

csv.field_size_limit(sys.maxsize)

# Get trip data
trip_id = "d9ONScAlfHuZ3DJWfAMm2g=="
crash_id = "2025341038"

print(f"Loading trip {trip_id}...")

# Load trip from vehicle data
trip_data = None
with open('data/connected_vehicle/support.NZ_report_withOD-c2b9c237370b552746703651-000000000054.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['TripID'] == trip_id:
            trip_data = row
            break

if not trip_data:
    print("Trip not found!")
    sys.exit(1)

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

# Get crash data
with open('confirmed_crash_vehicles_5min.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['nzta_crash_id'] == crash_id:
            crash_data = row
            break

crash_lat = float(crash_data['crash_y']) if 'crash_y' in crash_data else None
crash_lon = float(crash_data['crash_x']) if 'crash_x' in crash_data else None

# Need to convert NZTM to lat/lon for crash
from pyproj import Transformer
transformer = Transformer.from_crs("EPSG:2193", "EPSG:4326", always_xy=True)
crash_lon_wgs, crash_lat_wgs = transformer.transform(
    float(crash_data['crash_x']),
    float(crash_data['crash_y'])
)

print(f"Creating map with {len(coords)} GPS points...")

# Create HTML map
html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Trip {trip_id} - Crash {crash_id}</title>
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
        }}
        .legend-title {{ font-weight: bold; margin-bottom: 5px; }}
        .legend-scale {{ margin-top: 5px; }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        var map = L.map('map').setView([{coords[0][0]}, {coords[0][1]}], 13);

        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors'
        }}).addTo(map);

        // Speed color function (km/h)
        function getColor(speed) {{
            // Convert mph to km/h
            var kmh = speed * 1.60934;
            return kmh > 100 ? '#00ff00' :
                   kmh > 80  ? '#66ff33' :
                   kmh > 60  ? '#ccff33' :
                   kmh > 40  ? '#ffff00' :
                   kmh > 20  ? '#ffcc00' :
                   kmh > 10  ? '#ff6600' :
                                '#ff0000';
        }}

        // Add trip points
        var points = [
"""

# Add GPS points
for i, ((lat, lon), ts, speed) in enumerate(zip(coords, timestamps, speeds)):
    speed_val = float(speed) if speed else 0
    html += f"""            {{lat: {lat}, lon: {lon}, time: '{ts}', speed: {speed_val}, idx: {i}}},\n"""

html += f"""        ];

        points.forEach(function(point, idx) {{
            var color = getColor(point.speed);
            var marker = L.circleMarker([point.lat, point.lon], {{
                radius: 4,
                fillColor: color,
                color: '#000',
                weight: 1,
                opacity: 0.8,
                fillOpacity: 0.8
            }}).addTo(map);

            marker.bindPopup(
                '<b>Point ' + point.idx + '</b><br>' +
                'Time: ' + point.time + '<br>' +
                'Speed: ' + point.speed + ' mph (' + (point.speed * 1.60934).toFixed(1) + ' km/h)'
            );
        }});

        // Draw path
        var latlngs = points.map(p => [p.lat, p.lon]);
        var polyline = L.polyline(latlngs, {{color: 'blue', weight: 2, opacity: 0.5}}).addTo(map);

        // Add crash marker
        var crashMarker = L.marker([{crash_lat_wgs}, {crash_lon_wgs}], {{
            icon: L.icon({{
                iconUrl: 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0Ij48cGF0aCBmaWxsPSJyZWQiIGQ9Ik0xMiAyQzguMTMgMiA1IDUuMTMgNSA5YzAgNS4yNSA3IDEzIDcgMTNzNy03Ljc1IDctMTNjMC0zLjg3LTMuMTMtNy03LTd6bTAgOS41Yy0xLjM4IDAtMi41LTEuMTItMi41LTIuNXMxLjEyLTIuNSAyLjUtMi41IDIuNSAxLjEyIDIuNSAyLjUtMS4xMiAyLjUtMi41IDIuNXoiLz48L3N2Zz4=',
                iconSize: [32, 32],
                iconAnchor: [16, 32],
                popupAnchor: [0, -32]
            }})
        }}).addTo(map);

        crashMarker.bindPopup(
            '<b>CRASH LOCATION</b><br>' +
            '<b>Crash ID:</b> {crash_id}<br>' +
            '<b>Time:</b> {crash_data["crash_datetime"]}<br>' +
            '<b>Severity:</b> {crash_data["nzta_severity"]}<br>' +
            '<b>Location:</b> {crash_data["nzta_location"]}<br>' +
            '<b>Road:</b> {crash_data["nzta_road"]}<br>' +
            '<hr>' +
            '<b>Vehicle at crash:</b><br>' +
            'Trip: {trip_id[:20]}...<br>' +
            'Vehicle: {crash_data["vehicle_id"][:20]}...<br>' +
            'Type: {crash_data["vehicle_type"]}<br>' +
            'Distance: {crash_data["distance_to_crash"]}m<br>' +
            'Time diff: {crash_data["time_diff_minutes"]} min<br>' +
            'Speed at crash: {crash_data.get("speed_at_point", "N/A")} mph<br>' +
            'Match score: {crash_data["combined_score"]}/100'
        ).openPopup();

        // Fit bounds
        map.fitBounds(polyline.getBounds());

        // Add legend
        var legend = L.control({{position: 'topright'}});
        legend.onAdd = function (map) {{
            var div = L.DomUtil.create('div', 'legend');
            div.innerHTML = '<div class="legend-title">Speed (km/h)</div>';
            div.innerHTML += '<div style="background: #00ff00; width: 20px; height: 15px; display: inline-block;"></div> > 100<br>';
            div.innerHTML += '<div style="background: #66ff33; width: 20px; height: 15px; display: inline-block;"></div> 80-100<br>';
            div.innerHTML += '<div style="background: #ccff33; width: 20px; height: 15px; display: inline-block;"></div> 60-80<br>';
            div.innerHTML += '<div style="background: #ffff00; width: 20px; height: 15px; display: inline-block;"></div> 40-60<br>';
            div.innerHTML += '<div style="background: #ffcc00; width: 20px; height: 15px; display: inline-block;"></div> 20-40<br>';
            div.innerHTML += '<div style="background: #ff6600; width: 20px; height: 15px; display: inline-block;"></div> 10-20<br>';
            div.innerHTML += '<div style="background: #ff0000; width: 20px; height: 15px; display: inline-block;"></div> < 10<br>';
            div.innerHTML += '<hr><div style="font-size: 12px;"><b>Trip Info:</b><br>';
            div.innerHTML += 'Duration: {trip_data["TravelTimeMinutes"]} min<br>';
            div.innerHTML += 'Distance: {float(trip_data["TravelDistanceMiles"]):.1f} miles<br>';
            div.innerHTML += 'Max speed: {trip_data["SpeedMax"]} mph<br>';
            div.innerHTML += 'Avg speed: {trip_data["SpeedAvg"]} mph</div>';
            return div;
        }};
        legend.addTo(map);

        // Add start/end markers
        L.marker([{coords[0][0]}, {coords[0][1]}], {{
            icon: L.icon({{
                iconUrl: 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0Ij48Y2lyY2xlIGN4PSIxMiIgY3k9IjEyIiByPSI4IiBmaWxsPSJncmVlbiIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIi8+PHRleHQgeD0iMTIiIHk9IjE2IiBmb250LXNpemU9IjEyIiBmaWxsPSJ3aGl0ZSIgdGV4dC1hbmNob3I9Im1pZGRsZSI+UzwvdGV4dD48L3N2Zz4=',
                iconSize: [24, 24],
                iconAnchor: [12, 12]
            }})
        }}).addTo(map).bindPopup('<b>START</b><br>Time: {timestamps[0]}');

        L.marker([{coords[-1][0]}, {coords[-1][1]}], {{
            icon: L.icon({{
                iconUrl: 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0Ij48Y2lyY2xlIGN4PSIxMiIgY3k9IjEyIiByPSI4IiBmaWxsPSJibGFjayIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIi8+PHRleHQgeD0iMTIiIHk9IjE2IiBmb250LXNpemU9IjEyIiBmaWxsPSJ3aGl0ZSIgdGV4dC1hbmNob3I9Im1pZGRsZSI+RTwvdGV4dD48L3N2Zz4=',
                iconSize: [24, 24],
                iconAnchor: [12, 12]
            }})
        }}).addTo(map).bindPopup('<b>END</b><br>Time: {timestamps[-1]}');

    </script>
</body>
</html>"""

# Write HTML file
output_file = f'trip_map_{trip_id[:10]}.html'
with open(output_file, 'w') as f:
    f.write(html)

print(f"✓ Map created: {output_file}")
print(f"\nOpen in browser to view interactive map with:")
print(f"  • {len(coords)} GPS points color-coded by speed")
print(f"  • Red crash marker at {crash_data['nzta_location']}")
print(f"  • Click any point for details")
