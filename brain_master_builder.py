#!/usr/bin/env python3
import os,re,json
from datetime import datetime
from collections import Counter
BASE_DIR="/home/madbrad/BETA/app"
INPUT_FILE=os.path.join(BASE_DIR,"input.txt")
OUTPUT_FILE=os.path.join(BASE_DIR,"brain_master_output.json")
def readf(p):
    with open(p,"r",encoding="utf-8",errors="ignore") as f:return f.read()
def clean(t):
    return re.sub(r"\n{3,}","\n\n",t.replace("\r","\n").replace("_x000D_","")).strip()
def title(t):
    for l in t.splitlines()[:20]:
        s=l.strip()
        if s and len(s)<70 and s.upper()==s and not s.startswith(("INT.","EXT.")): return s.title()
    return "Untitled Project"
def genre(t):
    x=t.lower()
    if any(w in x for w in ["kill","crime","gun","murder","chase"]): return "Thriller"
    if any(w in x for w in ["laugh","funny","joke","party","bbq"]): return "Comedy"
    if any(w in x for w in ["kiss","love","relationship"]): return "Romance"
    return "Drama"
def chars(t):
    c=Counter()
    for l in t.splitlines():
        s=l.strip()
        if 2<=len(s)<=30 and s.isupper() and not s.startswith(("INT.","EXT.")): c[s.title()]+=1
    out=[]
    for i,(n,m) in enumerate(c.most_common(12)):
        out.append({"name":n,"role":"Protagonist" if i==0 else "Supporting","mentions":m})
    return out
def scenes(t):
    lines=t.splitlines(); idx=[]
    for i,l in enumerate(lines):
        s=l.strip().upper()
        if s.startswith(("INT.","EXT.","INT/EXT.","I/E.")): idx.append((i,l.strip()))
    out=[]
    for n,(start,slug) in enumerate(idx, start=1):
        out.append({"scene_number":n,"slugline":slug,"deck_worthy":True})
    return out
def main():
    txt=clean(readf(INPUT_FILE))
    data={
      "project":{"title":title(txt),"build_time":datetime.now().isoformat(),"source":"input.txt"},
      "script_identity":{"primary_genre":genre(txt)},
      "characters":chars(txt),
      "scenes":scenes(txt),
      "exports":{"deck_ready":True,"analysis_ready":True,"actor_prep_ready":True}
    }
    with open(OUTPUT_FILE,"w",encoding="utf-8") as f: json.dump(data,f,indent=2)
    print("brain_master_output.json created")
if __name__=="__main__": main()
