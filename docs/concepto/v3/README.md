# Concepto v3 de CuotaFlex

[Concepto editable](CONCEPT_SOLUTION.md) · [PDF](export/CuotaFlex-Solution-Concept-v3.pdf) · [Resumen editable](one-pager.md)

Esta revisión ajusta el concepto a las preguntas frecuentes del NEG-01 publicadas el 24 de noviembre: solo créditos nuevos con el plan fijo desde el desembolso, ciclo estimado con fuentes públicas y la captura del asesor, Cuota/UN ≤ factor en cada etapa, costos de la Caja y vista para el comité. [La versión 2](../v2/CONCEPT_SOLUTION.md) y [la versión entregada en la fase 1](../CONCEPT_SOLUTION.md) se conservan sin cambios.

Desde la raíz del repositorio, con las dependencias de `requirements-dev.txt` instaladas:

```bash
python docs/concepto/v3/cifras_cuota_un.py      # cifras de Cuota/UN (cerca de un minuto)
python docs/concepto/v3/generar_figura.py       # figura 1
python -m pip install markdown-it-py
python -m playwright install chromium
python docs/concepto/v3/exportar_pdf.py
```

Los diagramas se regeneran desde `docs/concepto/v3/img/` con el comando indicado al inicio de cada archivo `.mmd`.
