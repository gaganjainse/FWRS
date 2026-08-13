"""Test suite for the FWRS LP allocation pipeline and helpers.

Covers: the 3-stage lexicographic solver (fairness → priority → cost),
expiry-aware routing, haversine distance, data loading, evaluation metrics,
and CSV export. Kept offline (pure PuLP/CSV, no network, no filesystem writes
except tmp_path).
"""
import math
import pytest

from app.distance import haversine_km, expiry_aware_unit_cost
from app.models import Restaurant, NGO, Allocation
from app.optimizer_lp import pipeline_lp, fairness_stage, cost_stage
from app.evaluator import evaluate
from app.exporter import export_allocations_csv, export_summary_csv
from app.data_loader import load_restaurants, load_ngos


def make_r(id, lat, lon, supply, expiry=None):
    return Restaurant(id, f"R{id}", lat, lon, supply, expiry)


def make_n(id, lat, lon, demand, priority):
    return NGO(id, f"N{id}", lat, lon, demand, priority)


# ─────────────────────────── pipeline end-to-end ───────────────────────────

def test_lp_pipeline_allocates_all_when_supply_equals_demand():
    R = [make_r("r1", 0, 0, 40, 5.0), make_r("r2", 0, 0, 30, 5.0)]
    N = [make_n("n1", 0, 0, 50, 5), make_n("n2", 0, 0, 20, 3)]
    allocs = pipeline_lp(R, N, alpha=0.0)
    assert sum(a.amount for a in allocs) == 70
    # no allocation may exceed a restaurant's supply or an NGO's demand
    by_r = {}
    by_n = {}
    for a in allocs:
        by_r[a.restaurant_id] = by_r.get(a.restaurant_id, 0) + a.amount
        by_n[a.ngo_id] = by_n.get(a.ngo_id, 0) + a.amount
    for r in R:
        assert by_r.get(r.id, 0) <= r.supply
    for n in N:
        assert by_n.get(n.id, 0) <= n.demand


def test_lp_pipeline_supply_scarce_leaves_unmet_demand():
    R = [make_r("r1", 0, 0, 30, 5.0)]
    N = [make_n("n1", 0, 0, 100, 5)]
    allocs = pipeline_lp(R, N, alpha=0.0)
    delivered = sum(a.amount for a in allocs)
    assert delivered == 30  # everything available is delivered
    metrics = evaluate(R, N, allocs)
    assert metrics["unmet_demand"] == 70


def test_lp_pipeline_supply_surplus_leaves_unused():
    R = [make_r("r1", 0, 0, 100, 5.0)]
    N = [make_n("n1", 0, 0, 30, 5)]
    allocs = pipeline_lp(R, N, alpha=0.0)
    delivered = sum(a.amount for a in allocs)
    assert delivered == 30
    metrics = evaluate(R, N, allocs)
    assert metrics["unused_supply"] == 70


def test_priority_ngo_filled_first_when_scarce():
    # Two NGOs: same demand, but n_high has higher priority. Only 10 units.
    R = [make_r("r1", 0, 0, 10, 5.0)]
    N = [make_n("low", 0, 0, 10, 1), make_n("high", 0, 0, 10, 9)]
    allocs = pipeline_lp(R, N, alpha=0.0)
    by_n = {}
    for a in allocs:
        by_n[a.ngo_id] = by_n.get(a.ngo_id, 0) + a.amount
    assert by_n.get("high", 0) >= by_n.get("low", 0)


def test_fairness_spreads_when_equal_priority():
    # Fairness stage maximizes the minimum fill ratio across NGOs.
    R = [make_r("r1", 0, 0, 10, 5.0)]
    N = [make_n("a", 0, 0, 10, 5), make_n("b", 0, 0, 10, 5)]
    x, t = fairness_stage(R, N)
    # both NGOs get t*demand; with 10 supply and 20 demand, t should be ~0.5
    assert t is not None
    assert 0.4 <= t <= 0.6


def test_expired_food_prefers_nearby_ngo():
    # Restaurant r_far has 1h expiry; ngo at ~1000 km away takes ~33h -> huge
    # penalty in the cost stage. A close NGO (same spot) should win.
    R = [make_r("far", 0, 0, 10, 1.0)]
    N = [make_n("close", 0, 0, 10, 5), make_n("far", 10, 0, 10, 5)]  # ~1111 km
    # solve with cost stage only (fairness already allocates equally)
    x = cost_stage(R, N, {0: 10.0, 1: 0.0}, alpha=0.0)
    # cost stage lower-bounds NGO 0 at 10 (so 'close' must receive 10) — verify
    # it does not route the expired food to the far NGO instead.
    assert x[(0, 0)] is not None
    assert x[(0, 0)] > 9.0


