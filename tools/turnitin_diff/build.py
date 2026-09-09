import json,re,unicodedata
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.text import WD_COLOR_INDEX

D=json.load(open("paras.json")); A=json.load(open("align.json"))
V=["v11","v12_bloques","v12_copia","v12_final"]
LBL={"v2":"v2 (41 % IA)","v11":"v11 (38 % IA)","v12_bloques":"v12 bloques (46 % IA)",
     "v12_copia":"v12 copia (53 % IA)","v12_final":"v12 final (48 % IA)"}
FILE={"v2":"TFG_Bejarano_v2_recortado.docx","v11":"TFG_Bejarano_v11_tipografia-coherencia.docx",
 "v12_bloques":"TFG_Bejarano_v12_reescrito_bloques_pri….docx",
 "v12_copia":"TFG_Bejarano_v12_COPIA_reescrita_ac….docx",
 "v12_final":"source-TFG_Bejarano_v12_revision_localizada_academica_FINAL_1.docx"}
def norm(s):
    s=unicodedata.normalize("NFKD",s.lower()); s="".join(c for c in s if not unicodedata.combining(c))
    return set(re.findall(r"[a-z0-9]+",s))
maps={t:{a:b for a,b in A[t] if a is not None and b is not None} for t in V}
base=D["v2"]
# headings
heads=[(i,p["plain"].strip()) for i,p in enumerate(base) if p["size"]>=14 and len(p["plain"].strip())<95]
heads=[h for h in heads if not h[1].startswith(("ÍNDICE","Tabla A1"))]+[(82,"1. INTRODUCCIÓN")]
heads.sort()
def section(i):
    s=""
    for j,h in heads:
        if j<=i: s=h
    return s or "(preliminares)"

rows=[]
for i,p in enumerate(base):
    if len(norm(p["plain"]))<25 or p["pct"]==0: continue
    r=dict(i=i,page=p["page"],pct=p["pct"],chars=p["tot"])
    for t in V:
        j=maps[t].get(i)
        if j is None: r[t]=None; continue
        q=D[t][j]; s=norm(p["plain"]); w=norm(q["plain"])
        r[t]=dict(j=j,pct=q["pct"],sim=round(len(s&w)/len(s|w),2),page=q["page"])
    rows.append(r)
def cands(r,maxpct):
    return sorted([t for t in V if r[t] and r[t]["pct"]<=maxpct and 0.25<=r[t]["sim"]<=0.90],
                  key=lambda t:(r[t]["pct"],-r[t]["sim"]))
SUB=[];PEND=[]
for r in rows:
    c=cands(r,10)
    if c: SUB.append((r,c,"LIMPIA")); continue
    c=cands(r,25)
    if c and r["pct"]-r[c[0]]["pct"]>=25: SUB.append((r,c,"MEJORA PARCIAL")); continue
    PEND.append(r)

doc=Document()
st=doc.styles["Normal"]; st.font.name="Calibri"; st.font.size=Pt(10.5)
def H(txt,lvl=1):
    h=doc.add_heading(txt,lvl); return h
def marked_para(marked,pre="",color=None):
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
    if pre:
        r=p.add_run(pre); r.bold=True
    state=False
    buf=""
    def flush(s,hi):
        if not s: return
        run=p.add_run(s)
        if hi: run.font.highlight_color=WD_COLOR_INDEX.YELLOW
    for ch in marked:
        if ch=="\x01":
            flush(buf,state); buf=""; state=True
        elif ch=="\x02":
            flush(buf,state); buf=""; state=False
        else: buf+=ch
    flush(buf,state)
    return p

doc.add_heading("Sustituciones humanizadas para la versión 2",0)
p=doc.add_paragraph()
p.add_run("TFG «Evolución de la inversión publicitaria del sector de automoción en España "
          "dentro de la transformación del ecosistema mediático (2007–2025)» — María Bejarano Bonilla.\n").italic=True
