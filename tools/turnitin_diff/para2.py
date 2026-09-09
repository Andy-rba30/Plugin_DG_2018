import re, json
from para import lines_of
NAMES=[("v2","7d85d95a-AI_Report_2.pdf"),("v11","2812f4f9-AI_Report.pdf"),
       ("v12_bloques","b4a12dae-AI_Report_3.pdf"),("v12_copia","c14f27af-AI_Report_4.pdf"),
       ("v12_final","b0c4540c-AI_Report_5.pdf")]

def build(fn):
    ls=[l for l in lines_of(fn) if 68 < l["y"] < 770]
    RIGHT=541.0
    ps=[]; cur=None; prev=None
    for l in ls:
        nb=False
        if cur is None: nb=True
        elif l["page"]!=prev["page"]:
            nb = prev["x1"] < RIGHT-45
        else:
            gap=l["y"]-prev["y"]
            nb = gap>25.5 or prev["x1"] < RIGHT-45
        if nb: cur=[]; ps.append(cur)
        cur.append(l); prev=l
    out=[]
    for i,p in enumerate(ps):
        m=" ".join(x["marked"].strip() for x in p)
        m=re.sub(r"\x02\s*\x01"," ",m); m=re.sub(r"\s+"," ",m).strip()
        plain=re.sub(r"[\x01\x02]","",m)
        fl=sum(x["fl"] for x in p); tot=sum(x["tot"] for x in p)
        out.append(dict(idx=i,page=p[0]["page"],marked=m,plain=plain,
                        fl=fl,tot=tot,pct=round(100*fl/max(tot,1)),
                        size=max(x["size"] for x in p),nlines=len(p)))
    return out

data={}
for tag,fn in NAMES:
    data[tag]=build(fn); print(tag,len(data[tag]),"paras")
json.dump(data,open("paras.json","w"),ensure_ascii=False,indent=0)
