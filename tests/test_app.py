"""Pruebas de la aplicación web con el cliente de pruebas de Flask."""

import json

import pytest

from cromantic_scraper.app import crear_app

CSV = (
    "sku;marca;nombre;precio_cop;precio_texto;categoria\n"
    "11030;Olaplex;Kit Olaplex Hair Hydration Heroes;165990;$165.990;Capilar\n"
    "11015;Everyday Love;Shampoo Everyday Love Miracle;49900;$49.900;Capilar\n"
    "10996;Anyeluz;Tónico Romero Anyeluz;44990;$44.990;Capilar\n"
    "10997;Anyeluz;<script>alert(1)</script>;49990;$49.990;Capilar\n"
)


@pytest.fixture
def cliente(tmp_path):
    ruta = tmp_path / "productos.csv"
    ruta.write_text(CSV, encoding="utf-8-sig")
    (tmp_path / "calidad_datos.json").write_text(json.dumps(
        {"filas_entrada": 5, "sin_sku": 0, "sin_nombre": 0, "precio_invalido": 1,
         "duplicados": 0, "filas_salida": 4, "origen": "scraping",
         "fecha_utc": "2026-11-16 12:00"}))
    (tmp_path / "historial_precios.csv").write_text(
        "fecha;sku;marca;nombre;precio_cop\n"
        "2026-11-06;11030;Olaplex;Kit Olaplex Hair Hydration Heroes;165990\n"
        "2026-11-06;10996;Anyeluz;Tónico Romero Anyeluz;17996\n"
        "2026-11-09;11030;Olaplex;Kit Olaplex Hair Hydration Heroes;149391\n"
        "2026-11-09;10996;Anyeluz;Tónico Romero Anyeluz;44990\n",
        encoding="utf-8-sig")
    return crear_app(ruta).test_client()


@pytest.fixture
def cliente_sin_datos(tmp_path):
    return crear_app(tmp_path / "no_existe.csv").test_client()


def test_health_ok_con_datos(cliente):
    r = cliente.get("/health")
    assert r.status_code == 200
    assert r.get_json()["productos"] == 4


def test_health_informa_commit(cliente, monkeypatch):
    assert cliente.get("/health").get_json()["commit"] == "desconocido"
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abc1234def5678")
    assert cliente.get("/health").get_json()["commit"] == "abc1234"


def test_health_503_sin_datos(cliente_sin_datos):
    assert cliente_sin_datos.get("/health").status_code == 503
    assert cliente_sin_datos.get("/").status_code == 503


def test_pagina_muestra_indicadores(cliente):
    html = cliente.get("/").get_data(as_text=True)
    assert "Precios capilares en Cromantic" in html
    assert "$165.990" in html
    assert "Calidad de los datos" in html


def test_pagina_escapa_texto_peligroso(cliente):
    html = cliente.get("/").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_filtro_por_marca(cliente):
    datos = cliente.get("/api/productos?marca=Anyeluz").get_json()
    assert datos["total"] == 2
    assert {p["marca"] for p in datos["productos"]} == {"Anyeluz"}


def test_busqueda_por_texto_y_orden(cliente):
    datos = cliente.get("/api/productos?q=anyeluz&orden=precio_asc").get_json()
    assert [p["sku"] for p in datos["productos"]] == ["10996"]


def test_orden_por_defecto_mayor_precio(cliente):
    datos = cliente.get("/api/productos").get_json()
    assert datos["productos"][0]["sku"] == "11030"


def test_api_resumen(cliente):
    datos = cliente.get("/api/resumen").get_json()
    assert datos["resumen"]["maximo"] == 165990
    assert datos["por_marca"][0]["marca"] == "Olaplex"
    assert datos["calidad"]["filas_salida"] == 4


def test_pagina_muestra_tops(cliente):
    html = cliente.get("/").get_data(as_text=True)
    assert "Top 5 productos más caros" in html
    assert "Top 10 productos con más descuento" in html
    assert "60 %" in html
    assert "Terminó" in html and "Activa" in html


def test_api_descuentos(cliente):
    datos = cliente.get("/api/descuentos").get_json()
    assert datos["resumen"]["bajaron"] == 1
    assert datos["resumen"]["subieron"] == 1
    assert datos["top_descuentos"][0]["sku"] == "10996"


def test_sin_historial_muestra_aviso(tmp_path):
    ruta = tmp_path / "productos.csv"
    ruta.write_text(CSV, encoding="utf-8-sig")
    html = crear_app(ruta).test_client().get("/").get_data(as_text=True)
    assert "al menos dos extracciones" in html
