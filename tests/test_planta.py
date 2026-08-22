# -*- coding: utf-8 -*-
"""
Tests del modulo de planta.

Estos tests cumplen dos funciones:
  1. Verificar que el motor de reglas se comporta como se espera.
  2. Servir de control de integridad de los datos normativos: si alguien edita
     dg2018_reglas_base.json y altera un valor de la norma por error, estos
     tests fallan. Los valores esperados provienen del PDF oficial del DG-2018.
"""

import json
from pathlib import Path

import pytest

from auditor_dg2018 import REGLAS, auditar_planta

EJEMPLOS = Path(__file__).resolve().parents[1] / "examples"


def sev_de(informe, fragmento):
    """Devuelve las severidades de los hallazgos cuyo elemento contiene el fragmento."""
    return [h["sev"] for h in informe.h if fragmento.lower() in h["elem"].lower()]


def base_proyecto(**over):
    p = {
        "nombre": "test", "clase": "carretera_tercera_clase", "grupo_coordinacion": 2,
        "orografia": 3, "velocidad_diseno": 40,
        "ubicacion_via": "area_rural_accidentada_o_escarpada",
        "zona_peralte": "zona_rural_accidentado_o_escarpado",
        "n_carriles": 2, "ancho_calzada_m": 6.00, "B_eje_giro_m": 3.0,
        "bombeo_pct": 2.5, "L_vehiculo_m": 12.3, "pavimentada": True,
        "alineamiento": [],
    }
    p.update(over)
    return p


def curva(**over):
    c = {"tipo": "curva", "id": "C-1", "prog_ini": 100, "prog_fin": 200, "radio": 100,
         "velocidad_especifica": 40, "sentido": "D", "peralte_pct": 6.0}
    c.update(over)
    return c


# ------------------------------------------------------- integridad de los datos

class TestDatosNormativos:
    """Valores tomados directamente del manual; si cambian, algo se corrompio."""

    def test_radio_minimo_40kmh_rural_accidentada(self):
        # Tabla 302.02, pag. 129: V=40, peralte max 12% -> R min 45 m
        t = REGLAS["planta"]["radios_minimos"]["por_ubicacion"]
        assert t["area_rural_accidentada_o_escarpada"]["radio_min_m"]["40"] == 45
        assert t["area_rural_accidentada_o_escarpada"]["peralte_max_pct"] == 12.0

    def test_radio_minimo_urbana_30kmh(self):
        # Tabla 302.02, pag. 128: area urbana, V=30 -> 35 m
        t = REGLAS["planta"]["radios_minimos"]["por_ubicacion"]["area_urbana"]
        assert t["radio_min_m"]["30"] == 35
        assert t["peralte_max_pct"] == 4.0

    def test_tangente_minima_40kmh(self):
        # Tabla 302.01, pag. 127: V=40 -> S=56, O=111, max=668
        t = REGLAS["planta"]["tramos_en_tangente"]["valores_por_velocidad"]["40"]
        assert (t["L_min_s"], t["L_min_o"], t["L_max"]) == (56, 111, 668)

    def test_piso_absoluto_clotoide(self):
        # Tabla 302.10, nota: nunca menos de 30 m
        assert REGLAS["planta"]["curvas_de_transicion"]["longitud_minima"]["piso_absoluto_m"] == 30

    def test_peralte_maximo_rural_escarpado(self):
        # Tabla 304.05, pag. 196
        v = REGLAS["seccion_transversal"]["peralte_maximo"]["valores"]
        assert v["zona_rural_accidentado_o_escarpado"]["absoluto_pct"] == 12.0
        assert v["zona_rural_accidentado_o_escarpado"]["normal_pct"] == 8.0

    def test_coordinacion_grupo2_r500(self):
        # Tabla 302.08, pag. 137: R entrada 500 -> R salida min 259
        t = REGLAS["planta"]["coordinacion_curvas_circulares"]["tabla_302_08_grupo_2"]
        assert t["valores"]["500"]["R_salida_min_m"] == 259

    def test_vehiculo_ligero_dimensiones(self):
        # Tabla 202.01, pag. 27 - verificada visualmente (la extraccion de texto
        # plano daba 15.80/17.30 por ruido de columna; los valores reales son estos)
        vl = REGLAS["vehiculos_de_diseno"]["vehiculos"]["VL"]
        assert vl["largo_total"] == 5.80
        assert vl["radio_min_rueda_ext"] == 7.30

    def test_dp_40kmh(self):
        # Tabla 205.01, pag. 104: V=40 -> Dp 50 m
        assert REGLAS["visibilidad"]["distancia_parada"]["Dp_pendiente_0_redondeada_m"]["40"] == 50

    def test_toda_regla_tiene_fuente(self):
        """Ninguna regla de planta puede existir sin su cita normativa."""
        def revisar(nodo, ruta=""):
            if isinstance(nodo, dict):
                tiene_valores = any(
                    k for k in nodo
                    if k not in ("fuente", "descripcion", "nota", "_nota", "estado"))
                if tiene_valores and "fuente" in nodo:
                    f = nodo["fuente"]
                    assert f.get("seccion") or f.get("tabla") or f.get("tablas"), \
                        f"Fuente incompleta en {ruta}"
                for k, v in nodo.items():
                    revisar(v, f"{ruta}.{k}")
        revisar(REGLAS["planta"], "planta")


