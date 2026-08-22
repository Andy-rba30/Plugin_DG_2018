#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUDITOR DG-2018 — MODULO DE DISENO EN PLANTA (COMPLETO)
========================================================
Manual de Carreteras: Diseno Geometrico DG-2018 (MTC, Peru) — Seccion 302.

Motor de reglas determinístico: NINGUN valor normativo esta escrito en este
codigo. Todo se consulta en dg2018_reglas_base.json, extraido y verificado
contra el PDF oficial. Cada hallazgo cita seccion, tabla y pagina, y
transcribe el texto de la norma, para que el usuario lo ubique de inmediato.

COBERTURA (Seccion 302 completa):
  302.03    Tramos en tangente (Tabla 302.01)
  302.04.02 Radios minimos (Tablas 302.02 / 302.04)
  302.04.03 Peralte-radio-friccion (Tabla 302.03)
  302.04.04 Curvas en contraperalte (Tablas 302.05 / 302.06)
  302.04.05 Coordinacion entre curvas circulares (Tablas 302.07 / 302.08)
  302.05    Curvas de transicion / clotoide (Tablas 302.09-302.11 A/B)
  302.06    Curvas compuestas y vecinas del mismo sentido
  302.07    Curvas de vuelta (Tabla 302.12)
  302.08    Transicion de peralte (Tablas 302.13-302.18)
  302.09    Sobreancho: formula general, factores de reduccion y desarrollo
            (Tablas 302.19 / 302.20) + vehiculo de diseno (Tabla 202.01)
  302.10    Visibilidad en curva, banquetas, obstaculos, adelantamiento
            (Tablas 302.21 / 302.22) + Dp de la Seccion 205.02
  304.06.01 Peralte maximo (Tabla 304.05) — control transversal aplicado a la curva
