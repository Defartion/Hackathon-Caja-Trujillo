"""Sistema de diseño compartido: las tres apps usan copias idénticas de tema.css, marca.tsx y sesion.tsx.

Cada app se compila sola (Docker copia solo web/<app>/), por eso los archivos comunes van copiados.
Si cambias uno, copia la versión de web/asesor/src/ a web/cliente/src/ y web/tablero/src/.
"""
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
APPS = ("asesor", "cliente", "tablero")


@pytest.mark.parametrize("archivo", ["tema.css", "marca.tsx", "sesion.tsx"])
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
