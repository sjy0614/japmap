import streamlit as st
import pandas as pd
from geopy.distance import geodesic
import itertools

# 📁 데이터 불러오기
df = pd.read_excel("일본 원자력 발전소 위치.xlsx")
df = df.dropna(subset=["위도", "경도"])

df_point = pd.read_excel("전체_방사능_조사_측점_좌표_위경도_포함.xlsx")
df_point.columns = df_point.columns.str.strip()
df_point = df_point.dropna(subset=["위도", "경도"])

# 🔑 Google Maps API Key
api_key = "AIzaSyBg0wpE88ZHxNuwZGhN-QEQvUQgf-rW9zk"

# 🌏 지도 중심
center_lat, center_lng = 36.0, 137.0
zoom = 6
lat_offset = 0.0001
lng_offset = 0.0001

# 🟢 상태별 색상
status_color_map = {
    "운전 중": "red",
    "영구 정지": "green",
    "건설 중": "orange",
    "운전 중지": "blue",
}

# 📍 마커 코드 생성
marker_js = ""

# 🔴 원자력 발전소 마커
for i, row in df.iterrows():
    base_lat = row["위도"]
    base_lng = row["경도"]
    lat = base_lat + (i % 5) * lat_offset
    lng = base_lng + (i % 5) * lng_offset
    name = str(row["이름"]).strip()
    plant_type = str(row.get("유형", "정보 없음")).strip()
    status = str(row["상태"]).strip()
    location = str(row.get("위치", "정보 없음")).strip()
    color = status_color_map.get(status, "purple")
    icon_url = f"http://maps.google.com/mapfiles/ms/icons/{color}-dot.png"
    info_html = f"""<div><b>이름:</b> {name}<br><b>유형:</b> {plant_type}<br><b>상태:</b> {status}<br><b>위치:</b> {location}</div>"""
    marker_id = f"marker_{i}"
    infowindow_id = f"infowindow_{i}"
    marker_js += f"""
      const {infowindow_id} = new google.maps.InfoWindow({{ content: `{info_html}` }});
      const {marker_id} = new google.maps.Marker({{
        position: {{ lat: {lat}, lng: {lng} }},
        map: map,
        title: "{name}",
        icon: "{icon_url}"
      }});
      {marker_id}.addListener("click", function() {{
        {infowindow_id}.open(map, {marker_id});
      }});
      window.markers_{color}.push({marker_id});
    """

# ⚫ 방사능 측점 마커
for i, row in df_point.iterrows():
    lat = row["위도"]
    lng = row["경도"]
    info_html_parts = [f"<b>{col}:</b> {row[col]}" for col in df_point.columns if pd.notna(row[col])]
    info_html = "<div>" + "<br>".join(info_html_parts) + "</div>"
    marker_js += f"""
      const point_infowindow_{i} = new google.maps.InfoWindow({{ content: `{info_html}` }});
      const point_marker_{i} = new google.maps.Marker({{
        position: {{ lat: {lat}, lng: {lng} }},
        map: map,
        title: "방사능 측점",
        icon: {{
          path: google.maps.SymbolPath.CIRCLE,
          fillColor: "black",
          fillOpacity: 1,
          scale: 5,
          strokeWeight: 0
        }}
      }});
      point_marker_{i}.addListener("click", function() {{
        point_infowindow_{i}.open(map, point_marker_{i});
      }});
    """

# 🔁 선 연결: 해역별 측점 간 거리 계산
distance_data = []
for region, group in df_point.groupby("해역"):
    locations = list(zip(group['측점'], group['위도'], group['경도']))
    for (p1, lat1, lon1), (p2, lat2, lon2) in itertools.combinations(locations, 2):
        km = round(geodesic((lat1, lon1), (lat2, lon2)).km, 2)
        distance_data.append((region, p1, p2, lat1, lon1, lat2, lon2, km))

polyline_js = ""
for i, (region, p1, p2, lat1, lon1, lat2, lon2, km) in enumerate(distance_data):
    polyline_js += f"""
      const polyline_{i} = new google.maps.Polyline({{
        path: [{{ lat: {lat1}, lng: {lon1} }}, {{ lat: {lat2}, lng: {lon2} }}],
        geodesic: true,
        strokeColor: "#666666",
        strokeOpacity: 0.5,
        strokeWeight: 6,
        clickable: true,
        map: map
      }});

      const distanceLabel_{i} = new google.maps.InfoWindow({{
        content: "<b>{region}</b><br>{p1} ↔ {p2}: {km} km",
        position: {{ lat: {(lat1 + lat2)/2}, lng: {(lon1 + lon2)/2} }}
      }});

      polyline_{i}.addListener("click", function() {{
        distanceLabel_{i}.open(map);
      }});
    """



# 🧩 HTML 코드
html_code = f"""
<!DOCTYPE html>
<html>
  <head>
    <title>원자력 발전소 및 방사능 측정점 지도</title>
    <meta charset="utf-8">
    <meta name="viewport" content="initial-scale=1.0">
    <style>
      html, body {{ height: 100%; margin: 0; padding: 0; }}
      #map {{ height: 100vh; width: 100%; }}
      .legend {{
        background: white; padding: 10px; margin: 10px;
        font-size: 14px; font-family: Arial, sans-serif;
        border: 1px solid #ccc;
      }}
      .legend-item {{
        cursor: pointer; margin-bottom: 6px; padding: 6px;
        border: 1px solid #ccc; border-radius: 6px;
        background-color: #f8f8f8;
        transition: background-color 0.2s, opacity 0.2s;
      }}
      .legend-item:hover {{ background-color: #e0e0e0; }}
    </style>
    <script src="https://maps.googleapis.com/maps/api/js?key={api_key}"></script>
  </head>
  <body>
    <div id="map"></div>
    <script>
      window.markers_red = [];
      window.markers_green = [];
      window.markers_orange = [];
      window.markers_blue = [];

      function toggleMarkers(group, visible) {{
        group.forEach(marker => marker.setVisible(visible));
      }}

      function initMap() {{
        const center = {{ lat: {center_lat}, lng: {center_lng} }};
        const map = new google.maps.Map(document.getElementById("map"), {{
          zoom: {zoom},
          center: center,
          gestureHandling: "greedy"
        }});

        {marker_js}
        {polyline_js}

        const legend = document.createElement("div");
        legend.classList.add("legend");
        const states = [
          {{label: "운전 중", color: "red"}},
          {{label: "영구 정지", color: "green"}},
          {{label: "건설 중", color: "orange"}},
          {{label: "운전 중지", color: "blue"}}
        ];
        states.forEach(state => {{
          const div = document.createElement("div");
          div.classList.add("legend-item");
          div.innerHTML = `
            <img src='http://maps.google.com/mapfiles/ms/icons/${{state.color}}-dot.png' style='vertical-align: middle;'>
            <span style='margin-left: 8px;'>${{state.label}}</span>
          `;
          div.onclick = function() {{
            const group = window["markers_" + state.color];
            const anyVisible = group.some(m => m.getVisible());
            toggleMarkers(group, !anyVisible);
            div.style.opacity = anyVisible ? "0.4" : "1.0";
          }};
          legend.appendChild(div);
        }});
        map.controls[google.maps.ControlPosition.RIGHT_BOTTOM].push(legend);
      }}

      window.onload = initMap;
    </script>
  </body>
</html>
"""

# 🖥️ Streamlit 출력
st.set_page_config(layout="wide")
st.markdown("🗾 **일본 원자력 발전소 및 방사능 조사 측점 지도 (거리 포함)**")
st.components.v1.html(html_code, height=1000)
