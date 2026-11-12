"""Punto de entrada: python -m cromantic_scraper

Ejecuta el scraping, valida y limpia los datos, guarda el CSV y el reporte de
calidad, y genera la página estática del reporte.
Si el sitio no responde (por ejemplo, bloquea la IP del runner de GitHub),
usa como respaldo el último CSV guardado en el repositorio, para que el
despliegue no publique una página vacía.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from . import historial
from .analysis import a_dataframe
from .limpieza import limpiar
from .report import construir_html
from .scraper import scrape_paginado


def cargar_csv(ruta):
    """Lee el CSV del proyecto o el que exportaba el notebook de Colab."""
    df = pd.read_csv(ruta, sep=";", encoding="utf-8-sig", dtype=str)
    if "Referencia (SKU)" in df.columns:  # formato del notebook original
        partes = df["Nombre/Marca"].str.extract(r"^\[(.*?)\]\s*(.*)$")
        df = pd.DataFrame({
            "sku": df["Referencia (SKU)"],
            "marca": partes[0],
            "nombre": partes[1],
            "precio_cop": df["Valor (COP)"],
            "precio_texto": df["Valor"],
            "categoria": df["Características"],
        })
    df["precio_cop"] = pd.to_numeric(df["precio_cop"], errors="coerce")
    return df


def main(argv=None):
    parser = argparse.ArgumentParser(description="Scraper capilar Cromantic")
    # SCRAPER_PAGINAS llega como variable de entorno desde GitHub Actions
    parser.add_argument("--paginas", type=int,
                        default=int(os.environ.get("SCRAPER_PAGINAS", 12)))
    parser.add_argument("--csv", default="data/productos_cromantic.csv")
    parser.add_argument("--calidad", default="data/calidad_datos.json")
    parser.add_argument("--historial", default="data/historial_precios.csv")
    parser.add_argument("--salida", default="site/index.html")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    log = logging.getLogger("cromantic")

    ruta_csv = Path(args.csv)
    productos = scrape_paginado(paginas=args.paginas)

    if productos:
        origen = "scraping"
        df = a_dataframe(productos)
    elif ruta_csv.exists():
        origen = "respaldo"
        log.warning("Sin datos nuevos; se usa el CSV existente %s", ruta_csv)
        df = cargar_csv(ruta_csv)
    else:
        log.error("No hay datos para publicar.")
        return 1

    df, reporte = limpiar(df)
    log.info("Calidad de datos: %s", reporte)
    if df.empty:
        log.error("Ninguna fila pasó la validación.")
        return 1

    ruta_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta_csv, index=False, encoding="utf-8-sig", sep=";")
    reporte.update({
        "origen": origen,
        "fecha_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
    })
    Path(args.calidad).write_text(json.dumps(reporte, indent=2), encoding="utf-8")
    log.info("Guardados %s productos en %s", len(df), ruta_csv)

    if origen == "scraping":  # el respaldo no es una medición nueva
        hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        historial.agregar(df, args.historial, hoy)
        log.info("Historial actualizado en %s (%s)", args.historial, hoy)

    ruta_html = Path(args.salida)
    ruta_html.parent.mkdir(parents=True, exist_ok=True)
    ruta_html.write_text(construir_html(df), encoding="utf-8")
    log.info("Reporte generado en %s", ruta_html)
    return 0


if __name__ == "__main__":
    sys.exit(main())
