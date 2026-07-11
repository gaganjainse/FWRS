import math

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def expiry_aware_unit_cost(r, n, alpha=0.4, speed_kmph=30.0, penalty_per_hour=10.0):
    """Non-negative linear cost used in the last stage:
       base distance – alpha*priority, clamped to >= 0
       + overdue hours penalty if travel time exceeds remaining expiry
    """
    dist = haversine_km(r.lat, r.lon, n.lat, n.lon)
    base = max(0.0, dist - alpha * n.priority)
    if r.expiry_hours is None:
        return base
    travel_time = dist / max(1e-6, speed_kmph)
    deficit = max(0.0, travel_time - r.expiry_hours)
    return base + penalty_per_hour * deficit
