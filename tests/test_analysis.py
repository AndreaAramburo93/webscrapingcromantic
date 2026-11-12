"""Pruebas del análisis descriptivo y del reporte HTML."""

from pathlib import Path

from cromantic_scraper import analysis, report, scraper
from cromantic_scraper.__main__ import cargar_csv

FIXTURES = Path(__file__).parent / "fixtures"


def productos_ejemplo():
    html = (FIXTURES / "capilar_pagina1.html").read_text(encoding="utf-8")
    return scraper.parse_productos(html, "Capilar")


def test_dataframe_elimina_sku_repetidos():
    datos = productos_ejemplo() + productos_ejemplo()
    assert len(analysis.a_dataframe(datos)) == 3


def test_resumen_de_precios():
    df = analysis.a_dataframe(productos_ejemplo())
    r = analysis.resumen_precios(df)
    assert r["productos"] == 3
    assert r["minimo"] == 44990
    assert r["maximo"] == 165990
    assert r["mediana"] == 49900


def test_resumen_vacio_no_falla():
    df = analysis.a_dataframe([])
    assert analysis.resumen_precios(df)["productos"] == 0


def test_marca_mas_cara_primero():
    df = analysis.a_dataframe(productos_ejemplo())
    assert analysis.por_marca(df).iloc[0]["marca"] == "Olaplex"


def test_reporte_html_contiene_datos_y_escapa_texto():
    datos = productos_ejemplo()
    datos[0]["nombre"] = "<script>alert(1)</script>"
    pagina = report.construir_html(analysis.a_dataframe(datos))
    assert "$165.990" in pagina
    assert "<script>alert(1)</script>" not in pagina


def test_lee_csv_del_notebook_original(tmp_path):
    ruta = tmp_path / "viejo.csv"
    ruta.write_text(
        "Referencia (SKU);Nombre/Marca;Valor (COP);Valor;Características\n"
        "11030;[Olaplex] Kit Olaplex Hair Hydration Heroes;165990.0;"
        "$165.990;Capilar, Belleza\n",
        encoding="utf-8-sig",
    )
    df = cargar_csv(ruta)
    assert df.loc[0, "marca"] == "Olaplex"
    assert df.loc[0, "precio_cop"] == 165990.0


def test_reporte_estatico_incluye_tops_y_destacado():
    from cromantic_scraper.historial import COLUMNAS
    import pandas as pd
    df = analysis.a_dataframe(productos_ejemplo())
    hist = pd.DataFrame([
        ("2026-11-06", "10996", "Anyeluz", "Tónico Romero Anyeluz 110ml", 17996),
        ("2026-11-09", "10996", "Anyeluz", "Tónico Romero Anyeluz 110ml", 44990),
    ], columns=COLUMNAS)
    pagina = report.construir_html(df, hist)
    assert "Top 5 productos más caros" in pagina
    assert "Top 10 productos con más descuento" in pagina
    assert "Producto destacado" in pagina
    assert "/producto/" not in pagina   # el reporte estático no tiene esas rutas
