#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Interfaz de linea de comandos del Auditor DG-2018."""

import argparse
import json
import sys
from pathlib import Path

from .planta import auditar_planta, cargar_proyecto


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="auditor-dg2018",
        description="Auditor de diseno geometrico segun el Manual de Carreteras "
                    "DG-2018 (MTC, Peru). Verifica el diseno y cita la norma.")
    ap.add_argument("proyecto", help="Archivo JSON con los datos del proyecto")
    ap.add_argument("-m", "--modulo", default="planta", choices=["planta"],
                    help="Modulo de auditoria a ejecutar (por ahora solo 'planta')")
    ap.add_argument("-f", "--formato", default="texto", choices=["texto", "json"],
                    help="Formato de salida")
    ap.add_argument("-o", "--salida", help="Archivo de salida (por defecto: stdout)")
    ap.add_argument("--solo-hallazgos", action="store_true",
                    help="Omitir las verificaciones conformes (CUMPLE)")
    ap.add_argument("--strict", action="store_true",
                    help="Codigo de salida 1 si hay incumplimientos (util en CI)")
    a = ap.parse_args(argv)

    try:
        proyecto = cargar_proyecto(a.proyecto)
    except FileNotFoundError:
        print(f"Error: no se encontro el archivo '{a.proyecto}'", file=sys.stderr)
        return 2
    except json.JSONDecodeError as e:
        print(f"Error: JSON invalido en '{a.proyecto}': {e}", file=sys.stderr)
        return 2

    informe = auditar_planta(proyecto)

    if a.solo_hallazgos:
        informe.h = [x for x in informe.h if x["sev"] != "CUMPLE"]

    texto = json.dumps(informe.dict(), ensure_ascii=False, indent=2) \
        if a.formato == "json" else informe.texto()

    if a.salida:
        Path(a.salida).write_text(texto, encoding="utf-8")
        print(f"Informe escrito en {a.salida}")
    else:
        print(texto)

    if a.strict and any(x["sev"] == "NO_CUMPLE" for x in informe.h):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
