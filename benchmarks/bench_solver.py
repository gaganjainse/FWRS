"""Real hot-path benchmarks for FWRS (stdlib only, CI-safe).

The LP allocation solver is the core hot path: measures the full
3-stage lexicographic pipeline on synthetic instances of increasing
size. Median of N runs, loose bounds. Run:  python benchmarks/bench_solver.py
"""

from __future__ import annotations

import random
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import NGO, Restaurant  # noqa: E402
from app.optimizer_lp import pipeline_lp  # noqa: E402


def bench(label: str, fn, n: int = 20) -> float:
    times: list[float] = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    med = statistics.median(times)
    print(f"  {label:44s} median {med * 1e3:9.2f} ms  (n={n})")
    return med


def make_instance(n_rest: int, n_ngo: int, seed: int = 42) -> tuple[list[Restaurant], list[NGO]]:
    rng = random.Random(seed)
    rest = [
        Restaurant(id=f"R{i}", name=f"R{i}", lat=rng.uniform(26.7, 26.9),
                   lon=rng.uniform(75.7, 75.9), supply=rng.randint(50, 500),
                   expiry_hours=rng.uniform(1.0, 6.0))
        for i in range(n_rest)
    ]
    ngos = [
        NGO(id=f"N{i}", name=f"N{i}", demand=rng.randint(10, 200),
            lat=rng.uniform(26.7, 26.9), lon=rng.uniform(75.7, 75.9),
            priority=rng.randint(1, 10))
        for i in range(n_ngo)
    ]
    return rest, ngos


def main() -> int:
    for n_rest, n_ngo in ((10, 20), (20, 50), (40, 100)):
        R, N = make_instance(n_rest, n_ngo)
        bench(f"LP pipeline ({n_rest} restaurants / {n_ngo} NGOs)",
              lambda: pipeline_lp(R, N), n=15)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
