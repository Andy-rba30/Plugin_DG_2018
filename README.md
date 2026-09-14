# Auditor DG-2018

Auditor de diseño geométrico vial según el **Manual de Carreteras: Diseño
Geométrico DG-2018** (MTC, Perú).

Revisa un alineamiento y reporta qué incumple la norma, **citando sección, tabla
y página exactas** del manual, para que el proyectista pueda verificar el
sustento en la fuente en segundos.

```
[X] NO_CUMPLE | Curva C-2 (km 0+505) - radio minimo
    Radio 38 m < minimo 45 m (V=40 km/h, area rural accidentada o escarpada,
    peralte max 12.0%).
    Cita: DG-2018, Seccion 302.04.02, Tabla 302.02, pag. 128-129
    Norma: "debe evitarse el empleo de curvas de radio minimo; se tratara de
    usar curvas de radio amplio, reservando el empleo de radios minimos para
    las condiciones criticas"
```

## Estado

| Módulo | Estado | Cobertura |
|---|---|---|
| **Planta** (Sección 302) | Completo | 33 controles normativos |
| **Perfil** (Sección 303) | Parcial | Pendientes máx/mín, índices K |
| **Sección transversal** (304) | Parcial | Bombeo, peralte máximo |
| **Sincronía planta–perfil–transversal** | Pendiente | Reglas esqueletadas |

## Instalación

Sin dependencias externas: solo la librería estándar de Python (>=3.9).

```bash
git clone <url-del-repo>
cd auditor-dg2018
pip install -e .
```

## Uso

```bash
# Auditar un proyecto
auditor-dg2018 examples/tercera_clase_accidentado.json

# Solo lo que falla (omitir los CUMPLE)
auditor-dg2018 mi_proyecto.json --solo-hallazgos

# Salida JSON para integrar con otras herramientas
auditor-dg2018 mi_proyecto.json -f json -o informe.json

# En CI: código de salida 1 si hay incumplimientos
auditor-dg2018 mi_proyecto.json --strict
```

Como librería:

```python
from auditor_dg2018 import auditar_planta, cargar_proyecto

informe = auditar_planta(cargar_proyecto("mi_proyecto.json"))
print(informe.texto())

incumplimientos = [h for h in informe.h if h["sev"] == "NO_CUMPLE"]
```

## Formato del proyecto

```jsonc
{
  "nombre": "Tramo km 0+000 a 6+000",
  "clase": "carretera_tercera_clase",   // autopista_primera_clase | autopista_segunda_clase |
                                        // carretera_primera_clase | carretera_segunda_clase |
                                        // carretera_tercera_clase
  "grupo_coordinacion": 2,              // 1 = autopistas y 1ra clase; 2 = 2da y 3ra clase
  "orografia": 3,                       // 1 plano | 2 ondulado | 3 accidentado | 4 escarpado
  "velocidad_diseno": 40,               // km/h
  "ubicacion_via": "area_rural_accidentada_o_escarpada",
  "zona_peralte": "zona_rural_accidentado_o_escarpado",
  "n_carriles": 2,
  "ancho_calzada_m": 6.00,
  "B_eje_giro_m": 3.0,                  // borde de calzada al eje de giro del peralte
  "bombeo_pct": 2.5,
  "vehiculo_diseno": "T3S3",            // de la Tabla 202.01; o usar "L_vehiculo_m" directo
  "pavimentada": true,
  "pct_visibilidad_adelantamiento": 15, // solo para tramos > 5 km

  "obstaculos": [
    {"id": "OB-1", "progresiva": 520,
     "tipo": "obstaculos_aislados_pilares_postes", "distancia_m": 0.40}
  ],

  "alineamiento": [                     // ORDENADO por progresiva (metros)
    {"tipo": "tangente", "id": "T-1", "prog_ini": 0, "prog_fin": 350},
    {"tipo": "curva", "id": "C-1", "prog_ini": 350, "prog_fin": 470,
     "radio": 60, "velocidad_especifica": 40, "sentido": "D",
     "peralte_pct": 8.0, "pendiente_pct": -6.0,
     "long_transicion_entrada_m": 40, "sobreancho_m": 1.0,
     "ancho_libre_m": 5.0}
  ]
}
```

Campos opcionales de curva: `contraperalte`, `curva_de_vuelta` (con
`radio_interior_m`, `radio_exterior_m`, `maniobra`), `ancho_libre_m`.
Ver `examples/` para casos completos.

## Cómo leer un hallazgo

- **`[X] NO_CUMPLE`** — incumple un valor normativo explícito.
- **`[!] OBSERVACION`** — margen estrecho, dato faltante, o criterio que la norma
  formula como recomendación (*"se evitará"*, *"es deseable"*) y requiere sustento.
- **`[OK] CUMPLE`** — verificado conforme. Se reporta a propósito: en una
  auditoría formal, dejar constancia de lo verificado importa tanto como señalar
  lo que falla.

