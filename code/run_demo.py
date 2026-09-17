"""Run ONLY constructed examples. Never labels these outputs as field results."""
from pathlib import Path
import csv, json, itertools, sys, platform
import numpy as np
from core import (window_status, reference_window_status, scenario_window_probability,
                  Task, solve_deterministic)
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs'; OUT.mkdir(exist_ok=True)

def main():
    rows=[]
    A=[8,8,8,8,8,8,25,25]
    B=[8,8,25,8,8,25,8,8]
    for name,g in [('contiguous',A),('fragmented',B)]:
        z=window_status(g,3,11.1,20)
        rows.append({'case':name,'source_type':'constructed_not_observed',
                     'slots':len(g),'below_start_limit_slots':sum(v<=11.1 for v in g),
                     'duration':3,'admissible_start_windows':int((z==1).sum())})
    with (OUT/'constructed_windows.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    correlated=[[8,8],[25,25]]
    anticorrelated=[[8,25],[25,8]]
    marginal={
      'source_type':'constructed_not_observed',
      'first_law_one_hour_admissibility':[.5,.5],
      'second_law_one_hour_admissibility':[.5,.5],
      'first_law_two_hour_window_probability':float(scenario_window_probability(correlated,2,11.1,20)[0]),
      'second_law_two_hour_window_probability':float(scenario_window_probability(anticorrelated,2,11.1,20)[0]),
      'independence_product_in_both':.25}
    (OUT/'equal_marginals_counterexample.json').write_text(json.dumps(marginal,indent=2))
    checked=0
    for seq in itertools.product([8,15,25],repeat=8):
        for d in [1,2,3,4]:
            a=window_status(seq,d,11.1,20)
            b=reference_window_status(seq,d,11.1,20)
            if not np.array_equal(a,b):raise AssertionError((seq,d,a,b))
            checked+=1
    # Deterministic known-path illustration. Weather is deliberately constructed.
    g=[8,8,15,15,25,25,8,8,8,15,8,8,25,8,8,8]
    H=len(g)
    def starts(d,sensitive=True):
        return tuple(np.flatnonzero(window_status(g,d,11.1,20)==1).tolist()) if sensitive else tuple(range(H-d+1))
    tasks=[Task('prepare',2,(),(1,),starts(2,False)),
           Task('lift_A',3,('prepare',),(1,),starts(3)),
           Task('lift_B',2,('prepare',),(1,),starts(2)),
           Task('finish',2,('lift_A','lift_B'),(1,),starts(2,False))]
    result=solve_deterministic(tasks,[1],H)
    (OUT/'deterministic_toy_schedule.json').write_text(json.dumps(result,indent=2))
    report={'status':'PASS','source_type':'constructed_verification_only',
            'enumerated_weather_paths':3**8,'duration_variants_per_path':4,
            'vector_reference_comparisons':checked,'comparison_failures':0,
            'observed_weather_used_in_this_demo':False,
            'project_network_type':'constructed',
            'report_scope':'constructed kernel only; does not overwrite live project status',
            'python':sys.version.split()[0],'numpy':np.__version__, 'platform':platform.system(),
            'toy_scheduler_status':result['status'],'toy_makespan':result.get('makespan')}
    (OUT/'constructed_kernel_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
