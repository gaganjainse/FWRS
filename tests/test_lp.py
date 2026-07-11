from app.optimizer_lp import pipeline_lp
from app.models import Restaurant, NGO

def test_lp_pipeline_simple():
    R = [Restaurant('R1','A',0,0,40,1.0), Restaurant('R2','B',0,0,30,2.0)]
    N = [NGO('N1','X',0,0,50,5), NGO('N2','Y',0,0,20,3)]
    allocs = pipeline_lp(R,N,alpha=0.0)
    assert sum(a.amount for a in allocs) == 70