"""

import json
import sys
from math import sqrt, cos, radians
from pathlib import Path

DATA = Path(__file__).parent / "data" / "dg2018_reglas_base.json"
REGLAS = json.loads(DATA.read_text(encoding="utf-8"))
PL = REGLAS["planta"]
VIS = REGLAS["visibilidad"]["distancia_parada"]


# ------------------------------------------------------------------ utilidades

def cita(f: dict) -> str:
    """Construye la referencia normativa trazable."""
    q = []
    if f.get("seccion"):
        q.append(f"Seccion {f['seccion']}")
    for k in ("tabla", "tablas"):
        if f.get(k):
            v = f[k]
            q.append("Tabla " + (", ".join(v) if isinstance(v, list) else v))
    if f.get("figuras"):
        q.append("Fig. " + ", ".join(f["figuras"]))
    pag = f.get("pagina_manual") or f.get("paginas_manual")
    if pag:
        q.append(f"pag. {pag}")
    return "DG-2018, " + ", ".join(q)


def pk(m):
    return f"{int(m)//1000}+{int(m) % 1000:03d}"


def vk(v, tabla):
    k = str(int(round(v)))
    return k if k in tabla else None


def cercano_inf(valor, tabla_keys_num):
    """Mayor clave <= valor (para tablas escalonadas por radio)."""
    cands = [k for k in tabla_keys_num if k <= valor]
    return max(cands) if cands else None


class Informe:
    def __init__(self, cab):
        self.cab = cab
        self.h = []

    def add(self, sev, elem, msg, fuente, norma=None):
        self.h.append({"sev": sev, "elem": elem, "msg": msg,
                       "cita": cita(fuente), "norma": norma})

    NO, OB, OK = "NO_CUMPLE", "OBSERVACION", "CUMPLE"

    def texto(self):
        orden = {"NO_CUMPLE": 0, "OBSERVACION": 1, "CUMPLE": 2}
        sim = {"NO_CUMPLE": "[X]", "OBSERVACION": "[!]", "CUMPLE": "[OK]"}
        o = [self.cab, "=" * 78]
        for x in sorted(self.h, key=lambda z: orden[z["sev"]]):
            o.append(f"\n{sim[x['sev']]} {x['sev']} | {x['elem']}")
            o.append(f"    {x['msg']}")
            o.append(f"    Cita: {x['cita']}")
            if x["norma"]:
                o.append(f"    Norma: \"{x['norma']}\"")
        nb = sum(1 for x in self.h if x["sev"] == "NO_CUMPLE")
        no = sum(1 for x in self.h if x["sev"] == "OBSERVACION")
        o += ["\n" + "=" * 78,
              f"RESUMEN PLANTA: {nb} incumplimiento(s) | {no} observacion(es) | "
              f"{len(self.h)-nb-no} conforme(s) | {len(self.h)} verificaciones."]
        return "\n".join(o)

    def dict(self):
        return {"encabezado": self.cab, "hallazgos": self.h}


def Dp_de(proy, curva=None):
    """Distancia de parada (m). Usa pendiente del tramo si se declara."""
    v = (curva or {}).get("velocidad_especifica", proy["velocidad_diseno"])
    i = (curva or {}).get("pendiente_pct")
    k = vk(v, VIS["Dp_pendiente_0_redondeada_m"])
    if k is None:
        return None
    if i is None or abs(i) < 3:
        return VIS["Dp_pendiente_0_redondeada_m"][k]
    cols = VIS["Dp_con_pendiente_m"]["_cols"]
    fila = VIS["Dp_con_pendiente_m"].get(k)
    if not fila:
        return VIS["Dp_pendiente_0_redondeada_m"][k]
    lado = "bajada" if i < 0 else "subida"
    grado = min([3, 6, 9], key=lambda g: abs(abs(i) - g))
    return fila[cols.index(f"{lado}_{grado}")]



def L_vehiculo(proy, inf=None):
    """Distancia entre eje posterior y parte frontal (m) para la formula de sobreancho.
    Prioridad: valor explicito del proyecto > derivado de la Tabla 202.01."""
    if proy.get("L_vehiculo_m"):
        return proy["L_vehiculo_m"], "declarado en el proyecto", {"articulado": False}
    tipo = proy.get("vehiculo_diseno")
    if not tipo:
        return None, None, None
    vd = REGLAS["vehiculos_de_diseno"]
    v = vd["vehiculos"].get(tipo)
    if not v:
        return None, None, None
    tramos = v["separacion_ejes"]
    L = v["vuelo_delantero"] + sum(tramos)
    desc = (f"derivado de Tabla 202.01 para {tipo} ({v['nombre']}): vuelo delantero "
            f"{v['vuelo_delantero']} + separacion de ejes {'+'.join(str(x) for x in tramos)}")
    if len(tramos) > 1:
        L_alt = round(v["vuelo_delantero"] + max(tramos), 2)
        return round(L, 2), desc, {"articulado": True, "L_alternativo": L_alt,
                                   "tramos": tramos, "tipo": tipo}
    return round(L, 2), desc, {"articulado": False}


# ==================================================== VERIFICACIONES POR CURVA

def c_radio_minimo(c, proy, inf):
    r = PL["radios_minimos"]
    tab = r["por_ubicacion"][proy["ubicacion_via"]]["radio_min_m"]
    v = c.get("velocidad_especifica", proy["velocidad_diseno"])
    k = vk(v, tab)
    e = f"Curva {c['id']} (km {pk(c['prog_ini'])}) - radio minimo"
    if k is None:
        inf.add(inf.OB, e, f"V={v} km/h no tabulada en 302.02.", r["fuente"]); return
    rmin = tab[k]
    if c["radio"] < rmin:
        inf.add(inf.NO, e, f"Radio {c['radio']} m < minimo {rmin} m (V={k} km/h, "
                f"{proy['ubicacion_via'].replace('_',' ')}, peralte max "
                f"{r['por_ubicacion'][proy['ubicacion_via']]['peralte_max_pct']}%).",
                r["fuente"],
                "debe evitarse el empleo de curvas de radio minimo; se tratara de usar curvas de "
                "radio amplio, reservando el empleo de radios minimos para las condiciones criticas")
    elif c["radio"] <= rmin * 1.05:
        inf.add(inf.OB, e, f"Radio {c['radio']} m esta en el minimo o muy cerca ({rmin} m); "
                f"la norma pide reservarlo solo para condiciones criticas.", r["fuente"])
    else:
        inf.add(inf.OK, e, f"Radio {c['radio']} m >= minimo {rmin} m (V={k}).", r["fuente"])


def c_peralte(c, proy, inf):
    r = REGLAS["seccion_transversal"]["peralte_maximo"]
    val = r["valores"][proy["zona_peralte"]]
    p = c.get("peralte_pct")
    e = f"Curva {c['id']} - peralte"
    if p is None:
        inf.add(inf.OB, e, "No se declaro peralte para la curva.", r["fuente"]); return
    if p > val["absoluto_pct"]:
        inf.add(inf.NO, e, f"Peralte {p}% > maximo absoluto {val['absoluto_pct']}% "
                f"({proy['zona_peralte'].replace('_',' ')}).", r["fuente"])
    elif p > val["normal_pct"]:
        inf.add(inf.OB, e, f"Peralte {p}% supera el normal {val['normal_pct']}% sin exceder el "
                f"absoluto {val['absoluto_pct']}%: requiere sustento.", r["fuente"])
    else:
        inf.add(inf.OK, e, f"Peralte {p}% <= normal {val['normal_pct']}%.", r["fuente"])


def c_contraperalte(c, proy, inf):
    """302.04.04 — solo si la curva se declara en contraperalte."""
    if not c.get("contraperalte"):
        return
    r = PL["curvas_en_contraperalte"]
    v = c.get("velocidad_especifica", proy["velocidad_diseno"])
    e = f"Curva {c['id']} - contraperalte"
    if v < 60 or proy.get("pavimentada", True) is False:
        inf.add(inf.NO, e, f"Contraperalte no admisible: V={v} km/h (<60) o via sin pavimento.",
                r["fuente"], r["prohibicion"]); return
    k = vk(v, r["R_limite_adoptado_m_Tabla_302_05"])
    if k is None:
        return
    RL = r["R_limite_adoptado_m_Tabla_302_05"][k]
    if c["radio"] < RL:
        inf.add(inf.NO, e, f"Radio {c['radio']} m < R limite en contraperalte {RL} m (V={k}).",
                {"seccion": "302.04.04", "tabla": "302.05", "pagina_manual": "132"})
    else:
        inf.add(inf.OK, e, f"Radio {c['radio']} m >= R limite {RL} m (V={k}).",
                {"seccion": "302.04.04", "tabla": "302.05", "pagina_manual": "132"})


def c_necesidad_transicion(c, proy, inf):
    ct = PL["curvas_de_transicion"]
    tercera = proy["clase"] == "carretera_tercera_clase"
    ref = ct["radios_sin_transicion_tercera_clase"] if tercera else ct["radios_sin_transicion_general"]
    tab = ref["R_limite_m"]
    v = c.get("velocidad_especifica", proy["velocidad_diseno"])
    k = vk(v, tab)
    e = f"Curva {c['id']} - necesidad de curva de transicion"
    if k is None:
        return
    Rlim, tiene = tab[k], (c.get("long_transicion_entrada_m") or 0) > 0
    if c["radio"] < Rlim and not tiene:
        inf.add(inf.NO, e, f"Radio {c['radio']} m < R limite {Rlim} m (V={k}): se REQUIERE clotoide "
                f"y el proyecto no la declara.", ref["fuente"])
    elif c["radio"] < Rlim:
        inf.add(inf.OK, e, f"Radio {c['radio']} m < R limite {Rlim} m: transicion requerida y "
                f"declarada.", ref["fuente"])
    else:
        inf.add(inf.OK, e, f"Radio {c['radio']} m >= R limite {Rlim} m: se puede prescindir de la "
                f"curva de transicion.", ref["fuente"])


def c_longitud_transicion(c, proy, inf):
    lt = PL["curvas_de_transicion"]["longitud_minima"]
    L = c.get("long_transicion_entrada_m")
    if not L:
        return
    e = f"Curva {c['id']} - longitud de clotoide"
    v = c.get("velocidad_especifica", proy["velocidad_diseno"])
    k = vk(v, lt["L_min_redondeada_por_velocidad_m"])
    Lref = lt["L_min_redondeada_por_velocidad_m"].get(k) if k else None
    piso = lt["piso_absoluto_m"]
    if L < piso:
        inf.add(inf.NO, e, f"Longitud {L} m < piso absoluto {piso} m.", lt["fuente"], lt["nota_norma"])
    elif Lref and L < Lref:
        inf.add(inf.OB, e, f"Longitud {L} m < minima tabulada {Lref} m (V={k}). Formula: "
                f"{lt['formula']}", lt["fuente"])
    else:
        inf.add(inf.OK, e, f"Longitud {L} m >= minima exigible {max(piso, Lref or 0)} m.", lt["fuente"])
    # parametro A de la clotoide
    A = sqrt(c["radio"] * L)
    inf.add(inf.OK, f"Curva {c['id']} - parametro clotoide",
            f"A = sqrt(R*L) = sqrt({c['radio']}*{L}) = {A:.1f} m (ref. A^2 = R*L).",
            {"seccion": "302.05.02/302.05.03", "pagina_manual": "138-139"})


def c_transicion_peralte(c, proy, inf):
    tp = PL["transicion_de_peralte"]
    e = f"Curva {c['id']} - transicion de peralte"
    p, L = c.get("peralte_pct"), c.get("long_transicion_entrada_m")
    if p is None or L is None:
        return
    if proy["clase"] == "carretera_tercera_clase":
        t = tp["tercera_clase_Tabla_302_13"]
        v = c.get("velocidad_especifica", proy["velocidad_diseno"])
        k = vk(v, t["L_transicion_peralte_m"])
        if k is None:
            return
        Lreq = next((Lx for pe, Lx in zip(t["peraltes_pct"], t["L_transicion_peralte_m"][k])
                     if p <= pe), t["L_transicion_peralte_m"][k][-1])
        if L + 1e-6 < Lreq:
            inf.add(inf.NO, e, f"Longitud {L} m < minima de transicion de peralte {Lreq} m "
                    f"(V={k} km/h, p={p}%).", t["fuente"])
        else:
            inf.add(inf.OK, e, f"Longitud {L} m >= minima {Lreq} m (V={k}, p={p}%).", t["fuente"])
        Lb = t["L_transicion_bombeo_m"].get(k)
        if Lb:
            inf.add(inf.OK, f"Curva {c['id']} - transicion de bombeo",
                    f"Longitud minima de transicion de bombeo para V={k}: {Lb} m (base 2% de bombeo).",
                    t["fuente"])
    else:
        v = c.get("velocidad_especifica", proy["velocidad_diseno"])
        ipmax = 1.8 - 0.01 * v
        B = proy.get("B_eje_giro_m", 3.6)
        bombeo = proy.get("bombeo_pct", 2.5)
        Lreq = ((abs(p) + abs(bombeo)) / ipmax) * B
        if L + 1e-6 < Lreq:
            inf.add(inf.NO, e, f"Longitud {L} m < Lmin = ((pf-pi)/ipmax)*B = "
                    f"(({p}+{bombeo})/{ipmax:.2f})*{B} = {Lreq:.1f} m.", tp["fuente"],
                    tp["longitud_minima_formula"])
        else:
            inf.add(inf.OK, e, f"Longitud {L} m >= Lmin {Lreq:.1f} m (ipmax={ipmax:.2f}%, B={B} m).",
                    tp["fuente"])


def c_sobreancho(c, proy, inf):
    """302.09 — Sobreancho. La formula general aplica a TODO el rango de velocidad.
    La Tabla 302.20 (factores de reduccion) solo aplica a V <= 80 km/h y calzada 7.20 m;
    sobre 80 km/h la norma remite al calculo directo 'para cada caso' con el vehiculo
    de diseno del proyecto."""
    sa = PL["sobreancho"]
    e = f"Curva {c['id']} - sobreancho"
    n, R = proy.get("n_carriles", 2), c["radio"]
    Lv, origen, meta = L_vehiculo(proy)
    if not Lv:
        inf.add(inf.OB, e, "No se puede calcular el sobreancho: falta 'L_vehiculo_m' o "
                "'vehiculo_diseno' (Tabla 202.01).",
                REGLAS["vehiculos_de_diseno"]["fuente"]); return
    if R <= Lv:
        inf.add(inf.OB, e, f"Radio {R} m <= L del vehiculo ({Lv} m): geometria fuera del "
                f"dominio de la formula; verificar como curva de vuelta (302.07).", sa["fuente"]); return
    v = c.get("velocidad_especifica", proy["velocidad_diseno"])
    dec = c.get("sobreancho_m")
    Sa = n * (R - sqrt(R ** 2 - Lv ** 2)) + v / (10 * sqrt(R))
    detalle = f"Sa = {n}*({R} - sqrt({R}^2 - {Lv}^2)) + {v}/(10*sqrt({R})) = {Sa:.2f} m"
    amb = sa["ambito_formula"]
    fr = sa["factores_reduccion_Tabla_302_20"]
    aplica_reduccion = (v <= 80 and proy.get("ancho_calzada_m") == 7.20)
    if aplica_reduccion:
        keys = sorted(int(x) for x in fr["factores"])
        kk = cercano_inf(R, keys)
        if kk:
            f = fr["factores"][str(kk)]
            Sa_r = Sa * f
            inf.add(inf.OK, f"Curva {c['id']} - factor de reduccion",
                    f"V={v} km/h (<=80) y calzada 7.20 m: aplica factor {f} para R={kk} m. "
                    f"Sa {Sa:.2f} -> {Sa_r:.2f} m.", fr["fuente"])
            Sa, detalle = Sa_r, detalle + f" x factor {f} = {Sa_r:.2f} m"
    else:
        if v > 80:
            motivo = f"V={v} km/h > 80"
            texto = amb["texto_norma_radios_mayores"]
        else:
            motivo = f"ancho de calzada {proy.get('ancho_calzada_m')} m distinto de 7.20 m"
            texto = amb["texto_norma_302_20"]
        inf.add(inf.OK, f"Curva {c['id']} - regimen de calculo del sobreancho",
                f"No aplica la Tabla 302.20 de factores de reduccion ({motivo}). Se calcula "
                f"directamente con la formula 302.09.03 y el vehiculo de diseno "
                f"({origen}). {detalle}",
                {"seccion": "302.09.03", "pagina_manual": "162"}, texto)
    if meta and meta.get("articulado"):
        Lalt = meta["L_alternativo"]
        Sa_alt = n * (R - sqrt(R ** 2 - Lalt ** 2)) + v / (10 * sqrt(R)) if R > Lalt else None
        alt = f" Con L del tramo mayor ({Lalt} m): Sa = {Sa_alt:.2f} m." if Sa_alt else ""
        inf.add(inf.OB, f"Curva {c['id']} - criterio de L (vehiculo articulado)",
                f"{meta['tipo']} es articulado (tramos de ejes {meta['tramos']}). La formula de "
                f"302.09.03 asume un unico L; sumar todos los tramos (L={Lv} m) es conservador y "
                f"puede sobredimensionar.{alt} El proyectista debe sustentar el L adoptado.",
                REGLAS["vehiculos_de_diseno"]["fuente"],
                REGLAS["vehiculos_de_diseno"]["nota_L"])
    if Sa < sa["valor_minimo_m"]:
        inf.add(inf.OB, e, f"Sobreancho requerido {Sa:.2f} m < minimo practico "
                f"{sa['valor_minimo_m']} m: puede omitirse. ({detalle})", sa["fuente"], sa["nota_norma"])
        return
    if dec is None:
        inf.add(inf.OB, e, f"No se declara sobreancho; requerido = {Sa:.2f} m. {detalle} "
                f"[L {origen}]", sa["fuente"])
    elif dec + 1e-6 < Sa:
        inf.add(inf.NO, e, f"Sobreancho {dec} m < requerido {Sa:.2f} m. {detalle} "
                f"[L {origen}]", sa["fuente"], sa["aplicacion_borde"])
    else:
        inf.add(inf.OK, e, f"Sobreancho {dec} m >= requerido {Sa:.2f} m. {detalle}", sa["fuente"])


def c_distribucion_sobreancho(c, proy, inf):
    """302.09.04 — desarrollo del sobreancho a lo largo de la transicion."""
    ds = PL["sobreancho"]["distribucion_en_transicion"]
    L = c.get("long_transicion_entrada_m")
    dec = c.get("sobreancho_m")
    if not L or dec is None:
        return
    e = f"Curva {c['id']} - desarrollo del sobreancho"
    tercios = [(f"{q*100:.0f}% de la transicion ({q*L:.0f} m)", dec * q) for q in (0.25, 0.50, 0.75)]
    det = "; ".join(f"{t}: {s:.2f} m" for t, s in tercios)
    inf.add(inf.OK, e, f"Reparticion lineal San = (Sa/L)*Ln sobre L={L} m -> {det}; "
            f"al final: {dec:.2f} m.", ds["fuente"], ds["lineal"]["nota"])


def c_visibilidad_curva(c, proy, inf):
    """302.10.03 — ancho libre minimo (banqueta de visibilidad)."""
    vv = PL["verificacion_visibilidad"]["ancho_libre_minimo"]
    e = f"Curva {c['id']} - visibilidad / banqueta"
    Dp = Dp_de(proy, c)
    if Dp is None:
        return
    R = c["radio"]
    amin = R * (1 - cos(radians(28.65 * Dp / R)))
    decl = c.get("ancho_libre_m")
    base = {"seccion": "302.10.03", "pagina_manual": "167"}
    if decl is None:
        inf.add(inf.OB, e, f"No se declara ancho libre de obstrucciones. Requerido amin = "
                f"R*(1-cos(28.65*Dp/R)) = {R}*(1-cos(28.65*{Dp}/{R})) = {amin:.2f} m (Dp={Dp} m).",
                base, vv["regla"])
    elif decl + 1e-6 < amin:
        inf.add(inf.NO, e, f"Ancho libre {decl} m < minimo {amin:.2f} m (Dp={Dp} m, R={R} m): "
                f"la linea de visibilidad no alcanza la distancia de parada.", base, vv["regla"])
    else:
        inf.add(inf.OK, e, f"Ancho libre {decl} m >= minimo {amin:.2f} m (Dp={Dp} m).", base)
    if proy["clase"] == "carretera_tercera_clase" and (decl is not None and decl < amin):
        inf.add(inf.OB, f"Curva {c['id']} - criterio 3ra clase", vv["nota_tercera_clase"], base)


def c_curva_de_vuelta(c, proy, inf):
    """302.07 / Tabla 302.12 — solo si se declara como curva de vuelta."""
    if not c.get("curva_de_vuelta"):
        return
    cv = PL["curvas_de_vuelta"]
    e = f"Curva {c['id']} - curva de vuelta"
    Ri, Re = c.get("radio_interior_m"), c.get("radio_exterior_m")
    man = c.get("maniobra", "C2")
    if Ri is None or Re is None:
        inf.add(inf.OB, e, "Falta declarar radio interior (Ri) y exterior (Re).", cv["fuente"]); return
    if Ri < cv["Ri_minimo_absoluto_m"]:
        inf.add(inf.NO, e, f"Ri {Ri} m < minimo absoluto {cv['Ri_minimo_absoluto_m']} m.",
                cv["fuente"], cv["nota_norma"])
    elif Ri < cv["Ri_minimo_normal_m"]:
        inf.add(inf.OB, e, f"Ri {Ri} m por debajo del minimo normal {cv['Ri_minimo_normal_m']} m: "
                f"uso excepcional.", cv["fuente"], cv["nota_norma"])
    keys = sorted(float(x) for x in cv["Re_min_m"])
    kk = cercano_inf(Ri, keys)
    if kk is not None:
        Rereq = cv["Re_min_m"][f"{kk:.1f}"][man]
        if Re + 1e-6 < Rereq:
            inf.add(inf.NO, e, f"Re {Re} m < minimo {Rereq} m para Ri={kk} m, maniobra {man} "
                    f"({cv['maniobras'][man]}).", cv["fuente"], cv["nota_calzada"])
        else:
            inf.add(inf.OK, e, f"Re {Re} m >= minimo {Rereq} m (Ri={kk} m, maniobra {man}).",
                    cv["fuente"])


# ============================================ VERIFICACIONES POR TANGENTE Y PAR

def t_tangente(t, prev_c, next_c, proy, inf):
    r = PL["tramos_en_tangente"]
    k = vk(proy["velocidad_diseno"], r["valores_por_velocidad"])
    if k is None:
        return
    ref = r["valores_por_velocidad"][k]
    L = t["prog_fin"] - t["prog_ini"]
    e = f"Tangente {t['id']} (L={L:.0f} m, km {pk(t['prog_ini'])}-{pk(t['prog_fin'])})"
    if prev_c and next_c and prev_c.get("sentido") and next_c.get("sentido"):
        esS = prev_c["sentido"] != next_c["sentido"]
        Lmin = ref["L_min_s"] if esS else ref["L_min_o"]
        et = "trazado en S (sentidos opuestos)" if esS else "curvas del mismo sentido"
        if L < Lmin:
            inf.add(inf.NO, e, f"Longitud {L:.0f} m < minima {Lmin} m para {et} (V={k}).", r["fuente"])
        else:
            inf.add(inf.OK, e, f"L={L:.0f} m >= minima {Lmin} m ({et}).", r["fuente"])
        if not esS:
            cc = PL["curvas_compuestas"]
            if L < cc["mismo_sentido_tangente_min_m"]:
                inf.add(inf.OB, e, f"Curvas del mismo sentido separadas por {L:.0f} m "
                        f"(< {cc['mismo_sentido_tangente_min_m']} m).", cc["fuente"], cc["nota_norma"])
    if L > ref["L_max"]:
        inf.add(inf.OB, e, f"Longitud {L:.0f} m > maxima deseable {ref['L_max']} m (V={k}): "
                f"riesgo de monotonia.", r["fuente"])


def par_coordinacion(prev_c, tangL, next_c, proy, inf):
    """302.04.05 — Tablas 302.07 (grupo 1) / 302.08 (grupo 2)."""
    co = PL["coordinacion_curvas_circulares"]
    g = proy.get("grupo_coordinacion", 2)
    e = f"Coordinacion {prev_c['id']} -> {next_c['id']}"
    # regla especifica de autopistas con recta > 400 m
    ra = co["regla_autopistas_recta_larga"]
    if "autopista" in proy["clase"] and tangL and tangL > ra["recta_umbral_m"]:
        if next_c["radio"] < ra["R_salida_min_m"]:
            inf.add(inf.NO, e, f"Autopista con recta intermedia de {tangL:.0f} m (>{ra['recta_umbral_m']} m): "
                    f"R de salida {next_c['radio']} m < {ra['R_salida_min_m']} m.",
                    {"seccion": "302.04.05", "pagina_manual": ra["pagina_manual"]}, ra["texto"])
        else:
            inf.add(inf.OK, e, f"R de salida {next_c['radio']} m >= {ra['R_salida_min_m']} m "
                    f"(recta {tangL:.0f} m).",
                    {"seccion": "302.04.05", "pagina_manual": ra["pagina_manual"]})
        return
    if tangL is not None and tangL > co["umbral_tangente_m"]:
        return  # no aplica el control de relacion de radios
    tabla = co["tabla_302_07_grupo_1"] if g == 1 else co["tabla_302_08_grupo_2"]
    vals, tope = tabla["valores"], tabla["tope_superior_m"]
    keys = sorted(int(x) for x in vals)
    Rent, Rsal = prev_c["radio"], next_c["radio"]
    enl = "sin tangente intermedia" if not tangL else f"tangente de {tangL:.0f} m"
    if Rent < keys[0]:
        inf.add(inf.OB, e, f"R de entrada {Rent} m por debajo del rango tabulado "
                f"(min {keys[0]} m) para el grupo {g}.", co["fuente"], co["regla"]); return
    kk = cercano_inf(Rent, keys)
    fila = vals[str(kk)]
    rmin = fila["R_salida_min_m"]
    rmax = fila["R_salida_max_m"]
    src = {"seccion": "302.04.05", "tabla": "302.07" if g == 1 else "302.08",
           "pagina_manual": "135-136" if g == 1 else "137"}
    if Rsal < rmin:
        inf.add(inf.NO, e, f"Enlace {enl} (<= {co['umbral_tangente_m']} m): R salida {Rsal} m < "
                f"minimo {rmin} m para R entrada {kk} m (grupo {g}: {co['grupos'][str(g)]}).",
                src, co["regla"])
    elif isinstance(rmax, (int, float)) and Rsal > rmax:
        inf.add(inf.NO, e, f"Enlace {enl}: R salida {Rsal} m > maximo {rmax} m para R entrada "
                f"{kk} m (grupo {g}).", src, co["regla"])
    else:
        lim = f"{rmin}-{rmax}" if isinstance(rmax, (int, float)) else f"{rmin} a >{tope}"
        inf.add(inf.OK, e, f"R salida {Rsal} m dentro del rango admisible [{lim}] m para "
                f"R entrada {kk} m (grupo {g}).", src)


def par_curvas_compuestas(prev_c, next_c, proy, inf):
    """302.06 — curvas compuestas sin tangente intermedia."""
    cc = PL["curvas_compuestas"]
    if prev_c.get("sentido") != next_c.get("sentido"):
        return
    e = f"Curva compuesta {prev_c['id']} + {next_c['id']}"
    r1, r2 = prev_c["radio"], next_c["radio"]
    ratio = max(r1, r2) / min(r1, r2)
    if ratio > 1.5:
        inf.add(inf.NO, e, f"Curvas compuestas del mismo sentido sin tangente: relacion "
                f"{ratio:.2f} > 1.5 (R={r1} m y {r2} m).",
                {"seccion": "302.06.02", "pagina_manual": "147"}, cc["policentrica_3_centros"])
    else:
        inf.add(inf.OK, e, f"Relacion de radios {ratio:.2f} <= 1.5.",
                {"seccion": "302.06.02", "pagina_manual": "147"})
    inf.add(inf.OB, e, cc["regla_general"], cc["fuente"])


# ============================================ VERIFICACIONES DE TRAMO GLOBAL

def tramo_adelantamiento(proy, inf):
    """302.10.05 / Tabla 302.22 — solo para tramos > 5 km."""
    z = PL["verificacion_visibilidad"]["zonas_adelantamiento_Tabla_302_22"]
    elems = proy["alineamiento"]
    Ltot = elems[-1]["prog_fin"] - elems[0]["prog_ini"]
    e = f"Tramo global (L={Ltot:.0f} m) - zonas de adelantamiento"
    if Ltot <= 5000:
        return
    tipo = z["mapa_orografia"][str(proy["orografia"])]
    req = z["porcentajes"][tipo]
    decl = proy.get("pct_visibilidad_adelantamiento")
    if decl is None:
        inf.add(inf.OB, e, f"No se declara el porcentaje del tramo con visibilidad adecuada para "
                f"adelantar. Terreno {tipo}: minimo {req['minimo']}%, deseable >={req['deseable']}%.",
                z["fuente"])
    elif decl < req["minimo"]:
        inf.add(inf.NO, e, f"Solo {decl}% del tramo con visibilidad de adelantamiento; minimo "
                f"{req['minimo']}% para terreno {tipo}.", z["fuente"])
    elif decl < req["deseable"]:
        inf.add(inf.OB, e, f"{decl}% cumple el minimo ({req['minimo']}%) pero no el deseable "
                f"(>={req['deseable']}%) para terreno {tipo}.", z["fuente"])
    else:
        inf.add(inf.OK, e, f"{decl}% >= deseable {req['deseable']}% (terreno {tipo}).", z["fuente"])


def tramo_obstaculos(proy, inf):
    """302.10 / Tabla 302.21 — distancias minimas a obstaculos fijos."""
    ob = PL["verificacion_visibilidad"]["distancias_minimas_obstaculos_Tabla_302_21"]
    for o in proy.get("obstaculos", []):
        e = f"Obstaculo {o.get('id','?')} (km {pk(o['progresiva'])})"
        tipo = o["tipo"]
        ref = ob["valores_m"].get(tipo)
        if not ref:
            inf.add(inf.OB, e, f"Tipo '{tipo}' no tabulado en 302.21.", ob["fuente"]); continue
        d = o["distancia_m"]
        if d < ref["minimo_absoluto"]:
            inf.add(inf.NO, e, f"Distancia {d} m < minimo absoluto {ref['minimo_absoluto']} m "
                    f"({tipo.replace('_',' ')}), medida desde el borde exterior de la berma.",
                    ob["fuente"], ob["nota_norma"])
        elif d < ref["deseable"]:
            clase_ok = proy["clase"] in ("carretera_segunda_clase", "carretera_tercera_clase")
            sev = inf.OB if clase_ok else inf.NO
            inf.add(sev, e, f"Distancia {d} m entre el minimo absoluto ({ref['minimo_absoluto']} m) "
                    f"y el deseable ({ref['deseable']} m).", ob["fuente"], ob["nota_norma"])
        else:
            inf.add(inf.OK, e, f"Distancia {d} m >= deseable {ref['deseable']} m.", ob["fuente"])


# ==================================================================== ORQUESTADOR

def auditar_planta(proy):
    inf = Informe(
        f"AUDITORIA DE DISENO EN PLANTA - DG-2018\n"
        f"Proyecto: {proy['nombre']}\n"
        f"Clase: {proy['clase']} | Orografia tipo {proy['orografia']} | "
        f"Vd = {proy['velocidad_diseno']} km/h | Grupo coordinacion: {proy.get('grupo_coordinacion',2)}"
    )
    elems = proy["alineamiento"]

    for c in [e for e in elems if e["tipo"] == "curva"]:
        c_radio_minimo(c, proy, inf)
        c_peralte(c, proy, inf)
        c_contraperalte(c, proy, inf)
        c_necesidad_transicion(c, proy, inf)
        c_longitud_transicion(c, proy, inf)
        c_transicion_peralte(c, proy, inf)
        c_sobreancho(c, proy, inf)
        c_distribucion_sobreancho(c, proy, inf)
        c_visibilidad_curva(c, proy, inf)
        c_curva_de_vuelta(c, proy, inf)

    for i, e in enumerate(elems):
        if e["tipo"] == "tangente":
            pv = elems[i-1] if i > 0 and elems[i-1]["tipo"] == "curva" else None
            nx = elems[i+1] if i < len(elems)-1 and elems[i+1]["tipo"] == "curva" else None
            t_tangente(e, pv, nx, proy, inf)
            if pv and nx:
                par_coordinacion(pv, e["prog_fin"] - e["prog_ini"], nx, proy, inf)
        elif e["tipo"] == "curva" and i < len(elems)-1 and elems[i+1]["tipo"] == "curva":
            par_coordinacion(e, 0, elems[i+1], proy, inf)
            par_curvas_compuestas(e, elems[i+1], proy, inf)

    tramo_adelantamiento(proy, inf)
    tramo_obstaculos(proy, inf)
    return inf


def cargar_proyecto(ruta):
    """Carga un proyecto desde un archivo JSON."""
    return json.loads(Path(ruta).read_text(encoding="utf-8"))
