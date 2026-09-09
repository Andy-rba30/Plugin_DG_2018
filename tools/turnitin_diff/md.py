import json,re
D=json.load(open("paras.json")); F=json.load(open("final.json"))
LBL={"v11":"v11 (38 %)","v12_bloques":"v12 bloques (46 %)","v12_copia":"v12 copia (53 %)","v12_final":"v12 final (48 %)"}
A=json.load(open("align.json"))
V=["v11","v12_bloques","v12_copia","v12_final"]
maps={t:{a:b for a,b in A[t] if a is not None and b is not None} for t in V}
base=D["v2"]
heads=[(i,p["plain"].strip()) for i,p in enumerate(base) if p["size"]>=14 and len(p["plain"].strip())<95]
heads=[h for h in heads if not h[1].startswith(("ÍNDICE","Tabla A1"))]+[(82,"1. INTRODUCCIÓN")]
heads.sort()
def section(i):
    s=""
    for j,h in heads:
        if j<=i: s=h
    return s or "(preliminares)"
def mk(s): return s.replace("\x01","**[").replace("\x02","]**")
L=[]
L.append("# Comparativa de informes Turnitin AI — TFG Bejarano\n")
L.append("Base de trabajo: **v2** (`TFG_Bejarano_v2_recortado.docx`, 41 % IA).\n")
L.append("| Informe | Archivo | % IA | Palabras |")
L.append("|---|---|---|---|")
for a,b,c,d in [("AI_Report_2 (v2 — BASE)","TFG_Bejarano_v2_recortado.docx","41 %","14.089"),
 ("AI_Report (v11)","TFG_Bejarano_v11_tipografia-coherencia.docx","**38 %**","15.010"),
 ("AI_Report_3 (v12 bloques)","TFG_Bejarano_v12_reescrito_bloques_pri…","46 %","13.691"),
 ("AI_Report_5 (v12 final)","TFG_Bejarano_v12_revision_localizada_academica_FINAL_1","48 %","13.825"),
 ("AI_Report_4 (v12 copia)","TFG_Bejarano_v12_COPIA_reescrita_ac…","53 %","13.789")]:
    L.append("| %s | `%s` | %s | %s |"%(a,b,c,d))
L.append("\n## Sustituciones aprovechables (%d)\n"%len(F["sub"]))
for n,(i,c,kind) in enumerate(F["sub"],1):
    t=c[0]; j=maps[t][i]
    L.append("### [%02d] %s — v2 pág. %d — %s"%(n,section(i),base[i]["page"],kind))
    L.append("`v2 %d %% → %s %d %%`  ·  otras fuentes: %s\n"%(base[i]["pct"],LBL[t],D[t][j]["pct"],
        ", ".join(LBL[x] for x in c[1:]) or "—"))
    L.append("**Actual (v2)** — `[...]` = marcado como IA\n")
    L.append("> "+mk(base[i]["marked"])+"\n")
    L.append("**Reemplazo (%s, pág. %d)**\n"%(LBL[t],D[t][j]["page"]))
    L.append("> "+mk(D[t][j]["marked"])+"\n")
L.append("\n## Pendientes sin alternativa limpia (%d)\n"%len(F["pend"]))
P=sorted(F["pend"],key=lambda i:-(base[i]["tot"]*base[i]["pct"]/100))
for n,i in enumerate(P,1):
    mejor=min([t for t in V if maps[t].get(i) is not None],key=lambda t:D[t][maps[t][i]]["pct"],default=None)
    mn=" · mejor en otras versiones: %s %d %%"%(LBL[mejor],D[mejor][maps[mejor][i]]["pct"]) if mejor else ""
    L.append("### [P%02d] %s — v2 pág. %d — %d %% IA%s"%(n,section(i),base[i]["page"],base[i]["pct"],mn))
    L.append("> "+mk(base[i]["marked"])+"\n")
open("INFORME_COMPARATIVO_IA.md","w").write("\n".join(L))
print("ok", len(L))
