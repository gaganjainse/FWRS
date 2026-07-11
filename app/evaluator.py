from .models import Allocation

def evaluate(R, N, allocations):
    supply = sum(r.supply for r in R)
    demand = sum(n.demand for n in N)
    delivered = sum(a.amount for a in allocations)
    total_cost = sum(a.amount * a.cost_per_unit for a in allocations) if delivered else 0
    avg_cost = total_cost / delivered if delivered else 0
    unmet = demand - delivered
    unused = supply - delivered

    ngo_recv = {n.id: 0 for n in N}
    for a in allocations:
        ngo_recv[a.ngo_id] += a.amount
    fill_ratios = {}
    for n in N:
        if n.demand > 0:
            fill_ratios[n.id] = ngo_recv[n.id] / n.demand
        else:
            fill_ratios[n.id] = 1.0

    return {
        'supply': supply,
        'demand': demand,
        'delivered': delivered,
        'delivered_pct': (delivered / demand * 100) if demand else 0,
        'unused_supply': unused,
        'unmet_demand': unmet,
        'avg_cost_per_unit': avg_cost,
        'total_cost': total_cost,
        'min_fill_ratio': min(fill_ratios.values()) if fill_ratios else 0.0
    }

def evaluate_and_print(R, N, allocations):
    m = evaluate(R, N, allocations)
    print("=== Allocation Summary ===")
    for k, v in m.items():
        print(f"{k}: {v}")
    print("\nDetails:")
    for a in allocations:
        print(f"{a.restaurant_id} -> {a.ngo_id}: {a.amount} units @ cost {a.cost_per_unit:.2f}")
