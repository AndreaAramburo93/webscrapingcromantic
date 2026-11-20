"""Pruebas del análisis descriptivo de un producto."""

import pandas as pd

from cromantic_scraper.perfil import perfil_producto, tipo_de


def catalogo():
    filas = [
        ("1", "Marca A", "Cepillo Roller grande", 29990),
        ("2", "Marca A", "Cepillo Roller pequeño", 24990),
        ("3", "Marca A", "Scrunchie gris", 12990),
        ("4", "Marca B", "Shampoo reparador", 49990),
        ("5", "Marca B", "Kit de lujo", 199990),
    ]
    return pd.DataFrame(filas, columns=["sku", "marca", "nombre", "precio_cop"])


def historial_dos_fechas():
    filas = [
        ("2026-11-06", "1", "Marca A", "Cepillo Roller grande", 11996),
        ("2026-11-09", "1", "Marca A", "Cepillo Roller grande", 29990),
    ]
    columnas = ["fecha", "sku", "marca", "nombre", "precio_cop"]
    return pd.DataFrame(filas, columns=columnas)


def test_tipo_es_la_primera_palabra():
    assert tipo_de("cepillo Wet Brush") == "Cepillo"
    assert tipo_de("") == "Otro"


def test_producto_inexistente_devuelve_none():
    assert perfil_producto(catalogo(), None, "999") is None


def test_ubica_el_producto_en_catalogo_marca_y_tipo():
    p = perfil_producto(catalogo(), historial_dos_fechas(), "1")
    assert p["precio_texto"] == "$29.990"
    assert p["percentil"] == 40          # más caro que 2 de 5 productos
    assert p["puesto_marca"] == 1
    assert p["marca_productos"] == 3
    assert p["tipo"] == "Cepillo"
    assert p["tipo_productos"] == 2


def test_frases_describen_historial_y_promocion_terminada():
    p = perfil_producto(catalogo(), historial_dos_fechas(), "1")
    texto = " ".join(p["frases"])
    assert "una diferencia del 60 %" in texto
    assert "más alto registrado" in texto
    assert len(p["historial"]) == 2


def test_sin_historial_lo_explica():
    p = perfil_producto(catalogo(), None, "5")
    assert any("suficientes extracciones" in f for f in p["frases"])
    assert any("único producto de tipo «Kit»" in f for f in p["frases"])