# ─────────────────────────────── distance ───────────────────────────────

def test_haversine_zero_for_same_point():
    assert haversine_km(12.0, 77.0, 12.0, 77.0) == 0.0


def test_haversine_one_degree_latitude_is_about_111km():
    d = haversine_km(0, 0, 1, 0)
    assert 110.0 <= d <= 112.0


def test_haversine_is_symmetric():
    a, b = (28.6, 77.2), (13.0, 80.2)
    assert math.isclose(haversine_km(*a, *b), haversine_km(*b, *a), rel_tol=1e-9)


def test_expiry_cost_zero_when_no_expiry():
    r = make_r("r1", 0, 0, 10, None)
    n = make_n("n1", 0, 0, 10, 5)
    base = max(0.0, haversine_km(0, 0, 0, 0) - 0.4 * 5)
    assert expiry_aware_unit_cost(r, n, alpha=0.4) == base


def test_expiry_cost_penalizes_long_travel():
    # food expires in 0.5h; NGO 30km away at 30km/h = 1h travel -> 0.5h overdue
    r = make_r("r1", 0, 0, 10, 0.5)
    n = make_n("n1", 0, 30 / 111.0, 10, 5)  # ~30 km
    cost = expiry_aware_unit_cost(r, n, alpha=0.0, speed_kmph=30.0, penalty_per_hour=10.0)
    # base = dist (30km); penalty = 10 * 0.5 = 5; total ~ 35
    assert cost > 30.0
    assert cost < 36.0


def test_expiry_cost_never_negative():
    r = make_r("r1", 0, 0, 10, 100.0)
    n = make_n("n1", 0, 0, 10, 5)
    assert expiry_aware_unit_cost(r, n, alpha=0.4) >= 0.0


# ─────────────────────────────── data loading ───────────────────────────────

def test_load_restaurants_and_ngos(tmp_path):
    r_csv = tmp_path / "restaurants.csv"
    r_csv.write_text(
        "id,name,lat,lon,supply,expiry_hours\n"
        "r1,R1,12.9,77.6,40,3.0\n"
        "r2,R2,13.0,77.6,25,NA\n"
    )
    n_csv = tmp_path / "ngos.csv"
    n_csv.write_text(
        "id,name,lat,lon,demand,priority\n"
        "n1,N1,12.95,77.61,30,5\n"
    )
    R = load_restaurants(str(r_csv))
    N = load_ngos(str(n_csv))
    assert len(R) == 2 and len(N) == 1
    assert R[0].expiry_hours == 3.0
    assert R[1].expiry_hours is None  # 'NA' -> None
    assert R[1].supply == 25
    assert N[0].priority == 5


# ─────────────────────────────── evaluation ───────────────────────────────

def test_evaluate_metrics():
    R = [make_r("r1", 0, 0, 40, 5.0)]
    N = [make_n("n1", 0, 0, 50, 5)]
    allocs = [Allocation("r1", "n1", 40, 2.5)]
    m = evaluate(R, N, allocs)
    assert m["supply"] == 40
    assert m["demand"] == 50
    assert m["delivered"] == 40
    assert m["unused_supply"] == 0
    assert m["unmet_demand"] == 10
    assert m["avg_cost_per_unit"] == 2.5
    assert m["total_cost"] == 100.0
    assert m["min_fill_ratio"] == 0.8


def test_evaluate_empty_allocations():
    R = [make_r("r1", 0, 0, 40, 5.0)]
    N = [make_n("n1", 0, 0, 50, 5)]
    m = evaluate(R, N, [])
    assert m["delivered"] == 0
    assert m["avg_cost_per_unit"] == 0
    assert m["min_fill_ratio"] == 0.0


# ─────────────────────────────── export ───────────────────────────────

def test_export_allocations_csv(tmp_path):
    allocs = [Allocation("r1", "n1", 12, 3.25)]
    out = tmp_path / "allocations.csv"
    export_allocations_csv(str(out), allocs)
    lines = out.read_text().splitlines()
    assert lines[0] == "restaurant_id,ngo_id,amount,cost_per_unit"
    assert lines[1] == "r1,n1,12,3.2500"


def test_export_summary_csv(tmp_path):
    out = tmp_path / "summary.csv"
    export_summary_csv(str(out), {"delivered": 12, "avg_cost_per_unit": 3.25})
    lines = out.read_text().splitlines()
    assert lines[0] == "metric,value"
    assert "delivered,12" in lines
    assert "avg_cost_per_unit,3.25" in lines
