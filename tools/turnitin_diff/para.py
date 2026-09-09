import pymupdf, re, json, unicodedata
U="/root/.claude/uploads/15443fd3-ec81-544a-adc5-459e253b49eb/"
NAMES=[("v2","7d85d95a-AI_Report_2.pdf"),("v11","2812f4f9-AI_Report.pdf"),
       ("v12_bloques","b4a12dae-AI_Report_3.pdf"),("v12_copia","c14f27af-AI_Report_4.pdf"),
       ("v12_final","b0c4540c-AI_Report_5.pdf")]
CY=(0.3203125,0.77734375,0.85546875)
def iscy(c): return c is not None and all(abs(a-b)<0.06 for a,b in zip(c,CY))
HDR=re.compile(r"(Page \d+ of \d+|Submission ID|trn:oid|AI Writing Submission)")

def lines_of(fn):
    d=pymupdf.open(U+fn); res=[]
    for pi in range(2,d.page_count):
        p=d[pi]
        rects=[pymupdf.Rect(x['rect']) for x in p.get_drawings()
               if x['type']=='f' and iscy(x.get('fill'))]
        for bi,blk in enumerate(p.get_text("dict")["blocks"]):
            if blk["type"]!=0: continue
            for ln in blk["lines"]:
                spans=[s for s in ln["spans"] if s["text"].strip()]
                if not spans: continue
                plain="".join(s["text"] for s in spans)
                if HDR.search(plain): continue
                out=[];fl=0;tot=0
                for sp in spans:
                    t=sp["text"];x0,y0,x1,y1=sp["bbox"];n=len(t)
                    w=(x1-x0)/n if n else 0; cy=(y0+y1)/2; state=False
                    for i,ch in enumerate(t):
                        cx=x0+w*(i+0.5)
                        hi=any(r.x0-1<=cx<=r.x1+1 and r.y0-1<=cy<=r.y1+1 for r in rects)
                        if not ch.isspace():
                            tot+=1; fl+=1 if hi else 0
                        if hi!=state:
                            out.append("\x01" if hi else "\x02"); state=hi
                        out.append(ch)
                    if state: out.append("\x02"); state=False
                res.append(dict(page=pi+1,blk=bi,y=round(ln["bbox"][1],1),
                    x0=round(ln["bbox"][0],1),x1=round(ln["bbox"][2],1),
                    size=round(max(s["size"] for s in spans),1),
                    bold=any("Bold" in s["font"] for s in spans),
                    marked="".join(out),plain=plain,fl=fl,tot=tot))
    return res

def paras(lines):
    ps=[];cur=None
    RIGHT=max(l["x1"] for l in lines)
    for l in lines:
        newp = cur is None or l["blk"]!=cur["blk"] or l["page"]!=cur["page"]
        if not newp and cur["lines"][-1]["x1"] < RIGHT-40: newp=True
        # continuation across page: previous para line reached right margin
        if newp and cur is not None and l["page"]!=cur["page"] and cur["lines"][-1]["x1"]>=RIGHT-40 \
           and not cur["lines"][-1]["plain"].rstrip().endswith(('.',':')) :
            newp=False
        if newp:
            cur=dict(page=l["page"],blk=l["blk"],lines=[l]); ps.append(cur)
        else:
            cur["lines"].append(l); cur["blk"]=l["blk"]; cur["page"]=l["page"]
    out=[]
    for p in ps:
        marked=" ".join(x["marked"].strip() for x in p["lines"])
        marked=re.sub(r"»\s*«"," ",marked); marked=re.sub(r"\s+"," ",marked).strip()
        plain=re.sub(r"[«»]","",marked)
        fl=sum(x["fl"] for x in p["lines"]); tot=sum(x["tot"] for x in p["lines"])
        out.append(dict(page=p["page"],size=max(x["size"] for x in p["lines"]),
                        bold=any(x["bold"] for x in p["lines"]),
                        marked=marked,plain=plain,fl=fl,tot=tot,
                        pct=round(100*fl/max(tot,1))))
    return out

data={}
for tag,fn in NAMES:
    ps=paras(lines_of(fn)); data[tag]=ps
    print(tag,len(ps),"paragraphs")
json.dump(data,open("paras.json","w"),ensure_ascii=False,indent=0)
