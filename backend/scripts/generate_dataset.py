"""Fixed-seed generated assets. Evaluation creators are disjoint from demo creators."""
from pathlib import Path
import json
import random
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'demo_data/videos'
OUT.mkdir(parents=True,exist_ok=True)
def scene(seed, t):
    rng=random.Random(seed)
    img=np.zeros((240,320,3),np.uint8)
    colors=[tuple(rng.randrange(25,230) for _ in range(3)) for _ in range(8)]
    img[:]=colors[0]
    for i in range(6):
        x=rng.randrange(25,295);y=rng.randrange(25,215)
        cv2.circle(img,(int(x+8*np.sin(t/7+i)),y),rng.randrange(10,45),colors[i+1],-1)
    cv2.rectangle(img,(12,190),(300,235),colors[7],-1)
    cv2.putText(img,f'CREATOR {seed}',(15,225),cv2.FONT_HERSHEY_SIMPLEX,.55,(255,255,255),1)
    return img
def write(path, frames):
    first=frames[0];writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'mp4v'),10,(first.shape[1],first.shape[0]))
    if not writer.isOpened(): raise RuntimeError('MP4 encoder unavailable')
    for frame in frames:writer.write(frame)
    writer.release()
def transform(frames,kind):
    result=[]
    for f in frames:
        f=f.copy()
        if kind=='crop':f=cv2.resize(f[6:-6,8:-8],(320,240))
        if kind=='resize':f=cv2.resize(f,(256,192))
        if kind=='watermark':cv2.putText(f,'DEMO',(232,182),cv2.FONT_HERSHEY_SIMPLEX,.4,(255,255,255),1)
        if kind=='caption':cv2.rectangle(f,(0,0),(320,18),(40,40,40),-1)
        result.append(f)
    return result
manifest=[]
for seed in list(range(1,6))+list(range(101,111)):
    original=[scene(seed,t) for t in range(30)]
    name=f'original_{seed}.mp4';write(OUT/name,original)
    for kind in ['exact','crop','resize','watermark','caption','reencoded','credited','authorized','ambiguous','unrelated','fake_endorsement']:
        source=[scene(seed+900,t) for t in range(30)] if kind in ['unrelated','fake_endorsement'] else original
        derivative=transform(source,'crop' if kind=='ambiguous' else kind)
        candidate=f'{seed}_{kind}.mp4';write(OUT/candidate,derivative)
        manifest.append({'creator':f'fictional_{seed}','original':name,'candidate':candidate,'kind':kind,'match':kind not in ['unrelated','fake_endorsement'],'attribution':'credited' if kind=='credited' else 'absent','permission':'authorized' if kind=='authorized' else 'unknown','split':'held_out' if seed>=101 else 'demo','simulated_manipulation':kind=='fake_endorsement'})
(OUT.parent/'manifest.json').write_text(json.dumps({'seed':20261005,'assets':'procedurally generated abstract scenes; no real people','items':manifest},indent=2))
print(f'Generated {len(manifest)} labelled pairs. No training or human review claimed.')
