from app.data_loader import load_restaurants, load_ngos
from app.optimizer_lp import pipeline_lp
from app.evaluator import evaluate_and_print, evaluate
from app.exporter import export_allocations_csv, export_summary_csv

def run(alpha=0.4, export=None, export_summary=None):
    R = load_restaurants("data/restaurants.csv")
    N = load_ngos("data/ngos.csv")
    allocs = pipeline_lp(R, N, alpha=alpha)
    metrics = evaluate(R, N, allocs)
    evaluate_and_print(R, N, allocs)
    if export:
        export_allocations_csv(export, allocs)
        print(f"\nAllocations CSV exported to: {export}")
    if export_summary:
        export_summary_csv(export_summary, metrics)
        print(f"Summary CSV exported to: {export_summary}")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--alpha", type=float, default=0.4, help="Priority weight in cost stage (non-negative)")
    ap.add_argument("--export", type=str, default=None)
    ap.add_argument("--export-summary", type=str, default=None)
    args = ap.parse_args()
    run(alpha=args.alpha, export=args.export, export_summary=args.export_summary)
