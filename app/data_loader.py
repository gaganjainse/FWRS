import csv
from .models import Restaurant, NGO

def load_restaurants(path: str):
    res = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            expiry = row.get('expiry_hours')
            expiry_val = float(expiry) if (expiry not in (None, '', 'NA')) else None
            res.append(Restaurant(
                id=row['id'],
                name=row['name'],
                lat=float(row['lat']),
                lon=float(row['lon']),
                supply=int(row['supply']),
                expiry_hours=expiry_val
            ))
    return res

def load_ngos(path: str):
    res = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            res.append(NGO(
                id=row['id'],
                name=row['name'],
                lat=float(row['lat']),
                lon=float(row['lon']),
                demand=int(row['demand']),
                priority=int(row['priority'])
            ))
    return res
