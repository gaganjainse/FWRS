import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from flask import Flask, render_template_string, request, send_file
import io, csv
from app.data_loader import load_restaurants, load_ngos
from app.optimizer_lp import pipeline_lp
from app.evaluator import evaluate

app = Flask(__name__)

TPL = """
<!doctype html>
<title>Food Allocation (LP)</title>
<h2>LP Allocator — Lexicographic Fairness + Priority</h2>
<form method="post">
  α (priority weight in cost stage):
  <input type="number" step="0.1" name="alpha" value="{{ alpha }}">
  <button type="submit">Run</button>
</form>
{% if metrics %}
  <h3>Summary</h3>
  <ul>
    {% for k,v in metrics.items() %}<li><b>{{k}}</b>: {{v}}</li>{% endfor %}
  </ul>
  <h3>Allocations</h3>
  <table border=1 cellpadding=6>
    <tr><th>Restaurant</th><th>NGO</th><th>Amount</th><th>Cost/Unit</th></tr>
    {% for a in allocations %}
      <tr><td>{{a.restaurant_id}}</td><td>{{a.ngo_id}}</td><td>{{a.amount}}</td><td>{{'%.2f'|format(a.cost_per_unit)}}</td></tr>
    {% endfor %}
  </table>
  <form method="post">
    <input type="hidden" name="alpha" value="{{ alpha }}">
    <button name="download" value="1">Download CSV</button>
  </form>
{% endif %}
"""

@app.route('/', methods=['GET','POST'])
def index():
    alpha = float(request.form.get('alpha', 0.4))
    allocations, metrics = [], None
    if request.method == 'POST':
        R = load_restaurants('data/restaurants.csv')
        N = load_ngos('data/ngos.csv')
        allocations = pipeline_lp(R, N, alpha=alpha)
        metrics = evaluate(R, N, allocations)
        if request.form.get('download') == '1':
            mem = io.StringIO()
            w = csv.writer(mem)
            w.writerow(['restaurant_id','ngo_id','amount','cost_per_unit'])
            for a in allocations:
                w.writerow([a.restaurant_id, a.ngo_id, a.amount, f"{a.cost_per_unit:.4f}"])
            mem.seek(0)
            return send_file(
                io.BytesIO(mem.getvalue().encode('utf-8')),
                mimetype='text/csv',
                as_attachment=True,
                download_name='allocations.csv'
            )
    return render_template_string(TPL, alpha=alpha, allocations=allocations, metrics=metrics)

if __name__ == '__main__':
    app.run(debug=True)
