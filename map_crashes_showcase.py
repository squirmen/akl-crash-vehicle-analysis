#!/usr/bin/env python3
"""
SHOWCASE MAP - All the bells and whistles!
- Click crash to highlight vehicles
- Show GPS points along path
- Animated transitions
- Speed heatmap on paths
- Statistics panel
"""

import csv
import sys
import json
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

# Load trip paths WITH SPEEDS
print("\nLoading trip paths with speed data...")
vehicle_files = list(Path('data/connected_vehicle').glob('support.NZ_report_withOD-*.csv'))

trip_data_full = {}
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
                speed_path = row['SpeedPath'].split(',')
                timestamp_path = row['TimestampPath'].split(',')

                coords = []
                speeds = []
                timestamps = []

                for i, point_str in enumerate(raw_path):
                    parts = point_str.strip().split()
                    if len(parts) == 2:
                        lon, lat = float(parts[0]), float(parts[1])
                        coords.append([lat, lon])

                        try:
                            speed = float(speed_path[i]) if i < len(speed_path) and speed_path[i] not in ['', 'null'] else 0
                        except:
                            speed = 0
                        speeds.append(speed)

                        ts = timestamp_path[i] if i < len(timestamp_path) else ''
                        timestamps.append(ts)

                trip_data_full[row['TripID']] = {
                    'coords': coords,
                    'speeds': speeds,
                    'timestamps': timestamps,
                    'vehicle_type': row['VehicleType'],
                    'max_speed': row['SpeedMax'],
                    'avg_speed': row['SpeedAvg']
                }

                trips_needed.remove(row['TripID'])
                loaded += 1

                if loaded % 20 == 0:
                    print(f"  Loaded {loaded} trips...")

print(f"Loaded {len(trip_data_full)} trips with full data")

# Create HTML map
print("\nGenerating SHOWCASE map...")

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
    <title>Crash-Vehicle Match Analysis - Auckland 2025</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; }}
        #map {{ height: 100vh; width: 100vw; }}

        .legend {{
            background: white;
            padding: 14px 16px;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            font-size: 12px;
            line-height: 1.6;
        }}
        .legend-title {{
            font-weight: 600;
            margin-bottom: 8px;
            font-size: 14px;
            border-bottom: 1px solid #e0e0e0;
            padding-bottom: 6px;
            color: #333;
        }}
        .severity-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 6px;
            border: 1px solid rgba(0,0,0,0.2);
        }}

        #info-panel {{
            position: absolute;
            bottom: 20px;
            left: 20px;
            z-index: 1000;
            background: white;
            padding: 16px;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            min-width: 350px;
            max-width: 450px;
            max-height: 70vh;
            overflow-y: auto;
            display: none;
        }}
        #info-panel h3 {{
            margin: 0 0 12px 0;
            color: #333;
            font-size: 15px;
            font-weight: 600;
            border-bottom: 1px solid #e0e0e0;
            padding-bottom: 8px;
        }}
        #info-panel .stat {{
            margin: 6px 0;
            font-size: 12px;
            line-height: 1.5;
        }}
        #info-panel .stat strong {{
            color: #666;
            font-weight: 500;
        }}
        #info-panel .vehicles-list {{
            margin-top: 10px;
            border-top: 1px solid #e0e0e0;
            padding-top: 10px;
        }}

    </style>
