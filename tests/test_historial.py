"""Pruebas del historial de precios y la detección de descuentos."""

import pandas as pd

from cromantic_scraper import historial


def productos(precios):
    return pd.DataFrame([
        {"sku": sku, "marca": "M", "nombre": f"Producto {sku}", "precio_cop": p}
        for sku, p in precios.items()
    ])


def test_agregar_crea_y_reemplaza_la_misma_fecha(tmp_path):
    ruta = tmp_path / "hist.csv"
    historial.agregar(productos({"1": 100}), ruta, "2026-11-06")
    historial.agregar(productos({"1": 90}), ruta, "2026-11-06")
    hist = historial.cargar(ruta)
    assert len(hist) == 1
    assert hist.loc[0, "precio_cop"] == 90


def test_cargar_sin_archivo_devuelve_vacio(tmp_path):
    assert historial.cargar(tmp_path / "no.csv").empty
    assert historial.top_descuentos(historial.cargar(tmp_path / "no.csv")) == []


def test_una_sola_fecha_no_tiene_cambios(tmp_path):
    ruta = tmp_path / "hist.csv"
    hist = historial.agregar(productos({"1": 100}), ruta, "2026-11-06")
    assert historial.resumen_cambios(hist)["comparados"] == 0


def test_detecta_promocion_activa_y_terminada(tmp_path):
    ruta = tmp_path / "hist.csv"
    antes = productos({"1": 100, "2": 40, "3": 50, "4": 10})
    historial.agregar(antes, ruta, "2026-11-06")
    hist = historial.agregar(productos({"1": 60, "2": 100, "3": 50, "5": 20}), ruta,
                             "2026-11-09")
    r = historial.resumen_cambios(hist)
    assert (r["comparados"], r["bajaron"], r["subieron"]) == (3, 1, 1)
    top = historial.top_descuentos(hist)
    assert [d["sku"] for d in top] == ["2", "1"]
    assert top[0]["descuento_pct"] == 60.0
    assert top[0]["estado"] == "terminada"
    assert top[1]["estado"] == "activa"
    assert top[1]["precio_normal_texto"] == "$100"


def test_compara_solo_las_dos_ultimas_fechas(tmp_path):
    ruta = tmp_path / "hist.csv"
    historial.agregar(productos({"1": 10}), ruta, "2026-11-01")
    historial.agregar(productos({"1": 100}), ruta, "2026-11-06")
    hist = historial.agregar(productos({"1": 100}), ruta, "2026-11-09")
    assert historial.top_descuentos(hist) == []


def test_desempata_por_ahorro(tmp_path):
    ruta = tmp_path / "hist.csv"
    historial.agregar(productos({"a": 50, "b": 500}), ruta, "2026-11-06")
    hist = historial.agregar(productos({"a": 100, "b": 1000}), ruta, "2026-11-09")
    assert [d["sku"] for d in historial.top_descuentos(hist)] == ["b", "a"]
