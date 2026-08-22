# Indice de trazabilidad normativa — Auditor DG-2018 (Modulo Planta)

Manual de Carreteras: Diseno Geometrico DG-2018 (MTC, Peru) — Seccion 302 y concordantes.

Cada verificacion del auditor esta anclada a un articulo y tabla del manual.
Si el auditor reporta un hallazgo, esta tabla indica exactamente donde leer la
justificacion en la norma.

| Verificacion | Seccion | Tabla | Pagina del manual |
|---|---|---|---|
| Longitud de tangente (S / mismo sentido / maxima) | 302.03 | 302.01 | 127 |
| Radio minimo por ubicacion y velocidad | 302.04.02 | 302.02 | 128-129 |
| Radio minimo por peralte maximo adoptado | 302.04.02 | 302.04 | 131 |
| Friccion transversal maxima | 302.04.03 | 302.03 | 131 |
| Curvas en contraperalte - radio limite | 302.04.04 | 302.05 | 132 |
| Contraperalte en sectores singulares | 302.04.04 | 302.06 | 133 |
| Coordinacion radios consecutivos - grupo 1 | 302.04.05 | 302.07 | 135-136 |
| Coordinacion radios consecutivos - grupo 2 | 302.04.05 | 302.08 | 137 |
| Autopistas: recta >400 m exige R salida >=700 m | 302.04.05 | - | 137 |
| Variacion aceleracion transversal J | 302.05.03 | 302.09 | 139 |
| Longitud minima de clotoide (piso 30 m) | 302.05.04 | 302.10 | 139-140 |
| Parametro A de clotoide (A^2 = R*L) | 302.05.02/03 | - | 138-139 |
| Radios que permiten prescindir de transicion | 302.05.07 | 302.11 A | 146 |
| Idem - carreteras de Tercera Clase | 302.05.07 | 302.11 B | 146 |
| Curvas compuestas: relacion <= 1.5 | 302.06.02 | - | 147 |
| Curvas mismo sentido: tangente >= 400 m | 302.06.03 | - | 147 |
| Curvas de vuelta: Ri / Re por maniobra | 302.07 | 302.12 | 150-151 |
| Transicion de peralte - ipmax = 1.8-0.01V | 302.08 | - | 152 |
| Transicion de peralte - Tercera Clase | 302.08 | 302.13 | 156 |
| Transicion de peralte por ancho y eje de giro | 302.08 | 302.14-302.18 | 152-154 |
| Sobreancho - formula general (todo el rango de V) | 302.09.03 | - | 160-161 |
| Vehiculo de diseno (dimensiones, L) | 202.02/202.03 | 202.01 | 27 |
| Desarrollo del sobreancho en la transicion | 302.09.04 | - | 162-163 |
| Holguras teoricas vehiculos comerciales | 302.09.01 | 302.19 | 159 |
| Factores de reduccion del sobreancho | 302.09.03 | 302.20 | 162 |
| Visibilidad en curva - ancho libre amin | 302.10.03 | - | 167 |
| Distancias minimas a obstaculos fijos | 302.10 | 302.21 | 166 |
| Zonas de no adelantar - senalizacion | 302.10.04 | - | 167 |
| % tramo con visibilidad de adelantamiento | 302.10.05 | 302.22 | 168 |
| Distancia de visibilidad de parada (Dp) | 205.02 | 205.01 | 104 |
| Dp corregida por pendiente | 205.02 | 205.01-A | 105 |
| Peralte maximo absoluto y normal | 304.06.01 | 304.05 | 196 |

**Total: 33 controles normativos implementados.**

## Como leer un hallazgo

```
[X] NO_CUMPLE | Curva C-2 (km 0+505) - radio minimo
    Radio 38 m < minimo 45 m (V=40 km/h, area rural accidentada o escarpada)
    Cita: DG-2018, Seccion 302.04.02, Tabla 302.02, pag. 128-129
    Norma: "debe evitarse el empleo de curvas de radio minimo..."
```

- `[X] NO_CUMPLE` — incumple un valor normativo explicito.
- `[!] OBSERVACION` — margen estrecho, dato faltante, o criterio que la norma
  formula como recomendacion ("se evitara", "es deseable") y requiere sustento.
- `[OK] CUMPLE` — verificado conforme; se reporta para dejar constancia en el
  informe de auditoria.

La linea **Cita** da seccion, tabla y pagina exacta. La linea **Norma**
transcribe el texto del manual cuando este es literal y decisivo.

## Origen de los datos

Los valores no provienen de la memoria de un modelo de lenguaje: fueron
extraidos del PDF oficial con `pdftotext -layout` y las tablas matriciales
criticas (302.02, 303.01, 205.01-A) se cotejaron visualmente contra las paginas
rasterizadas del manual. Todo reside en `dg2018_reglas_base.json`, editable y
auditable de forma independiente al codigo.

## Nota sobre el sobreancho y la velocidad de diseno

La formula de 302.09.03 —`Sa = n(R - sqrt(R^2 - L^2)) + V/(10*sqrt(R))`— **no
tiene techo de velocidad**: es aplicable a todo el rango. Lo que la norma
restringe a V <= 80 km/h y calzada de 7.20 m es la **Tabla 302.20 de factores de
reduccion** (pag. 162).

La frase "sera calculado para cada caso" para radios mayores y V > 80 km/h no
significa que no exista formula, sino que en ese regimen no se aplica el factor
de reduccion tabulado: se calcula directo con el vehiculo de diseno del proyecto.
El auditor implementa ambos regimenes y declara en cada hallazgo cual aplico y
por que.

**Sobre el parametro L:** la norma no lo tabula por vehiculo. El auditor lo
deriva de la Tabla 202.01 como `L = vuelo delantero + separacion de ejes`. Para
vehiculos articulados (T2S1, T3S3, BA-1, C2R1, T3S2S2, T3S2S1S2) sumar todos los
tramos es conservador, porque la formula de la DG asume un L unico; en esos casos
el auditor emite una observacion, ofrece el calculo alternativo con el tramo
mayor, y exige que el proyectista sustente el L adoptado. La decision queda en el
ingeniero, documentada.
