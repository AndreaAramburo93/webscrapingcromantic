"""Aplicación web de precios capilares de Cromantic (Flask).

Rutas:
    /                 página con indicadores, filtros y catálogo
    /api/productos    productos en JSON (filtros: marca, q, orden)
    /api/resumen      estadísticas de precio y tabla por marca en JSON
    /health           estado del servicio, usado por Render y la prueba de humo

Variables de entorno:
    DATA_PATH   ruta del CSV (por defecto data/productos_cromantic.csv)
    ENTORNO     nombre del entorno que se muestra en la página
"""

import json
import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from . import __version__, historial
from .__main__ import cargar_csv
from .analysis import mas_caros, por_marca, resumen_precios
from .scraper import formatear_cop

ORDENES = {
    "precio_desc": ("precio_cop", False),
    "precio_asc": ("precio_cop", True),
    "nombre": ("nombre", True),
}


def crear_app(ruta_datos=None):
    app = Flask(__name__)
    ruta = Path(ruta_datos or os.environ.get(
        "DATA_PATH", "data/productos_cromantic.csv"))
    ruta_calidad = ruta.with_name("calidad_datos.json")
    ruta_historial = ruta.with_name("historial_precios.csv")
    cache = {"mtime": None, "df": None}
    cache_hist = {"mtime": None, "df": None}

    def cargar():
        """Lee el CSV y lo guarda en memoria hasta que el archivo cambie."""
        if not ruta.exists():
            return None
        mtime = ruta.stat().st_mtime
        if cache["mtime"] != mtime:
            cache["df"] = cargar_csv(ruta)
            cache["mtime"] = mtime
        return cache["df"]

    def cargar_historial():
        mtime = ruta_historial.stat().st_mtime if ruta_historial.exists() else None
        if cache_hist["mtime"] != mtime or cache_hist["df"] is None:
            cache_hist["df"] = historial.cargar(ruta_historial)
            cache_hist["mtime"] = mtime
        return cache_hist["df"]

    def calidad():
        if ruta_calidad.exists():
            return json.loads(ruta_calidad.read_text(encoding="utf-8"))
        return {}

    def filtrar(df):
        marca = request.args.get("marca", "").strip()
        texto = request.args.get("q", "").strip()
        orden = request.args.get("orden", "precio_desc")
        if marca:
            df = df[df["marca"] == marca]
        if texto:
            df = df[df["nombre"].str.contains(texto, case=False, na=False,
                                              regex=False)]
        columna, ascendente = ORDENES.get(orden, ORDENES["precio_desc"])
        return df.sort_values(columna, ascending=ascendente), marca, texto, orden

    @app.get("/")
    def inicio():
        df = cargar()
        if df is None or df.empty:
            return render_template("sin_datos.html"), 503
        filtrado, marca, texto, orden = filtrar(df)
        r = resumen_precios(df)
        hist = cargar_historial()
        return render_template(
            "index.html",
            productos=filtrado.to_dict("records"),
            total=len(df),
            resumen={k: formatear_cop(v) if k != "productos" else v
                     for k, v in r.items()},
            marcas=por_marca(df).to_dict("records"),
            lista_marcas=sorted(df["marca"].dropna().unique()),
            marca=marca, texto=texto, orden=orden,
            calidad=calidad(),
            caros=mas_caros(df, 5).to_dict("records"),
            descuentos=historial.top_descuentos(hist, 10),
            cambios=historial.resumen_cambios(hist),
            entorno=os.environ.get("ENTORNO", "local"),
            version=__version__,
            formatear_cop=formatear_cop,
        )

    @app.get("/api/productos")
    def api_productos():
        df = cargar()
        if df is None:
            return jsonify(error="sin datos"), 503
        filtrado, *_ = filtrar(df)
        columnas = ["sku", "marca", "nombre", "precio_cop", "precio_texto"]
        return jsonify(total=len(filtrado),
                       productos=filtrado[columnas].to_dict("records"))

    @app.get("/api/resumen")
    def api_resumen():
        df = cargar()
        if df is None:
            return jsonify(error="sin datos"), 503
        return jsonify(resumen=resumen_precios(df),
                       por_marca=por_marca(df).to_dict("records"),
                       calidad=calidad())

    @app.get("/api/descuentos")
    def api_descuentos():
        hist = cargar_historial()
        return jsonify(resumen=historial.resumen_cambios(hist),
                       top_descuentos=historial.top_descuentos(hist, 10))

    @app.get("/health")
    def health():
        df = cargar()
        productos = 0 if df is None else int(len(df))
        estado = 200 if productos else 503
        # Render define RENDER_GIT_COMMIT con el commit desplegado
        commit = os.environ.get("RENDER_GIT_COMMIT", "")[:7] or "desconocido"
        return jsonify(status="ok" if productos else "sin datos",
                       productos=productos, version=__version__,
                       commit=commit), estado

    return app


app = crear_app()
