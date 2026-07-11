import csv
from typing import List, Dict
from .models import Allocation

def export_allocations_csv(path: str, allocations: List[Allocation]):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['restaurant_id','ngo_id','amount','cost_per_unit'])
        for a in allocations:
            w.writerow([a.restaurant_id, a.ngo_id, a.amount, f"{a.cost_per_unit:.4f}"])

def export_summary_csv(path: str, metrics: Dict[str, float]):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['metric','value'])
        for k, v in metrics.items():
            w.writerow([k, v])
