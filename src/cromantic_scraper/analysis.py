"""Análisis descriptivo de los productos extraídos."""

import pandas as pd

COLUMNAS = ["sku", "marca", "nombre", "precio_cop", "precio_texto",
            "categoria"]


def a_dataframe(productos):
    """Convierte la lista de productos en DataFrame sin SKU repetidos."""
    df = pd.DataFrame(productos, columns=COLUMNAS)
    return df.drop_duplicates(subset=["sku"]).reset_index(drop=True)


def resumen_precios(df):
    """Estadísticas básicas de precio (COP), ignorando precios vacíos."""
    precios = df["precio_cop"].dropna()
    if precios.empty:
        return {"productos": 0, "promedio": None, "mediana": None,
                "minimo": None, "maximo": None}
    return {
        "productos": int(precios.count()),
        "promedio": round(float(precios.mean())),
        "mediana": round(float(precios.median())),
        "minimo": round(float(precios.min())),
        "maximo": round(float(precios.max())),
    }


def por_marca(df):
    """Cantidad de productos y precio promedio por marca."""
    tabla = (
        df.groupby("marca")["precio_cop"]
        .agg(productos="count", precio_promedio="mean")
        .sort_values("precio_promedio", ascending=False)
        .round(0)
        .reset_index()
    )
    return tabla


def mas_caros(df, n=5):
    """Los n productos de mayor precio."""
    return df.nlargest(n, "precio_cop")[["marca", "nombre", "precio_texto"]]
