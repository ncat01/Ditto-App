from pathlib import Path
import json, sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.matching.video import frames, compare
ROOT=Path(__file__).resolve().parents[2]
dataset=json.loads((ROOT/'demo_data/manifest.json').read_text())
threshold=.80  # Prespecified; no fitting on held-out creators.
counts={'tp':0,'fp':0,'tn':0,'fn':0}; results=[];cache={}
for item in dataset['items']:
    if item['split']!='held_out':continue
    a=item['original'];b=item['candidate']
    if a not in cache:cache[a]=frames(ROOT/'demo_data/videos'/a)
    score=compare(cache[a],frames(ROOT/'demo_data/videos'/b))
    predicted=score>=threshold; truth=item['match']
    counts['tp' if predicted and truth else 'fp' if predicted else 'fn' if truth else 'tn']+=1
    results.append({**item,'similarity':score,'prediction':predicted})
tp,fp,tn,fn=[counts[x] for x in ['tp','fp','tn','fn']]
p=tp/(tp+fp) if tp+fp else 0;r=tp/(tp+fn) if tp+fn else 0
report={'task':'synthetic near-duplicate video detection only','threshold':threshold,'pairs':len(results),'held_out_creators':10,'precision':p,'recall':r,'f1':2*p*r/(p+r) if p+r else 0,'false_positive_rate':fp/(fp+tn) if fp+tn else 0,'confusion_matrix':counts,'limitations':['Abstract generated videos only; no real-world validation','No calibrated confidence, deepfake detection, or human-reviewer evaluation','Temporal samples assume aligned clips; edits may evade detection'],'results':results}
(ROOT/'demo_data/evaluation.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='results'},indent=2))
