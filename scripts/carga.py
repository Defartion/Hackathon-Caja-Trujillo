"""Mide una carga sintética sobre una API CuotaFlex local y desechable."""
from __future__ import annotations

import argparse
import asyncio
import math
import os
import platform
import signal
import socket
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from itertools import count
from pathlib import Path
from tempfile import TemporaryDirectory, TemporaryFile
from time import monotonic

import httpx

RAIZ = Path(__file__).resolve().parents[1]
CICLO = ("propuesta", "cliente", "agente", "propuesta", "simulacion",
         "propuesta", "cliente", "agente", "propuesta", "propuesta")
RUTAS = {
    "propuesta": "POST /motor/propuesta",
    "cliente": "GET /cliente/prestamos/{id}",
    "agente": "POST /agente/sesion/{id}/mensaje",
    "simulacion": "POST /simulacion/correr",
}


@dataclass
class Medicion:
    latencias: list[float] = field(default_factory=list)
    errores: Counter = field(default_factory=Counter)


def _percentil(datos: list[float], fraccion: float) -> str:
    if not datos:
        return "—"
    return f"{sorted(datos)[math.ceil(len(datos) * fraccion) - 1]:.1f}"


def _rss_api_mib(pid: int) -> tuple[float, float]:
    """Devuelve RSS del proceso API y de su árbol, incluido el pool del tablero."""
    if os.name == "nt":
        comando = ["powershell.exe", "-NoProfile", "-Command",
                   'Get-CimInstance Win32_Process | ForEach-Object { '
                   '"$($_.ProcessId) $($_.ParentProcessId) $([long]($_.WorkingSetSize / 1KB))" }']
    else:
        comando = ["ps", "-A", "-o", "pid=,ppid=,rss="]
    salida = subprocess.check_output(comando, text=True, timeout=5)
    procesos = {}
    for fila in salida.splitlines():
        partes = fila.split()
        if len(partes) == 3 and all(parte.isdigit() for parte in partes):
            hijo, padre, rss_kib = map(int, partes)
            procesos[hijo] = (padre, rss_kib)
    if pid not in procesos:
        raise RuntimeError("No se encontró el proceso de la API para medir su memoria")
    arbol = {pid}
    while True:
        hijos = {hijo for hijo, (padre, _) in procesos.items() if padre in arbol}
        nuevos = hijos - arbol
        if not nuevos:
            break
        arbol.update(nuevos)
    return procesos[pid][1] / 1024, sum(procesos[hijo][1] for hijo in arbol) / 1024


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _detener(api: subprocess.Popen) -> None:
    if os.name == "nt":
        if api.poll() is None:
            subprocess.run(["taskkill", "/PID", str(api.pid), "/T", "/F"],
                           check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        if api.poll() is None:
            api.terminate()
            try:
                api.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
        # Uvicorn ya cerró los sockets. Recolecta trabajadores que hayan quedado en su grupo.
        try:
            os.killpg(api.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    api.wait(timeout=5)


async def _json(cliente: httpx.AsyncClient, metodo: str, ruta: str, **opciones):
    respuesta = await cliente.request(metodo, ruta, **opciones)
    respuesta.raise_for_status()
    return respuesta.json()


async def _preparar(cliente: httpx.AsyncClient, api: subprocess.Popen, usuarios: int) -> tuple[list, list]:
    limite = monotonic() + 90
    while True:
        if api.poll() is not None:
            raise RuntimeError("Uvicorn se cerró durante el arranque")
        try:
            cartera = await _json(cliente, "GET", "/motor/cartera-demo", params={"n": usuarios, "semilla": 7},
                                  timeout=2)
            break
        except httpx.ConnectError:
            if monotonic() >= limite:
                raise RuntimeError("La API local no arrancó dentro del plazo") from None
            await asyncio.sleep(0.2)
    cartera = [fila for fila in cartera if fila["cliente_id"].startswith("C")]
    if len(cartera) != usuarios:
        raise RuntimeError("La cartera generada no tiene la cantidad de usuarios esperada")
    # El tablero solicita los parámetros y activa sus trabajadores al abrirse.
    await _json(cliente, "GET", "/simulacion/parametros-editables")
    prestamo = await _json(cliente, "POST", "/cliente/demo-seed", params={"producto": "aplazamiento"})
    sesiones = [await _json(cliente, "POST", "/agente/sesion", json=solicitud) for solicitud in cartera[:usuarios]]
    return cartera, [prestamo["loanId"], *(sesion["sesion_id"] for sesion in sesiones)]


async def _correr(cliente: httpx.AsyncClient, pid: int, cartera: list, estado: list, usuarios: int,
                 duracion: float) -> dict:
    prestamo, *sesiones = estado
    mediciones = {ruta: Medicion() for ruta in RUTAS}
    siguiente = count()
    simulacion = count()
    cache = Counter()
    memoria = [await asyncio.to_thread(_rss_api_mib, pid)]
    inicio = monotonic()
    fin = inicio + duracion

    async def usuario(i: int) -> None:
        while monotonic() < fin:
            numero = next(siguiente)
            ruta = CICLO[numero % len(CICLO)]
            medicion = mediciones[ruta]
            t0 = monotonic()
            try:
                if ruta == "propuesta":
                    await _json(cliente, "POST", "/motor/propuesta", json=cartera[numero % len(cartera)])
                elif ruta == "cliente":
                    await _json(cliente, "GET", f"/cliente/prestamos/{prestamo}")
                elif ruta == "agente":
                    await _json(cliente, "POST", f"/agente/sesion/{sesiones[i]}/mensaje",
                                json={"texto": "¿Y a 24 meses?"})
                else:
                    semilla, variante = divmod(next(simulacion) % 6, 2)
                    respuesta = await _json(cliente, "POST", "/simulacion/correr", json={
                        "n_clientes": 150, "n_escenarios": 80, "semilla": 2026 + semilla,
                        "replanificar": True, "cambios": {"el_nino.probabilidad_anual": 1.0} if variante else {},
                    })
                    cache["acierto" if respuesta["desde_cache"] else "cálculo"] += 1
            except httpx.HTTPStatusError as error:
                medicion.errores[f"HTTP {error.response.status_code}"] += 1
            except (httpx.RequestError, ValueError, KeyError) as error:
                medicion.errores[type(error).__name__] += 1
            else:
                medicion.latencias.append((monotonic() - t0) * 1000)

    async def muestrear_memoria(tarea: asyncio.Future) -> None:
        while not tarea.done():
            await asyncio.wait([tarea], timeout=1)
            memoria.append(await asyncio.to_thread(_rss_api_mib, pid))

    tarea = asyncio.gather(*(usuario(i) for i in range(usuarios)))
    await asyncio.gather(tarea, muestrear_memoria(tarea))
    return {"mediciones": mediciones, "memoria": memoria, "cache": cache, "total_s": monotonic() - inicio}


def _reporte(resultado: dict, argumentos) -> str:
    total = sum(len(m.latencias) + m.errores.total() for m in resultado["mediciones"].values())
    memoria = resultado["memoria"]
    lineas = [
        "# Carga ligera de CuotaFlex", "",
        f"Medición del {datetime.now().astimezone().isoformat(timespec='seconds')} en "
        f"{platform.platform()}, Python {platform.python_version()} y {os.cpu_count()} núcleos lógicos.", "",
        f"Se ejecutaron {argumentos.usuarios} usuarios concurrentes durante {argumentos.duracion:g} s "
        f"en una API local desechable. Se completaron {total} intentos en {resultado['total_s']:.1f} s, "
        "incluidas las solicitudes que seguían en curso al cerrar la ventana.",
        "Se usaron datos sintéticos, ENFEN en modo demo y plantillas del agente. Las simulaciones de "
        "tamaño Rápido usaron 150 créditos × 80 escenarios, alternando Base y Año El Niño "
        "con tres semillas consecutivas desde 2026.", "",
        "| Endpoint | Intentos | Mezcla real | p50 (ms) | p95 (ms) | Error | Detalle |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for k, m in resultado["mediciones"].items():
        cantidad = len(m.latencias) + m.errores.total()
        p50, p95 = (_percentil(m.latencias, p) for p in (0.5, 0.95))
        tasa = f"{m.errores.total() / cantidad:.2%}" if cantidad else "—"
        errores = ", ".join(f"{detalle} × {n}" for detalle, n in sorted(m.errores.items())) or "—"
        mezcla = f"{cantidad / total:.1%}" if total else "—"
        lineas.append(f"| `{RUTAS[k]}` | {cantidad} | {mezcla} | {p50} | {p95} | {tasa} | {errores} |")
    cache = resultado["cache"]
    lineas.extend([
        "",
        f"La API tuvo {memoria[0][0]:.1f} MiB de RSS al iniciar la carga y un máximo de "
        f"{max(m[0] for m in memoria):.1f} MiB. El árbol completo, incluidos los trabajadores de simulación, "
        f"alcanzó {max(m[1] for m in memoria):.1f} MiB en {len(memoria)} muestras.",
        f"En simulación hubo {cache['cálculo']} respuestas calculadas y {cache['acierto']} servidas desde caché.", "",
        "## Método e interpretación", "",
        "- La mezcla programada es 50 % propuestas, 20 % vistas, 20 % chat y 10 % simulaciones. "
        "Cada usuario inicia su siguiente petición al terminar la anterior.",
        "- Los percentiles usan rango más cercano sobre respuestas exitosas. La latencia incluye HTTP y "
        "lectura del cuerpo. Los fallos HTTP, de transporte y de lectura cuentan en el porcentaje de error.",
        "- Se excluye la preparación de la cartera sintética, el préstamo activo y una sesión por usuario. "
        f"El tiempo límite por fase HTTP es de {argumentos.timeout:g} s.",
        "- La RSS se muestrea aproximadamente una vez por segundo. La suma del árbol puede contar páginas "
        "compartidas en más de un proceso.",
        "",
    ])
    lentas = [RUTAS[k] for k, m in resultado["mediciones"].items()
              if k != "simulacion" and m.latencias and float(_percentil(m.latencias, 0.95)) > 3000]
    if lentas:
        lineas.extend(["## Consultas por encima de 3 s", ""])
        lineas.extend(f"- `{ruta}`." for ruta in lentas)
        lineas.extend([
            "",
            "Compara estas rutas con una corrida de un usuario y revisa CPU, RSS y tiempos del motor. "
            "Una diferencia bajo concurrencia indicaría contención; una latencia alta con un usuario "
            "justifica medir los pasos internos con un perfilador. Repite la carga tras el cambio que "
            "corresponda para comprobar su efecto.", "",
        ])
    else:
        lineas.extend(["Las rutas distintas de simulación quedaron por debajo de 3 s en p95.", ""])
    lineas.extend(["## Reproducir", "", "```bash", "python scripts/carga.py", "```", ""])
    return "\n".join(lineas)


async def _medir(argumentos, puerto: int, api: subprocess.Popen) -> dict:
    async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{puerto}", trust_env=False,
                                 timeout=argumentos.timeout,
                                 limits=httpx.Limits(max_connections=argumentos.usuarios)) as cliente:
        cartera, estado = await _preparar(cliente, api, argumentos.usuarios)
        print(f"API local lista. Iniciando {argumentos.usuarios} usuarios por {argumentos.duracion:g} s.", flush=True)
        return await _correr(cliente, api.pid, cartera, estado, argumentos.usuarios, argumentos.duracion)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duracion", type=float, default=120, help="Segundos para iniciar peticiones")
    parser.add_argument("--usuarios", type=int, default=10, help="Número de usuarios simultáneos")
    parser.add_argument("--timeout", type=float, default=45, help="Tiempo límite por fase de petición, en segundos")
    parser.add_argument("--salida", type=Path, default=RAIZ / "docs/demo/CARGA.md")
    args = parser.parse_args()
    if (not 1 <= args.usuarios <= 100 or not math.isfinite(args.duracion) or args.duracion <= 0
            or not math.isfinite(args.timeout) or args.timeout <= 0):
        parser.error("Usa entre 1 y 100 usuarios, duración y timeout finitos y positivos.")

    puerto = _puerto_libre()
    entorno = os.environ.copy()
    entorno.update(PYTHONPATH=str(RAIZ / "src"), ENFEN_MODO="demo",
                   ENFEN_REVISION_AUTOMATICA="0", CUOTAFLEX_LLM="0")
    entorno.pop("FINERACT_URL", None)
    opciones = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt"
                else {"start_new_session": True})
    with TemporaryDirectory() as carpeta, TemporaryFile() as registro:
        entorno["NOTIFICACIONES_ARCHIVO"] = str(Path(carpeta) / "notificaciones.jsonl")
        api = subprocess.Popen([sys.executable, "-m", "uvicorn", "cuotaflex.api.main:app",
                                "--host", "127.0.0.1", "--port", str(puerto), "--no-access-log"],
                               cwd=RAIZ, env=entorno, stdout=registro, stderr=subprocess.STDOUT, **opciones)
        try:
            resultado = asyncio.run(_medir(args, puerto, api))
        except (httpx.HTTPError, OSError, RuntimeError) as error:
            print(f"Prueba interrumpida. {error}", file=sys.stderr)
            registro.seek(0)
            print(registro.read().decode(errors="replace")[-3000:], file=sys.stderr)
            return 1
        finally:
            _detener(api)

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(_reporte(resultado, args), encoding="utf-8")
    print(f"Reporte de carga generado en {args.salida}")
    return int(any(m.errores for m in resultado["mediciones"].values()))


if __name__ == "__main__":
    raise SystemExit(main())
