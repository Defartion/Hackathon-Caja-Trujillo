# Concepto v2 de CuotaFlex

[Concepto editable](CONCEPT_SOLUTION.md) · [PDF](export/CuotaFlex-Solution-Concept-v2.pdf) · [Resumen editable](one-pager.md)

Esta revisión usa los resultados calibrados de la fase 2. [La versión entregada en la fase 1](../CONCEPT_SOLUTION.md) conserva las cifras y figuras de entonces.

Desde la raíz del repositorio, con las dependencias de `requirements.txt` instaladas:

```bash
python docs/concepto/generar_figuras.py --salida docs/concepto/v2/img/cronograma-ejemplo.png
python -m pip install markdown-it-py playwright
python -m playwright install chromium
python docs/concepto/v2/exportar_pdf.py
```
