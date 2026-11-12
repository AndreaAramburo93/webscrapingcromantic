"""Pruebas de la validación y limpieza de datos."""

import pandas as pd

from cromantic_scraper.limpieza import limpiar


def datos_sucios():
    filas = [
        # sku, marca, nombre, precio
        ("1", " Olaplex ", "Kit Olaplex", 165990),
        ("1", "Olaplex", "Kit repetido", 165990),
        (None, "Anyeluz", "Sin SKU", 44990),
        ("No disponible", "X", "SKU vacío", 1000),
        ("2", "Anyeluz", "  ", 44990),
        ("3", "Revox", "Precio texto", "consultar"),
        ("4", "Revox", "Precio cero", 0),
        ("5", "", "Sin marca", "49900"),
    ]
    return pd.DataFrame(filas, columns=["sku", "marca", "nombre", "precio_cop"])


def test_cuenta_cada_tipo_de_problema():
    _, reporte = limpiar(datos_sucios())
    assert reporte["filas_entrada"] == 8
    assert reporte["sin_sku"] == 2
    assert reporte["sin_nombre"] == 1
    assert reporte["precio_invalido"] == 2
    assert reporte["duplicados"] == 1
    assert reporte["filas_salida"] == 2
    assert reporte["filas_descartadas"] == 6


def test_quita_espacios_y_completa_marca():
    df, reporte = limpiar(datos_sucios())
    assert df.loc[0, "marca"] == "Olaplex"
    assert df.loc[1, "marca"] == "Cromantic"
    assert reporte["marca_completada"] == 1


def test_precio_queda_numerico_y_con_texto():
    df, _ = limpiar(datos_sucios())
    assert df["precio_cop"].tolist() == [165990.0, 49900.0]
    assert df["precio_texto"].tolist() == ["$165.990", "$49.900"]


def test_no_modifica_el_original():
    original = datos_sucios()
    limpiar(original)
    assert len(original) == 8


def test_agrega_columnas_faltantes():
    df, _ = limpiar(pd.DataFrame([{"sku": "9", "nombre": "Solo", "precio_cop": 10}]))
    assert list(df.columns) == ["sku", "marca", "nombre", "precio_cop",
                                "precio_texto", "categoria"]
