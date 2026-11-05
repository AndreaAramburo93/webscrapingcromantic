"""Punto de entrada: python -m cromantic_scraper

Ejecuta el scraping, guarda el CSV y genera la página del reporte.
Si el sitio no responde (por ejemplo, bloquea la IP del runner de GitHub),
usa como respaldo el último CSV guardado en el repositorio, para que el
despliegue no publique una página vacía.
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from .analysis import a_dataframe
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
    parser.add_argument("--paginas", type=int, default=12)
    parser.add_argument("--csv", default="data/productos_cromantic.csv")
    parser.add_argument("--salida", default="site/index.html")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    log = logging.getLogger("cromantic")

    ruta_csv = Path(args.csv)
    productos = scrape_paginado(paginas=args.paginas)

    if productos:
        df = a_dataframe(productos)
        ruta_csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(ruta_csv, index=False, encoding="utf-8-sig", sep=";")
        log.info("Guardados %s productos en %s", len(df), ruta_csv)
    elif ruta_csv.exists():
        log.warning("Sin datos nuevos; se usa el CSV existente %s", ruta_csv)
        df = cargar_csv(ruta_csv)
    else:
        log.error("No hay datos para publicar.")
        return 1

    ruta_html = Path(args.salida)
    ruta_html.parent.mkdir(parents=True, exist_ok=True)
    ruta_html.write_text(construir_html(df), encoding="utf-8")
    log.info("Reporte generado en %s", ruta_html)
    return 0


if __name__ == "__main__":
    sys.exit(main())
