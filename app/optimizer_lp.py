from typing import List, Dict, Tuple
from collections import defaultdict
import pulp as pl
from .models import Restaurant, NGO, Allocation
from .distance import expiry_aware_unit_cost

def _index_maps(R: List[Restaurant], N: List[NGO]):
    Ri = {r.id: idx for idx, r in enumerate(R)}
    Nj = {n.id: idx for idx, n in enumerate(N)}
    return Ri, Nj

def fairness_stage(R: List[Restaurant], N: List[NGO]) -> Tuple[Dict[Tuple[int,int], float], float]:
    Ri, Nj = _index_maps(R, N)
    I, J = range(len(R)), range(len(N))

    prob = pl.LpProblem("FairnessMaxMin", pl.LpMaximize)
    x = pl.LpVariable.dicts('x', (list(I), list(J)), lowBound=0, cat='Continuous')
    t = pl.LpVariable('t', lowBound=0, upBound=1, cat='Continuous')

    prob += t

    for j in J:
        prob += pl.lpSum(x[i][j] for i in I) >= t * N[j].demand

    for i in I:
        prob += pl.lpSum(x[i][j] for j in J) <= R[i].supply

    prob.solve(pl.PULP_CBC_CMD(msg=False))
    sol_x = {(i,j): pl.value(x[i][j]) or 0.0 for i in I for j in J}
    sol_t = pl.value(t) or 0.0
    return sol_x, sol_t

def priority_stage(R: List[Restaurant], N: List[NGO], lower_bounds_by_ngo: Dict[int, float], tier_ngos: List[int]) -> Dict[Tuple[int,int], float]:
    I, J = range(len(R)), range(len(N))
    prob = pl.LpProblem("PriorityTier", pl.LpMaximize)
    x = pl.LpVariable.dicts('x', (list(I), list(J)), lowBound=0, cat='Continuous')

    prob += pl.lpSum(x[i][j] for i in I for j in tier_ngos)

    for j in J:
        lb = lower_bounds_by_ngo.get(j, 0.0)
        prob += pl.lpSum(x[i][j] for i in I) >= lb

    for i in I:
        prob += pl.lpSum(x[i][j] for j in J) <= R[i].supply

    for j in J:
        prob += pl.lpSum(x[i][j] for i in I) <= N[j].demand

    prob.solve(pl.PULP_CBC_CMD(msg=False))
    sol_x = {(i,j): pl.value(x[i][j]) or 0.0 for i in I for j in J}
    return sol_x

def cost_stage(R: List[Restaurant], N: List[NGO], lower_bounds_by_ngo: Dict[int, float], alpha=0.4, speed_kmph=30.0, penalty_per_hour=10.0) -> Dict[Tuple[int,int], float]:
    I, J = range(len(R)), range(len(N))
    prob = pl.LpProblem("CostMin", pl.LpMinimize)
    x = pl.LpVariable.dicts('x', (list(I), list(J)), lowBound=0, cat='Continuous')

    C = [[expiry_aware_unit_cost(R[i], N[j], alpha=alpha, speed_kmph=speed_kmph, penalty_per_hour=penalty_per_hour) for j in J] for i in I]

    prob += pl.lpSum(C[i][j] * x[i][j] for i in I for j in J)

    for j in J:
        lb = lower_bounds_by_ngo.get(j, 0.0)
        prob += pl.lpSum(x[i][j] for i in I) >= lb
        prob += pl.lpSum(x[i][j] for i in I) <= N[j].demand

    for i in I:
        prob += pl.lpSum(x[i][j] for j in J) <= R[i].supply

    prob.solve(pl.PULP_CBC_CMD(msg=False))
    sol_x = {(i,j): pl.value(x[i][j]) or 0.0 for i in I for j in J}
    return sol_x

def pipeline_lp(R: List[Restaurant], N: List[NGO], alpha=0.4, speed_kmph=30.0, penalty_per_hour=10.0):
    fair_x, t = fairness_stage(R, N)
    I, J = range(len(R)), range(len(N))

    lb_ngo = {j: sum(fair_x[i,j] for i in I) for j in J}

    tiers = sorted(set(n.priority for n in N), reverse=True)

    for pr in tiers:
        tier_js = [j for j in J if N[j].priority == pr]
        if not tier_js:
            continue
        sol_x = priority_stage(R, N, lb_ngo, tier_js)
        for j in J:
            lb_ngo[j] = max(lb_ngo[j], sum(sol_x[i,j] for i in I))

    sol_x = cost_stage(R, N, lb_ngo, alpha=alpha, speed_kmph=speed_kmph, penalty_per_hour=penalty_per_hour)

    allocs = []
    for i in I:
        for j in J:
            amt = sol_x[i,j]
            if amt and amt > 1e-9:
                c = expiry_aware_unit_cost(R[i], N[j], alpha=alpha, speed_kmph=speed_kmph, penalty_per_hour=penalty_per_hour)
                allocs.append(Allocation(R[i].id, N[j].id, int(round(amt)), c))
    return allocs