p.add_run("Documento base: TFG_Bejarano_v2_recortado.docx (41 % IA en Turnitin).\n")
p.add_run("Amarillo = fragmento marcado como IA por Turnitin en esa versión.")

H("1. Comparativa de las cinco versiones",1)
tb=doc.add_table(rows=1,cols=5); tb.style="Light Grid Accent 1"
for k,v in zip(tb.rows[0].cells,["Informe","Archivo","% IA","Palabras","Frases marcadas"]):
    k.text=v
DATA=[("AI_Report_2 (v2 — BASE)","TFG_Bejarano_v2_recortado.docx","41 %","14.089","40"),
      ("AI_Report (v11)","TFG_Bejarano_v11_tipografia-coherencia.docx","38 %","15.010","37"),
      ("AI_Report_3 (v12 bloques)","TFG_Bejarano_v12_reescrito_bloques_pri…","46 %","13.691","46"),
      ("AI_Report_5 (v12 final)","TFG_Bejarano_v12_revision_localizada_academica_FINAL_1","48 %","13.825","41"),
      ("AI_Report_4 (v12 copia)","TFG_Bejarano_v12_COPIA_reescrita_ac…","53 %","13.789","46")]
for row in DATA:
    c=tb.add_row().cells
    for cc,vv in zip(c,row): cc.text=vv
doc.add_paragraph()
doc.add_paragraph("En la v2 hay 135 párrafos de contenido (≥25 palabras); 57 llevan marca de IA. "
 "De esos 57, %d tienen una reescritura utilizable en alguna versión posterior y %d siguen sin "
 "alternativa limpia en ninguna de las cinco."%(len(SUB),len(PEND)))

H("2. Sustituciones propuestas (%d bloques)"%len(SUB),1)
for n,(r,c,kind) in enumerate(SUB,1):
    t=c[0]
    H("[%02d] %s — v2 pág. %d — %s"%(n,section(r["i"])[:70],r["page"],kind),2)
    q=doc.add_paragraph()
    q.add_run("IA en v2: %d %%  →  %s: %d %%  ·  similitud léxica %.2f  ·  origen: %s (pág. %d)"%(
        r["pct"],LBL[t],r[t]["pct"],r[t]["sim"],FILE[t],r[t]["page"])).italic=True
    if len(c)>1:
        doc.add_paragraph("Otras fuentes válidas: "+", ".join("%s %d %%"%(LBL[x],r[x]["pct"]) for x in c[1:]))
    marked_para(D["v2"][r["i"]]["marked"],"TEXTO ACTUAL EN v2 — ")
    marked_para(D[t][r[t]["j"]]["marked"],"REEMPLAZO PROPUESTO — ")

H("3. Párrafos de la v2 sin alternativa limpia (%d)"%len(PEND),1)
doc.add_paragraph("Estos párrafos siguen marcados como IA en la v2 y en todas las versiones "
 "posteriores comparables: hay que reescribirlos a mano. Se ordenan por volumen de texto marcado.")
PEND.sort(key=lambda r:-(r["chars"]*r["pct"]/100))
for n,r in enumerate(PEND,1):
    H("[P%02d] %s — v2 pág. %d — %d %% IA"%(n,section(r["i"])[:70],r["page"],r["pct"]),2)
    mejor=min([t for t in V if r[t]],key=lambda t:r[t]["pct"],default=None)
    if mejor:
        doc.add_paragraph("Mínimo alcanzado en las otras versiones: %s con %d %% (similitud %.2f)."%(
            LBL[mejor],r[mejor]["pct"],r[mejor]["sim"]))
    marked_para(D["v2"][r["i"]]["marked"])
doc.save("Sustituciones_v2_humanizadas.docx")
print("sustituciones:",len(SUB)," pendientes:",len(PEND))
json.dump({"sub":[[r["i"],c,k] for r,c,k in SUB],"pend":[r["i"] for r in PEND]},open("final.json","w"))
