import json,re,unicodedata
D=json.load(open("paras.json")); A=json.load(open("align.json"))
def norm(s):
    s=unicodedata.normalize("NFKD",s.lower()); s="".join(c for c in s if not unicodedata.combining(c))
    return set(re.findall(r"[a-z0-9]+",s))
V=["v11","v12_bloques","v12_copia","v12_final"]
maps={t:{a:b for a,b in A[t] if a is not None and b is not None} for t in V}
base=D["v2"]
big=[ (i,p) for i,p in enumerate(base) if len(norm(p["plain"]))>=25 ]
flag=[(i,p) for i,p in big if p["pct"]>0]
print("v2: %d parrafos de contenido (>=25 palabras); %d marcados con IA"%(len(big),len(flag)))
rows=[]
for i,p in flag:
    row=dict(i=i,page=p["page"],pct=p["pct"],chars=p["tot"],text=p["plain"])
    for t in V:
        j=maps[t].get(i)
        if j is None: row[t]=None; continue
        q=D[t][j]; s=norm(p["plain"]); r=norm(q["plain"])
        row[t]=dict(j=j,pct=q["pct"],sim=round(len(s&r)/len(s|r),2),page=q["page"],text=q["plain"])
    rows.append(row)
def cands(r,maxpct=10,minsim=0.25,maxsim=0.90):
    return [t for t in V if r[t] and r[t]["pct"]<=maxpct and minsim<=r[t]["sim"]<=maxsim]
def ident_flip(r):
    return [t for t in V if r[t] and r[t]["pct"]<=10 and r[t]["sim"]>0.95]
rw=[r for r in rows if cands(r)]
idf=[r for r in rows if not cands(r) and ident_flip(r)]
print("  -> %d con REESCRITURA limpia (<=10%% IA, texto realmente distinto)"%len(rw))
print("  -> %d limpios solo por ruido del detector (texto identico, veredicto distinto)"%len(idf))
print("  -> %d sin alternativa limpia en ninguna version"%(len(rows)-len(rw)-len(idf)))
print("caracteres marcados recuperables por reescritura: %d de %d (%.0f%%)"%(
    sum(r["chars"]*r["pct"]/100 for r in rw), sum(r["chars"]*r["pct"]/100 for r in rows),
    100*sum(r["chars"]*r["pct"]/100 for r in rw)/sum(r["chars"]*r["pct"]/100 for r in rows)))
json.dump(rows,open("rows.json","w"),ensure_ascii=False)
json.dump([r["i"] for r in rw],open("rw.json","w"))
print()
for r in rw:
    c=cands(r)
    print("### v2 p.%d | %d%% IA | %d car | fuentes limpias: %s"%(r["page"],r["pct"],r["chars"],
        ", ".join("%s(%d%%,sim %.2f)"%(t,r[t]["pct"],r[t]["sim"]) for t in c)))
