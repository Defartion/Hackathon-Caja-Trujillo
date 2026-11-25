# Final del Cajatón · 3 y 4 de diciembre de 2026, Hub UPAO

Todo lo necesario para que los dos días de la final rindan al máximo (fase 3, lote C).

| Documento | Para qué sirve |
|---|---|
| [PLAN_DOS_DIAS.md](PLAN_DOS_DIAS.md) | Plan por horas, controles cada 2 horas, regla de recorte y regla de oro |
| [MODULO_EN_VIVO.md](MODULO_EN_VIVO.md) | Diseño del módulo que se construye en el evento: pago por ventas y pago a cosecha (8 horas) |
| [CHECKLIST.md](CHECKLIST.md) | Lista de verificación de equipos, cuentas, software y datos, con responsables |
| [CONTINGENCIAS.md](CONTINGENCIAS.md) | Qué hacer si falla internet, Fineract, la IA, el proyector o una laptop |
| [VIDEO.md](VIDEO.md) | Video de respaldo: guion, enlace y cómo volver a grabarlo |
| [PROPIEDAD_INTELECTUAL.md](PROPIEDAD_INTELECTUAL.md) | Qué existía antes del evento, qué se construye en él y licencias de terceros |

## ¿Está lista la laptop?

```bash
scripts/verificar_entorno.sh                 # Linux, Mac o Git Bash
```

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verificar_entorno.ps1    # Windows
```

Responde en verde o rojo: versiones de Python y Node, dependencias, `pytest` rápido (~20 s), compilación de
las tres apps, puertos 8000 y 5173–5175 libres, Docker (opcional) y espacio en disco. Con `--rapido`
(`-Rapido` en PowerShell) tarda unos segundos; con `--completo`, corre todas las pruebas.
