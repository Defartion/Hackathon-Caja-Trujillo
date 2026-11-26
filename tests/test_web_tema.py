"""Sistema de diseño compartido: las tres apps usan copias idénticas de tema.css, marca.tsx, sesion.tsx,
apariencia.tsx (tema claro u oscuro), exportar.ts y MenuExportar.tsx.

Cada app se compila sola (Docker copia solo web/<app>/), por eso los archivos comunes van copiados.
Si cambias uno, copia la versión de web/asesor/src/ a web/cliente/src/ y web/tablero/src/.
"""
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
APPS = ("asesor", "cliente", "tablero")


COMUNES = ["tema.css", "marca.tsx", "sesion.tsx", "apariencia.tsx", "exportar.ts", "MenuExportar.tsx"]


@pytest.mark.parametrize("archivo", COMUNES)
def test_archivos_comunes_son_copias_identicas(archivo):
    copias = {app: (RAIZ / "web" / app / "src" / archivo).read_text(encoding="utf-8") for app in APPS}
    distintas = [app for app in APPS if copias[app] != copias["asesor"]]
    assert not distintas, f"{archivo} difiere en {distintas}: copia web/asesor/src/{archivo} a esas apps"


@pytest.mark.parametrize("app", APPS)
def test_cada_app_carga_la_fuente_y_el_tema_antes_que_sus_estilos(app):
    main = (RAIZ / "web" / app / "src" / "main.tsx").read_text(encoding="utf-8")
    fuente = main.find("@fontsource-variable/archivo")
    tema = main.find("./tema.css")
    estilos = main.find("./styles.css")
    assert -1 < fuente < tema < estilos, "orden esperado: fuente, tema.css y luego styles.css"


def test_la_portada_usa_la_fuente_que_publica_la_app_del_asesor():
    portada = (RAIZ / "public" / "index.html").read_text(encoding="utf-8")
    assert "Elige tu rol" in portada
    css = re.search(r"<style>(.*?)</style>", portada, re.S).group(1)
    sin_comentarios = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    assert "*/" not in sin_comentarios, "un comentario se cierra antes de tiempo (ojo con rutas como web/*/src)"
    assert "@font-face" in sin_comentarios
    assert "/asesor/fuentes/archivo-latin-wdth-normal.woff2" in portada
    assert (RAIZ / "web" / "asesor" / "public" / "fuentes" / "archivo-latin-wdth-normal.woff2").is_file()



@pytest.mark.parametrize("app", APPS)
def test_cada_app_aplica_el_tema_guardado_antes_de_pintar(app):
    """El script en línea del index.html usa la misma clave que apariencia.tsx, para que no parpadee."""
    html = (RAIZ / "web" / app / "index.html").read_text(encoding="utf-8")
    apariencia = (RAIZ / "web" / app / "src" / "apariencia.tsx").read_text(encoding="utf-8")
    clave = re.search(r'const CLAVE = "([^"]+)"', apariencia).group(1)
    cabeza = html.split("</head>")[0]
    assert f'localStorage.getItem("{clave}")' in cabeza
    assert "dataset.tema" in cabeza and "prefers-color-scheme: dark" in cabeza


def test_la_portada_tiene_tema_oscuro_y_comparte_la_clave():
    portada = (RAIZ / "public" / "index.html").read_text(encoding="utf-8")
    assert 'localStorage.getItem("cuotaflex.tema")' in portada.split("</head>")[0]
    assert ':root[data-tema="oscuro"]' in portada
    assert 'role="switch"' in portada and 'aria-label="Tema oscuro"' in portada


def test_el_tema_oscuro_redefine_los_colores_que_usan_las_apps():
    """Cada color del tema claro que cambia de sentido en oscuro tiene su valor oscuro."""
    tema = (RAIZ / "web" / "asesor" / "src" / "tema.css").read_text(encoding="utf-8")
    claro = re.search(r":root, \.cf-claro \{(.*?)\n\}", tema, re.S).group(1)
    oscuro = re.search(r':root\[data-tema="oscuro"\] \{(.*?)\n\}', tema, re.S).group(1)
    variables = lambda bloque: set(re.findall(r"(--cf-[a-z0-9-]+):", bloque))
    deben_cambiar = {v for v in variables(claro) if v.startswith(("--cf-gris", "--cf-graf", "--cf-superficie"))}
    deben_cambiar |= {"--cf-tinta", "--cf-fondo", "--cf-elevada", "--cf-lateral", "--cf-rojo-texto"}
    assert deben_cambiar <= variables(oscuro), sorted(deben_cambiar - variables(oscuro))