# ------------------------------------------------------------- reglas de curva

class TestRadioMinimo:
    def test_radio_insuficiente_incumple(self):
        p = base_proyecto(alineamiento=[curva(radio=38)])
        assert "NO_CUMPLE" in sev_de(auditar_planta(p), "radio minimo")

    def test_radio_amplio_cumple(self):
        p = base_proyecto(alineamiento=[curva(radio=200)])
        assert sev_de(auditar_planta(p), "radio minimo") == ["CUMPLE"]

    def test_radio_justo_en_el_minimo_observa(self):
        """La norma pide reservar el radio minimo para condiciones criticas."""
        p = base_proyecto(alineamiento=[curva(radio=45)])
        assert "OBSERVACION" in sev_de(auditar_planta(p), "radio minimo")


class TestPeralte:
    def test_peralte_sobre_absoluto_incumple(self):
        p = base_proyecto(alineamiento=[curva(peralte_pct=13.0)])
        assert "NO_CUMPLE" in sev_de(auditar_planta(p), "peralte")

    def test_peralte_entre_normal_y_absoluto_observa(self):
        p = base_proyecto(alineamiento=[curva(peralte_pct=10.0)])
        assert "OBSERVACION" in sev_de(auditar_planta(p), "peralte")

    def test_peralte_normal_cumple(self):
        p = base_proyecto(alineamiento=[curva(peralte_pct=6.0)])
        assert "CUMPLE" in sev_de(auditar_planta(p), "peralte")


class TestClotoide:
    def test_transicion_bajo_piso_30m_incumple(self):
        p = base_proyecto(alineamiento=[curva(radio=60, long_transicion_entrada_m=20)])
        assert "NO_CUMPLE" in sev_de(auditar_planta(p), "longitud de clotoide")

    def test_radio_grande_puede_prescindir(self):
        p = base_proyecto(alineamiento=[curva(radio=500)])
        s = sev_de(auditar_planta(p), "necesidad de curva de transicion")
        assert s == ["CUMPLE"]

    def test_radio_pequeno_sin_transicion_incumple(self):
        p = base_proyecto(alineamiento=[curva(radio=60)])  # < 95 m limite 3ra clase
        assert "NO_CUMPLE" in sev_de(auditar_planta(p), "necesidad de curva de transicion")


class TestSobreancho:
    def test_formula_aplica_sobre_80kmh(self):
        """Regresion: la formula 302.09.03 no tiene techo de velocidad.
        Solo la Tabla 302.20 de factores de reduccion se limita a V <= 80."""
        p = base_proyecto(clase="autopista_primera_clase", grupo_coordinacion=1,
                          velocidad_diseno=100, ancho_calzada_m=7.20,
                          ubicacion_via="area_rural_plano_u_ondulada",
                          zona_peralte="zona_rural_plano_ondulado_o_accidentado",
                          vehiculo_diseno="B2", L_vehiculo_m=None,
                          alineamiento=[curva(radio=450, velocidad_especifica=100,
                                              peralte_pct=6.0, sobreancho_m=0.30)])
        inf = auditar_planta(p)
        assert "NO_CUMPLE" in sev_de(inf, "C-1 - sobreancho")
        regimen = [h for h in inf.h if "regimen de calculo" in h["elem"]]
        assert regimen and "> 80" in regimen[0]["msg"]

    def test_factor_reduccion_solo_bajo_80_y_calzada_720(self):
        p = base_proyecto(ancho_calzada_m=7.20, velocidad_diseno=60,
                          alineamiento=[curva(radio=100, velocidad_especifica=60,
                                              sobreancho_m=5.0)])
        inf = auditar_planta(p)
        assert any("factor de reduccion" in h["elem"] for h in inf.h)

    def test_L_derivado_de_tabla_202_01(self):
        p = base_proyecto(vehiculo_diseno="B2", L_vehiculo_m=None,
                          alineamiento=[curva(radio=100)])
        inf = auditar_planta(p)
        h = [x for x in inf.h if "sobreancho" in x["elem"] and "Tabla 202.01" in x["msg"]]
        assert h, "Debe derivar L del vehiculo de diseno y declararlo"
        # B2: vuelo delantero 2.30 + separacion 8.25 = 10.55
        assert "10.55" in h[0]["msg"]

    def test_articulado_emite_observacion(self):
        p = base_proyecto(vehiculo_diseno="T3S3", L_vehiculo_m=None,
                          alineamiento=[curva(radio=100)])
        assert "OBSERVACION" in sev_de(auditar_planta(p), "vehiculo articulado")


