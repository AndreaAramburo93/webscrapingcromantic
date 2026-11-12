"""Tablero de precios: arma las métricas y genera el reporte estático.

`contexto()` calcula todo lo que muestra el tablero (indicadores, top de
descuentos, top de productos caros, producto destacado y marcas). Lo usan la
app web (Render) y `construir_html()`, que genera site/index.html para GitHub
Pages en cada ejecución del pipeline. Así las dos versiones muestran lo mismo.
"""

import pandas as pd
from jinja2 import Environment, PackageLoader, select_autoescape

from . import __version__, historial
from .analysis import mas_caros, por_marca, resumen_precios
from .perfil import perfil_producto
from .scraper import formatear_cop

_entorno_plantillas = Environment(
    loader=PackageLoader("cromantic_scraper", "templates"),
    autoescape=select_autoescape(["html"]),
)


def contexto(df, hist=None, calidad=None):
    """Métricas del tablero a partir del catálogo actual y el historial."""
    if hist is None:
        hist = pd.DataFrame(columns=historial.COLUMNAS)
    r = resumen_precios(df)
    descuentos = historial.top_descuentos(hist, 10)
    caros = mas_caros(df, 5).to_dict("records")

    # Producto destacado: el de mayor descuento; si aún no hay historial,
    # el más caro del catálogo.
    sku = descuentos[0]["sku"] if descuentos else (caros[0]["sku"] if caros else None)
    destacado = perfil_producto(df, hist, sku) if sku else None

    return {
        "resumen": {k: v if k == "productos" else formatear_cop(v)
                    for k, v in r.items()},
        "marcas": por_marca(df).to_dict("records"),
        "descuentos": descuentos,
        "cambios": historial.resumen_cambios(hist),
        "caros": caros,
        "destacado": destacado,
        "calidad": calidad or {},
        "formatear_cop": formatear_cop,
        "version": __version__,
    }


def construir_html(df, hist=None, calidad=None, entorno="GitHub Pages"):
    """Devuelve el HTML del reporte estático con todas las métricas."""
    datos = contexto(df, hist, calidad)
    datos["entorno"] = entorno
    ordenado = df.sort_values("precio_cop", ascending=False)
    datos["productos"] = ordenado.to_dict("records")
    return _entorno_plantillas.get_template("reporte.html").render(**datos)
