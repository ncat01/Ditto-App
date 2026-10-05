"""Measured video-frame pHash. No face/manipulation inference."""
from pathlib import Path
import cv2
import imagehash
from PIL import Image

def frames(path: str, count=5):
    cap=cv2.VideoCapture(str(path))
    if not cap.isOpened(): raise ValueError("Video cannot be decoded")
    total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    output=[]
    try:
        for i in range(count):
            index=int(max(0,total-1)*i/max(1,count-1))
            cap.set(cv2.CAP_PROP_POS_FRAMES,index)
            ok, frame=cap.read()
            if not ok: raise ValueError("Video frame cannot be decoded")
            output.append(str(imagehash.phash(Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)))))
    finally: cap.release()
    return output

def compare(a,b):
    if not a or len(a)!=len(b): raise ValueError("Incompatible video fingerprints")
    return sum(1-(int(x,16)^int(y,16)).bit_count()/64 for x,y in zip(a,b))/len(a)
