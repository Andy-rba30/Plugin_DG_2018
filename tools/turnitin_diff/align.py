import json, re, unicodedata
D=json.load(open("paras.json"))
def norm(s):
    s=unicodedata.normalize("NFKD",s.lower())
    s="".join(c for c in s if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9]+",s)
for tag,ps in D.items():
    for p in ps:
        w=norm(p["plain"]); p["ws"]=set(w); p["nw"]=len(w)
def sim(a,b):
    if not a["ws"] or not b["ws"]: return 0.0
    i=len(a["ws"]&b["ws"]); u=len(a["ws"]|b["ws"])
    return i/u
def align(A,B):
    n,m=len(A),len(B); GAP=-0.35
    import numpy as np
    S=np.zeros((n+1,m+1)); P=np.zeros((n+1,m+1),dtype=np.int8)
    for i in range(1,n+1): S[i][0]=S[i-1][0]+GAP; P[i][0]=1
    for j in range(1,m+1): S[0][j]=S[0][j-1]+GAP; P[0][j]=2
    for i in range(1,n+1):
        Ai=A[i-1]
        for j in range(1,m+1):
            d=S[i-1][j-1]+ (sim(Ai,B[j-1])-0.25)
            u=S[i-1][j]+GAP; l=S[i][j-1]+GAP
            if d>=u and d>=l: S[i][j]=d; P[i][j]=0
            elif u>=l: S[i][j]=u; P[i][j]=1
            else: S[i][j]=l; P[i][j]=2
    i,j=n,m; pairs=[]
    while i>0 or j>0:
        p=P[i][j]
        if i>0 and j>0 and p==0: pairs.append((i-1,j-1)); i-=1; j-=1
        elif i>0 and p==1: pairs.append((i-1,None)); i-=1
        else: pairs.append((None,j-1)); j-=1
    return pairs[::-1]
base=D["v2"]
res={}
for tag in ["v11","v12_bloques","v12_copia","v12_final"]:
    res[tag]=align(base,D[tag])
    print(tag,"aligned pairs:",sum(1 for a,b in res[tag] if a is not None and b is not None))
json.dump({k:[[a,b] for a,b in v] for k,v in res.items()},open("align.json","w"))
