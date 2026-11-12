"""Prueba de punta a punta del pipeline: scraping → limpieza → historial → HTML."""

import json

from cromantic_scraper import __main__ as principal
from cromantic_scraper.historial import cargar


def productos(precio_tonico):
    return [
        {"sku": "11030", "marca": "Olaplex", "nombre": "Kit Olaplex Hair Heroes",
         "precio_cop": 165990.0, "precio_texto": "$165.990", "categoria": "Capilar"},
        {"sku": "10996", "marca": "Anyeluz", "nombre": "Tónico Romero Anyeluz",
         "precio_cop": precio_tonico, "precio_texto": "", "categoria": "Capilar"},
        {"sku": "", "marca": "X", "nombre": "Fila sin SKU",
         "precio_cop": 1000.0, "precio_texto": "", "categoria": "Capilar"},
    ]


def ejecutar(tmp_path, monkeypatch, datos, fecha):
    monkeypatch.setattr(principal, "scrape_paginado", lambda paginas: datos)

    class Reloj:
        @staticmethod
        def now(tz=None):
            from datetime import datetime
            return datetime.fromisoformat(fecha + "T12:00:00+00:00")

    monkeypatch.setattr(principal, "datetime", Reloj)
    return principal.main([
        "--csv", str(tmp_path / "productos.csv"),
        "--calidad", str(tmp_path / "calidad.json"),
        "--historial", str(tmp_path / "historial.csv"),
        "--salida", str(tmp_path / "site" / "index.html"),
    ])


def test_pipeline_genera_reporte_con_metricas(tmp_path, monkeypatch):
    assert ejecutar(tmp_path, monkeypatch, productos(17996.0), "2026-11-06") == 0
    assert ejecutar(tmp_path, monkeypatch, productos(44990.0), "2026-11-09") == 0

    calidad = json.loads((tmp_path / "calidad.json").read_text())
    assert calidad["sin_sku"] == 1 and calidad["filas_salida"] == 2

    hist = cargar(tmp_path / "historial.csv")
    assert sorted(hist["fecha"].unique()) == ["2026-11-06", "2026-11-09"]

    html = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    assert "Top 10 productos con más descuento" in html
    assert "Tónico Romero Anyeluz" in html
    assert "Producto destacado" in html


def test_sin_datos_ni_respaldo_termina_con_error(tmp_path, monkeypatch):
    assert ejecutar(tmp_path, monkeypatch, [], "2026-11-06") == 1
