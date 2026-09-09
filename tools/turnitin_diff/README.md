# turnitin_diff

Comparador de informes Turnitin *AI Writing* en PDF.

Extrae, para cada informe, el texto del documento y los tramos resaltados como IA
(rectángulos cian que Turnitin dibuja bajo el texto), reconstruye los párrafos por
geometría, alinea los párrafos entre versiones (Needleman–Wunsch sobre similitud
Jaccard de palabras) y localiza los párrafos marcados en la versión base que tienen
una reescritura limpia en alguna versión posterior.

## Uso

```bash
pip install pymupdf numpy python-docx
python para2.py      # extrae párrafos con % de texto marcado -> paras.json
python align.py      # alinea cada versión contra la base -> align.json
python report2.py    # resumen por consola
python build.py      # Sustituciones_v2_humanizadas.docx
python md.py         # INFORME_COMPARATIVO_IA.md
```

Las rutas de los PDF y las etiquetas de versión están en la lista `NAMES` de
`para.py` / `para2.py`.

## Criterios

- Solo se consideran párrafos de contenido (>= 25 palabras).
- Candidato a sustitución: párrafo alineado con <= 10 % de texto marcado y
  similitud léxica entre 0,25 y 0,90 (reescritura real, no texto idéntico).
- Mejora parcial: <= 25 % marcado y al menos 25 puntos por debajo de la base.
- Similitud > 0,95 con veredicto distinto se descarta: es ruido del detector,
  no una reescritura.