</head>
<body>
    <div id="map"></div>
    <div id="info-panel"></div>

    <script>
        var map = L.map('map').setView([{center_lat}, {center_lon}], 11);

        // Define multiple basemap options
        var openStreetMap = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }});

        var voyager = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '© OpenStreetMap contributors © CARTO',
            maxZoom: 20
        }});

        var voyagerLabels = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager_labels_under/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '© OpenStreetMap contributors © CARTO',
            maxZoom: 20
        }});

        var positron = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '© OpenStreetMap contributors © CARTO',
            maxZoom: 20
        }});

        var darkMatter = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '© OpenStreetMap contributors © CARTO',
            maxZoom: 20
        }});

        // Add default layer
        openStreetMap.addTo(map);

        // Create layer control
        var baseMaps = {{
            "OpenStreetMap": openStreetMap,
            "Voyager": voyager,
            "Voyager + Labels": voyagerLabels,
            "Light": positron,
            "Dark": darkMatter
        }};

        L.control.layers(baseMaps).addTo(map);

        var selectedCrashId = null;
        var crashMarkers = {{}};
        var pathLayers = {{}};
        var highlightedLayers = [];

        // Speed color gradient
        function getSpeedColor(speed) {{
            var kmh = speed * 1.60934;
            return kmh > 100 ? '#2ecc71' :
                   kmh > 80  ? '#95d13a' :
                   kmh > 60  ? '#f1c40f' :
                   kmh > 40  ? '#f39c12' :
                   kmh > 20  ? '#e67e22' :
                   kmh > 5   ? '#e74c3c' :
                                '#c0392b';
        }}

        // Crash data
        var crashes = [
"""

for crash_id, crash in crashes_dict.items():
    num_vehicles = len(crash['vehicles'])
    color = severity_colors.get(crash['severity'], '#999')
    trip_ids = crash_to_trips[crash_id]

    vehicles_info = []
    for v in crash['vehicles']:
        # Parse speed and acceleration (may be empty/null)
        try:
            speed_at = float(v['speed_at_point']) if v['speed_at_point'] and v['speed_at_point'] != '' else None
        except:
            speed_at = None

        try:
            accel_at = float(v['x_accel_at_point']) if v['x_accel_at_point'] and v['x_accel_at_point'] != '' else None
        except:
            accel_at = None

        vehicles_info.append({
            'trip_id': v['trip_id'],
            'vehicle_type': v['vehicle_type'],
            'distance': float(v['distance_to_crash']),
            'time_diff': float(v['time_diff_minutes']),
            'score': float(v['combined_score']),
            'speed_at_point': speed_at,
            'x_accel_at_point': accel_at,
            'trip_speed_max': float(v['trip_speed_max']) if v['trip_speed_max'] else None,
            'trip_speed_avg': float(v['trip_speed_avg']) if v['trip_speed_avg'] else None,
            'closest_timestamp': v['closest_timestamp'],
            'closest_point_idx': int(v['closest_point_idx']) if v['closest_point_idx'] else None
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
                trip_ids: {json.dumps(trip_ids)},
                vehicles: {json.dumps(vehicles_info)}
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

            marker.on('click', function(e) {{
                L.DomEvent.stopPropagation(e);
                highlightCrash(crash.id);
            }});

            crashMarkers[crash.id] = {{
                marker: marker,
                data: crash,
                originalStyle: {{
                    fillColor: crash.color,
                    opacity: 1,
                    fillOpacity: 0.8,
                    weight: 2,
                    radius: 6 + Math.min(crash.num_vehicles * 2, 10)
                }}
            }};
        }});

        // Trip data with speeds
        var tripData = {{
"""

for trip_id, data in trip_data_full.items():
    coords_js = str(data['coords']).replace("'", '"')
    speeds_js = str(data['speeds'])
    timestamps_js = str([ts.split('.')[0] if '.' in ts else ts for ts in data['timestamps']]).replace("'", '"')

    html += f"""            '{trip_id}': {{
                coords: {coords_js},
                speeds: {speeds_js},
                timestamps: {timestamps_js},
                vehicle_type: '{data['vehicle_type']}',
                max_speed: {data['max_speed']},
                avg_speed: {data['avg_speed']}
            }},
"""

html += f"""        }};

        // Draw initial paths
        Object.entries(tripData).forEach(([tripId, data]) => {{
            if (data.coords.length > 1) {{
                var path = L.polyline(data.coords, {{
                    color: '#0066cc',
                    weight: 2,
                    opacity: 0.2,
                    interactive: false
                }}).addTo(map);

                pathLayers[tripId] = {{
                    layer: path,
                    data: data,
                    originalStyle: {{
                        color: '#0066cc',
                        weight: 2,
                        opacity: 0.2
                    }}
                }};
            }}
        }});

        // Bring all crash markers to front so they're clickable
        Object.values(crashMarkers).forEach(data => {{
            if (data.marker._path) {{
                data.marker.bringToFront();
            }}
        }});

        // Highlight crash
        function highlightCrash(crashId) {{
            console.log('Highlighting crash:', crashId);

            // Clear any existing highlights first
            clearHighlightedLayers();

            selectedCrashId = crashId;

            var selectedCrash = crashes.find(c => c.id === crashId);
            if (!selectedCrash) {{
                console.error('Crash not found:', crashId);
                return;
            }}

            console.log('Selected crash:', selectedCrash);
            console.log('Trip IDs:', selectedCrash.trip_ids);

            // Update info panel
            var infoPanel = document.getElementById('info-panel');
            var vehicleStats = selectedCrash.vehicles.map((v, idx) => {{
                var speedText = v.speed_at_point !== null ? (v.speed_at_point * 1.60934).toFixed(1) + ' km/h' : 'N/A';
                var accelText = v.x_accel_at_point !== null ? v.x_accel_at_point.toFixed(2) + ' m/s²' : 'N/A';
                var maxSpeedText = v.trip_speed_max !== null ? (v.trip_speed_max * 1.60934).toFixed(1) + ' km/h' : 'N/A';
                var avgSpeedText = v.trip_speed_avg !== null ? (v.trip_speed_avg * 1.60934).toFixed(1) + ' km/h' : 'N/A';

                return `<div class="stat" style="margin: 8px 0; padding: 8px; background: #f9f9f9; border-left: 3px solid #0066cc;">
                    <strong style="font-size: 13px;">${{idx + 1}}. ${{v.vehicle_type}}</strong><br>
                    <div style="margin-top: 4px; font-size: 11px;">
                        <strong>At Closest Point:</strong><br>
                        • Distance: ${{v.distance.toFixed(1)}}m from crash<br>
                        • Time: ${{v.time_diff.toFixed(2)}}min before crash<br>
                        • Speed: ${{speedText}}<br>
                        • Acceleration: ${{accelText}}<br>
                        • Timestamp: ${{v.closest_timestamp}}<br>
                        <strong style="margin-top: 4px; display: block;">Trip Summary:</strong>
                        • Max speed: ${{maxSpeedText}}<br>
                        • Avg speed: ${{avgSpeedText}}<br>
                        • Match score: ${{v.score.toFixed(1)}}
                    </div>
                </div>`;
            }}).join('');

            infoPanel.innerHTML =
                '<h3>Crash Details</h3>' +
                '<div class="stat"><strong>Severity:</strong> ' + selectedCrash.severity + '</div>' +
                '<div class="stat"><strong>Location:</strong> ' + selectedCrash.location + '</div>' +
                '<div class="stat"><strong>Road:</strong> ' + selectedCrash.road + '</div>' +
                '<div class="stat"><strong>Time:</strong> ' + selectedCrash.datetime + '</div>' +
                '<div class="stat"><strong>Crash ID:</strong> ' + selectedCrash.id + '</div>' +
                '<div class="vehicles-list"><strong>Detected Vehicles (' + selectedCrash.num_vehicles + '):</strong>' +
                vehicleStats + '</div>';
            infoPanel.style.display = 'block';

            console.log('Info panel updated');

            // Dim ALL crashes
            console.log('Dimming crashes, total:', crashes.length);
            var dimmedCount = 0;
            var highlightedCount = 0;
            try {{
                Object.keys(crashMarkers).forEach(crashKey => {{
                    var crashData = crashMarkers[crashKey];
                    if (!crashData || !crashData.marker) {{
                        console.warn('Missing crash marker for:', crashKey);
                        return;
                    }}
                    var marker = crashData.marker;

                    if (crashKey === crashId) {{
                        // Highlight selected crash
                        marker.setStyle({{
                            fillColor: crashData.originalStyle.fillColor,
                            opacity: 1,
                            fillOpacity: 1,
                            weight: 4,
                            color: '#fff',
                            radius: crashData.originalStyle.radius * 1.3
                        }});
                        highlightedCount++;
                        console.log('Highlighted crash:', crashKey);
                    }} else {{
                        // Dim other crashes
                        marker.setStyle({{
                            fillColor: '#ccc',
                            opacity: 0.3,
                            fillOpacity: 0.3,
                            weight: 1,
                            color: '#999'
                        }});
                        dimmedCount++;
                    }}
                }});
                console.log('Crashes dimmed successfully. Dimmed:', dimmedCount, 'Highlighted:', highlightedCount);
            }} catch(e) {{
                console.error('Error dimming crashes:', e);
            }}

            // Dim all paths
            console.log('Dimming paths, total:', Object.keys(pathLayers).length);
            try {{
                Object.keys(pathLayers).forEach(tripId => {{
                    pathLayers[tripId].layer.setStyle({{
                        color: '#ddd',
                        weight: 1,
                        opacity: 0.1
                    }});
                }});
                console.log('Paths dimmed successfully');
            }} catch(e) {{
                console.error('Error dimming paths:', e);
            }}

            // Highlight selected trip paths with speed gradient
            console.log('Highlighting selected trips:', selectedCrash.trip_ids);
            try {{
                selectedCrash.trip_ids.forEach((tripId, tripIdx) => {{
                if (!pathLayers[tripId] || !pathLayers[tripId].data) return;

                var pathData = pathLayers[tripId].data;
                var coords = pathData.coords;
                var speeds = pathData.speeds;
                var timestamps = pathData.timestamps;
                var vehicleType = pathData.vehicle_type;

                if (!coords || coords.length < 2) return;

                // Find vehicle info for this trip
                var vehicleInfo = selectedCrash.vehicles.find(v => v.trip_id === tripId);
                var distance = vehicleInfo ? vehicleInfo.distance.toFixed(1) : 'N/A';
                var timeDiff = vehicleInfo ? vehicleInfo.time_diff.toFixed(2) : 'N/A';
                var speedAtCrash = vehicleInfo && vehicleInfo.speed_at_point !== null ?
                    (vehicleInfo.speed_at_point * 1.60934).toFixed(1) + ' km/h' : 'N/A';
                var accelAtCrash = vehicleInfo && vehicleInfo.x_accel_at_point !== null ?
                    vehicleInfo.x_accel_at_point.toFixed(2) + ' m/s²' : 'N/A';
                var maxSpeed = vehicleInfo && vehicleInfo.trip_speed_max !== null ?
                    (vehicleInfo.trip_speed_max * 1.60934).toFixed(1) + ' km/h' : 'N/A';

                // Draw speed-colored segments
                for (var i = 0; i < coords.length - 1; i++) {{
                    var segmentColor = getSpeedColor(speeds[i]);
                    var segment = L.polyline([coords[i], coords[i+1]], {{
                        color: segmentColor,
                        weight: 4,
                        opacity: 0.8,
                        interactive: false
                    }}).addTo(map);
                    highlightedLayers.push(segment);
                }}

                // Add start marker (green)
                var startMarker = L.circleMarker(coords[0], {{
                    radius: 6,
                    fillColor: '#27ae60',
                    color: '#fff',
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 1
                }}).addTo(map);
                startMarker.bindTooltip(
                    '<strong>Trip Start</strong><br>' +
                    '<strong>Type:</strong> ' + vehicleType + '<br>' +
                    '<strong>Distance to crash:</strong> ' + distance + 'm<br>' +
                    '<strong>Time before crash:</strong> ' + timeDiff + ' min<br>' +
                    '<strong>Speed at crash:</strong> ' + speedAtCrash + '<br>' +
                    '<strong>Acceleration:</strong> ' + accelAtCrash + '<br>' +
                    '<strong>Max speed:</strong> ' + maxSpeed,
                    {{ permanent: false, direction: 'top', className: 'custom-tooltip' }}
                );
                highlightedLayers.push(startMarker);

                // Add end marker (red)
                var endMarker = L.circleMarker(coords[coords.length - 1], {{
                    radius: 6,
                    fillColor: '#e74c3c',
                    color: '#fff',
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 1
                }}).addTo(map);
                endMarker.bindTooltip(
                    '<strong>Trip End</strong><br>' +
                    'Type: ' + vehicleType,
                    {{ permanent: false, direction: 'top' }}
                );
                highlightedLayers.push(endMarker);

                // Add GPS points every 2nd point
                coords.forEach((coord, idx) => {{
                    if (idx % 2 === 0 && idx > 0 && idx < coords.length - 1) {{
                        var pointMarker = L.circleMarker(coord, {{
                            radius: 3,
                            fillColor: getSpeedColor(speeds[idx]),
                            color: '#333',
                            weight: 1,
                            opacity: 1,
                            fillOpacity: 1
                        }}).addTo(map);

                        pointMarker.bindTooltip(
                            'Speed: ' + (speeds[idx] * 1.60934).toFixed(1) + ' km/h<br>Time: ' + timestamps[idx],
                            {{ permanent: false, direction: 'top' }}
                        );

                        highlightedLayers.push(pointMarker);
                    }}
                }});
                console.log('Trip highlighted:', tripId);
            }});
            console.log('All trips highlighted, total layers:', highlightedLayers.length);
            }} catch(e) {{
                console.error('Error highlighting trips:', e);
            }}

            // Bring ALL crash markers to front so they remain clickable above highlighted paths
            console.log('Bringing crash markers to front');
            try {{
                crashes.forEach(crash => {{
                    var crashData = crashMarkers[crash.id];
                    if (crashData && crashData.marker && crashData.marker._path) {{
                        crashData.marker.bringToFront();
                    }}
                }});
                console.log('All crash markers brought to front');
            }} catch(e) {{
                console.error('Error bringing markers to front:', e);
            }}

            // Zoom to crash
            console.log('Zooming to crash');
            map.flyTo([selectedCrash.lat, selectedCrash.lon], 14, {{
                duration: 0.8
            }});
            console.log('highlightCrash complete');
        }}

        function clearHighlightedLayers() {{
            highlightedLayers.forEach(layer => {{
                try {{
                    map.removeLayer(layer);
                }} catch(e) {{
                    // Layer might not be on map
                }}
            }});
            highlightedLayers = [];
        }}

        function clearSelection() {{
            console.log('clearSelection called, selectedCrashId:', selectedCrashId);

            if (selectedCrashId === null) {{
                console.log('No selection to clear');
                return;
            }}

            // Clear highlights
            console.log('Clearing highlighted layers');
            clearHighlightedLayers();

            selectedCrashId = null;
            document.getElementById('info-panel').style.display = 'none';

            // Restore ALL crashes
            console.log('Restoring all crash markers');
            try {{
                crashes.forEach(crash => {{
                    var crashData = crashMarkers[crash.id];
                    if (crashData && crashData.marker && crashData.originalStyle) {{
                        crashData.marker.setStyle(crashData.originalStyle);
                    }}
                }});
                console.log('All crashes restored');
            }} catch(e) {{
                console.error('Error restoring crashes:', e);
            }}

            // Restore ALL paths
            console.log('Restoring all paths');
            try {{
                Object.keys(pathLayers).forEach(tripId => {{
                    var pathData = pathLayers[tripId];
                    if (pathData && pathData.layer && pathData.originalStyle) {{
                        pathData.layer.setStyle(pathData.originalStyle);
                    }}
                }});
                console.log('All paths restored');
            }} catch(e) {{
                console.error('Error restoring paths:', e);
            }}

            // Bring crash markers to front again
            console.log('Bringing crash markers to front');
            try {{
                Object.values(crashMarkers).forEach(data => {{
                    if (data.marker._path) {{
                        data.marker.bringToFront();
                    }}
                }});
                console.log('Crash markers brought to front');
            }} catch(e) {{
                console.error('Error bringing markers to front:', e);
            }}

            // Zoom out
            console.log('Zooming out');
            map.flyTo([{center_lat}, {center_lon}], 11, {{
                duration: 0.8
            }});
            console.log('clearSelection complete');
        }}

        // Click map to clear selection
        map.on('click', function(e) {{
            console.log('Map clicked, selectedCrashId:', selectedCrashId);
            if (selectedCrashId !== null) {{
                console.log('Clearing selection from map click');
                clearSelection();
            }}
        }});

        // Legend
        var legend = L.control({{position: 'topright'}});
        legend.onAdd = function (map) {{
            var div = L.DomUtil.create('div', 'legend');
            div.innerHTML = '<div class="legend-title">Crash-Vehicle Analysis</div>';
            div.innerHTML += '<b>Dataset:</b> {len(matches)} observations<br>';
            div.innerHTML += '<b>Crashes:</b> {len(crashes_dict)} locations<br>';
            div.innerHTML += '<b>Time Window:</b> ±5 minutes<br><br>';

            div.innerHTML += '<b>Crash Severity</b><br>';
            div.innerHTML += '<span class="severity-dot" style="background: #8B0000;"></span> Fatal<br>';
            div.innerHTML += '<span class="severity-dot" style="background: #FF4500;"></span> Serious<br>';
            div.innerHTML += '<span class="severity-dot" style="background: #FFA500;"></span> Minor<br>';
            div.innerHTML += '<span class="severity-dot" style="background: #FFD700;"></span> Non-Injury<br><br>';

            div.innerHTML += '<b>Speed Gradient</b><br>';
            div.innerHTML += '<span style="color: #2ecc71; font-size: 14px;">●</span> Fast (>100 km/h)<br>';
            div.innerHTML += '<span style="color: #f1c40f; font-size: 14px;">●</span> Medium (40-60 km/h)<br>';
            div.innerHTML += '<span style="color: #e74c3c; font-size: 14px;">●</span> Slow (<20 km/h)<br><br>';

            div.innerHTML += '<div style="font-size: 11px; color: #666; border-top: 1px solid #e0e0e0; padding-top: 8px;">';
            div.innerHTML += 'Click crash to view details<br>';
            div.innerHTML += 'Click map to clear selection</div>';

            return div;
        }};
        legend.addTo(map);

    </script>
</body>
</html>"""

output_file = 'showcase_crash_map.html'
with open(output_file, 'w') as f:
    f.write(html)

print(f"\nMap created: {output_file}")
print(f"\nFeatures:")
print(f"  - Click crash to view speed-colored vehicle paths")
print(f"  - GPS points with start/end markers and hover tooltips")
print(f"  - Detailed vehicle data (speed, acceleration, timestamps)")
print(f"  - Dimming of non-selected crashes and trips")
print(f"  - Enhanced statistics panel for selected crash")
print(f"  - Click map to clear selection")
print(f"  - Layer selector with 5 basemap options (including POI layers)")
print(f"  - Professional styling and color gradients")