La distinción entre las dos primeras es deliberada. La DG-2018 mezcla
prescripciones y recomendaciones; un auditor que las trate igual genera ruido y
pierde credibilidad.

## Arquitectura

```
auditor_dg2018/
├── data/dg2018_reglas_base.json   <- TODOS los valores normativos
├── planta.py                      <- motor de verificación (sin valores hardcodeados)
└── cli.py
```

**Separación deliberada entre datos y lógica.** Ningún valor de la norma está
escrito en el código Python: todo se consulta en `dg2018_reglas_base.json`. Esto
permite auditar los datos sin leer código, corregir un valor sin tocar la lógica,
y que un ingeniero verifique la base normativa contra el manual de forma
independiente.

Cada regla del JSON lleva su bloque `fuente` con sección, tabla y página.

## Metodología de extracción de la norma

Los valores **no provienen de la memoria de un modelo de lenguaje**. Se
extrajeron del PDF oficial con `pdftotext -layout`, y las tablas matriciales
críticas se cotejaron visualmente contra las páginas rasterizadas del manual.

Esa verificación no es ceremonial. Ejemplos reales encontrados en el proceso:

- La **Tabla 202.01** (vehículos de diseño) extraía el vehículo ligero con largo
  `15.80 m` y radio `17.30 m`. Los valores reales son **5.80 m** y **7.30 m**:
  el `1` era ruido de la columna vecina. Cargarlo sin verificar habría
  distorsionado todos los cálculos de sobreancho.
- La **Tabla 303.01** (pendientes máximas) cruza 5 clases × 4 orografías × 11
  velocidades; la extracción de texto plano desalinea las columnas y asigna
  valores a la orografía equivocada.

Por eso se desaconseja poblar `dg2018_reglas_base.json` con herramientas de
extracción automática no verificadas.

## Tests

```bash
pip install pytest
pytest tests/ -v
```

La suite cumple dos funciones: validar el motor de reglas, y actuar como
**control de integridad de los datos normativos**. Si alguien edita el JSON y
altera un valor de la norma por error, los tests fallan — los valores esperados
provienen del PDF oficial.

## Documentación

- [`docs/INDICE_TRAZABILIDAD_PLANTA.md`](docs/INDICE_TRAZABILIDAD_PLANTA.md) —
  mapa de los 33 controles con su ubicación exacta en el manual. Sirve como anexo
  del informe de auditoría y como documento de defensa técnica.

## Alcance y limitaciones

Esta herramienta **asiste** la revisión de diseño; no la reemplaza ni constituye
aprobación de ningún tipo. La responsabilidad del diseño y su conformidad con la
normativa vigente es del ingeniero proyectista.

Limitaciones conocidas:

- El parámetro `L` para el sobreancho no está tabulado por vehículo en la norma;
  se deriva de la Tabla 202.01 como `vuelo delantero + separación de ejes`. Para
  vehículos articulados esa derivación es conservadora y el auditor lo advierte
  explícitamente, ofreciendo el cálculo alternativo.
- Las Figuras 302.06/302.07 se implementan vía las Tablas 302.07/302.08; la
  lectura gráfica fina no está cubierta.
- Verificar siempre contra la versión vigente del manual: la DG-2018 puede tener
  modificatorias posteriores.

## Norma de referencia

Ministerio de Transportes y Comunicaciones del Perú, Dirección General de Caminos
y Ferrocarriles. *Manual de Carreteras: Diseño Geométrico DG-2018*. Revisada y
corregida a enero de 2018.

El PDF de la norma **no se incluye en este repositorio**.

## Calculadora (`calculadora.py`)

Utilidad independiente en la raíz del repositorio, sin dependencias externas.
Evalúa expresiones aritméticas de forma segura (analiza el árbol sintáctico con
`ast`; nunca llama a `eval`), con funciones matemáticas, constantes, historial,
memoria (M+, M-, MR, MC) y la variable `ans` con el último resultado.

```bash
python calculadora.py                     # modo interactivo (escriba 'ayuda')
python calculadora.py "(2 + 3) * 4"       # -> 20
python calculadora.py "sqrt(2)" -p 4      # -> 1.4142
python calculadora.py -- "-5 + 3"         # -> -2  ('--' si empieza por un signo menos)
python -m pytest tests/test_calculadora.py
```

Como librería:

```python
from calculadora import Calculadora, evaluar

evaluar("2 ^ 10 + factorial(5)")          # 1144

c = Calculadora()
c.evaluar("10 / 4")                       # 2.5
c.evaluar("ans * 2")                      # 5.0
c.raiz(27, 3)                             # 3.0
c.historial                               # [('10 / 4', 2.5), ('ans * 2', 5.0), ('raiz(27, 3)', 3.0)]
```