# ----------------------------------------------------- tangentes y coordinacion

class TestTangentes:
    def test_tangente_corta_en_S_incumple(self):
        p = base_proyecto(alineamiento=[
            curva(id="C-1", prog_ini=0, prog_fin=100, sentido="D"),
            {"tipo": "tangente", "id": "T-1", "prog_ini": 100, "prog_fin": 135},
            curva(id="C-2", prog_ini=135, prog_fin=235, sentido="I"),
        ])
        assert "NO_CUMPLE" in sev_de(auditar_planta(p), "T-1")

    def test_tangente_muy_larga_observa(self):
        p = base_proyecto(alineamiento=[
            curva(id="C-1", prog_ini=0, prog_fin=100, sentido="D"),
            {"tipo": "tangente", "id": "T-1", "prog_ini": 100, "prog_fin": 1000},
            curva(id="C-2", prog_ini=1000, prog_fin=1100, sentido="I"),
        ])
        assert "OBSERVACION" in sev_de(auditar_planta(p), "T-1")


class TestCoordinacion:
    def test_relacion_radios_fuera_de_tabla_incumple(self):
        p = base_proyecto(alineamiento=[
            curva(id="C-1", prog_ini=0, prog_fin=100, radio=500, sentido="I"),
            curva(id="C-2", prog_ini=100, prog_fin=200, radio=120, sentido="I"),
        ])
        assert "NO_CUMPLE" in sev_de(auditar_planta(p), "Coordinacion")

    def test_no_aplica_con_tangente_larga(self):
        """Sobre 200 m de tangente intermedia el control no aplica (302.04.05)."""
        p = base_proyecto(alineamiento=[
            curva(id="C-1", prog_ini=0, prog_fin=100, radio=500, sentido="I"),
            {"tipo": "tangente", "id": "T-1", "prog_ini": 100, "prog_fin": 400},
            curva(id="C-2", prog_ini=400, prog_fin=500, radio=120, sentido="I"),
        ])
        assert sev_de(auditar_planta(p), "Coordinacion") == []

    def test_autopista_recta_larga_exige_r700(self):
        p = base_proyecto(clase="autopista_primera_clase", grupo_coordinacion=1,
                          velocidad_diseno=100,
                          ubicacion_via="area_rural_plano_u_ondulada",
                          zona_peralte="zona_rural_plano_ondulado_o_accidentado",
                          alineamiento=[
                              curva(id="C-1", prog_ini=0, prog_fin=100, radio=800,
                                    velocidad_especifica=100, sentido="D"),
                              {"tipo": "tangente", "id": "T-1", "prog_ini": 100, "prog_fin": 600},
                              curva(id="C-2", prog_ini=600, prog_fin=700, radio=500,
                                    velocidad_especifica=100, sentido="I"),
                          ])
        assert "NO_CUMPLE" in sev_de(auditar_planta(p), "Coordinacion")


# ------------------------------------------------------------------ trazabilidad

class TestTrazabilidad:
    def test_todo_hallazgo_lleva_cita(self):
        p = json.loads((EJEMPLOS / "tercera_clase_accidentado.json").read_text(encoding="utf-8"))
        inf = auditar_planta(p)
        assert inf.h, "El ejemplo debe producir hallazgos"
        for h in inf.h:
            assert h["cita"].startswith("DG-2018"), f"Sin cita: {h['elem']}"
            assert len(h["cita"]) > len("DG-2018, "), f"Cita vacia: {h['elem']}"

    def test_severidades_validas(self):
        p = json.loads((EJEMPLOS / "tercera_clase_accidentado.json").read_text(encoding="utf-8"))
        for h in auditar_planta(p).h:
            assert h["sev"] in ("NO_CUMPLE", "OBSERVACION", "CUMPLE")


class TestEjemplos:
    @pytest.mark.parametrize("nombre", ["tercera_clase_accidentado", "autopista_100kmh"])
    def test_ejemplos_corren(self, nombre):
        p = json.loads((EJEMPLOS / f"{nombre}.json").read_text(encoding="utf-8"))
        inf = auditar_planta(p)
        assert len(inf.h) > 0
