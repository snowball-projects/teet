"""Independent HiGHS/PuLP oracle for the browser DP; optional developer check."""
import itertools
import json
from pathlib import Path
import subprocess
import pulp
ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'web/data.json').read_text())
cases=[dict(hero=h,dungeon=11,count=6,crit=True,mr=False,cdr=False) for h in data['classes']]
cases += [dict(hero=h,dungeon=8,count=6,crit=c,mr=m,cdr=d) for h in ['Champion','Dark ArchTemplar'] for c,m,d in itertools.product([False,True],repeat=3)]
js="import {optimize} from './web/optimizer.js'; let s='';for await(const c of process.stdin)s+=c;const {data,cases}=JSON.parse(s);console.log(JSON.stringify(cases.map(p=>{try{return {score:optimize(data,p).score}}catch{return {infeasible:true}}})));"
actual=json.loads(subprocess.check_output(['node','--input-type=module','-e',js],cwd=ROOT,input=json.dumps(dict(data=data,cases=cases)),text=True))
for case,got in zip(cases,actual):
    items=[i for i in data['items'] if case['hero'] in i['classes'] and i['stats']['Dungeon']<=case['dungeon']]
    weights=data['weights'][case['hero']].copy()
    for stat in ['Str','Agi','Int']:
        if stat!=data['primary'][case['hero']]: weights['Total_DMG_'+stat]=0
    p=pulp.LpProblem('reference',pulp.LpMaximize)
    xs=[pulp.LpVariable('x'+str(i),cat=pulp.LpBinary) for i in range(len(items))]
    scores=[sum(i['stats'].get(k,0)*v for k,v in weights.items()) for i in items]
    p+=pulp.lpSum(x*v for x,v in zip(xs,scores));p+=pulp.lpSum(xs)==case['count']
    if case['crit']:p+=pulp.lpSum(x for x,i in zip(xs,items) if i['stats']['CC']>0 or i['stats']['CX']>0)<=1
    for option,stat in [('mr','MR'),('cdr','CDS')]:
        matching=[x for x,i in zip(xs,items) if i['stats'][stat]>0]
        if case[option] and matching:p+=pulp.lpSum(matching)>=1
    status=p.solve(pulp.HiGHS(msg=False))
    if pulp.LpStatus[status]=='Infeasible':assert got.get('infeasible'),case
    else:
        assert pulp.LpStatus[status]=='Optimal',case
        assert abs(got['score']-pulp.value(p.objective))<1e-5,(case,got,pulp.value(p.objective))
print(f'{len(cases)} browser results match independent HiGHS/PuLP solves')
