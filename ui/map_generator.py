import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import folium
from folium.plugins import AntPath, HeatMap
import branca
from app.data_loader import load_restaurants, load_ngos
from app.optimizer_lp import pipeline_lp
from app.distance import haversine_km, expiry_aware_unit_cost
import math

def _add_legend(m):
    legend_html = '''
     <div style="position: fixed; 
                 bottom: 50px; left: 50px; width: 230px; height: 160px; 
                 background-color: rgba(30,30,30,0.8); color: white; z-index:9999; padding:10px; border-radius:8px;">
     <h4 style="margin:0 0 6px 0; color:white">Legend</h4>
     <div><span style="background:#ff6b6b;display:inline-block;width:12px;height:12px;margin-right:6px;"></span>Priority 5</div>
     <div><span style="background:#ff9f43;display:inline-block;width:12px;height:12px;margin-right:6px;"></span>Priority 4</div>
     <div><span style="background:#ffd54f;display:inline-block;width:12px;height:12px;margin-right:6px;"></span>Priority 3</div>
     <div><span style="background:#2ecc71;display:inline-block;width:12px;height:12px;margin-right:6px;"></span>Priority 2</div>
     <div><span style="background:#4aa3ff;display:inline-block;width:12px;height:12px;margin-right:6px;"></span>Priority 1</div>
     <div style="margin-top:8px;"><span style="border-left:4px solid white;padding-left:6px;margin-right:6px;"></span>Edge thickness = amount</div>
     </div>
     '''
    m.get_root().html.add_child(branca.element.Element(legend_html))

def generate_map_with_heatmap(rest_csv="bangalore_dataset/restaurants.csv", ngo_csv="bangalore_dataset/ngos.csv", alpha=0.4, out_path="map.html"):
    R = load_restaurants(rest_csv)
    N = load_ngos(ngo_csv)
    allocations = pipeline_lp(R, N, alpha=alpha)

    # center map
    all_coords = [(r.lat, r.lon) for r in R] + [(n.lat, n.lon) for n in N]
    avg_lat = sum(lat for lat,lon in all_coords)/len(all_coords)
    avg_lon = sum(lon for lat,lon in all_coords)/len(all_coords)

    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=13, tiles="CartoDB dark_matter")

    # Restaurants
    for r in R:
        folium.CircleMarker(location=[r.lat, r.lon], radius=6, color="#7f8c8d", fill=True, fill_color="#7f8c8d",
                            popup=f"{r.name}<br>Supply: {r.supply}<br>Expiry: {r.expiry_hours}h").add_to(m)
    # NGOs
    colors = {5:"#ff6b6b",4:"#ff9f43",3:"#ffd54f",2:"#2ecc71",1:"#4aa3ff"}
    for n in N:
        folium.CircleMarker(location=[n.lat, n.lon], radius=8, color=colors.get(n.priority,"#ffffff"),
                            fill=True, fill_color=colors.get(n.priority,"#ffffff"),
                            popup=f"{n.name}<br>Demand: {n.demand}<br>Priority: {n.priority}").add_to(m)

    # Allocation flows + collect heatmap points (use cost as intensity)
    heat_points = []
    for a in allocations:
        r = next(r for r in R if r.id==a.restaurant_id)
        n = next(n for n in N if n.id==a.ngo_id)
        dist = haversine_km(r.lat, r.lon, n.lat, n.lon)
        # use cost per unit as intensity
        intensity = a.cost_per_unit
        # AntPath for animated line
        AntPath(locations=[[r.lat, r.lon],[n.lat, n.lon]], tooltip=f"{r.name} → {n.name}<br>Amount: {a.amount}<br>Dist: {dist:.2f} km<br>Cost/u: {a.cost_per_unit:.2f}",
                color="#00ffff", weight=max(2, a.amount/10)).add_to(m)
        # add midpoint heat point with intensity scaled
        mid_lat = (r.lat + n.lat)/2
        mid_lon = (r.lon + n.lon)/2
        heat_points.append([mid_lat, mid_lon, max(0.1, intensity)])

    # Add HeatMap layer for route cost intensity
    # Add heatmap as a toggleable layer
    if heat_points:
        heat_fg = folium.FeatureGroup(name='Route Cost Heatmap', show=True)
        HeatMap(heat_points, radius=25, max_zoom=13).add_to(heat_fg)
        heat_fg.add_to(m)

    # Add layer control so user can toggle heatmap on/off
    folium.LayerControl(collapsed=False).add_to(m)

    # Legend overlay
    _add_legend(m)

    m.save(out_path)
    print(f"Map saved to {out_path}")

if __name__=="__main__":
    generate_map_with_heatmap()