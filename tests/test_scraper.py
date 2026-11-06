"""Pruebas unitarias del scraper. No hacen peticiones reales a internet."""

from pathlib import Path

import pytest

from cromantic_scraper import scraper

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def html_capilar():
    return (FIXTURES / "capilar_pagina1.html").read_text(encoding="utf-8")


def test_parse_lee_los_tres_productos_del_itemlist(html_capilar):
    productos = scraper.parse_productos(html_capilar, "Capilar")
    assert [p["sku"] for p in productos] == ["11030", "11015", "10996"]


def test_parse_ignora_json_invalido_y_tipos_ajenos(html_capilar):
    # El fixture trae un bloque Organization y uno roto: no deben romper nada
    productos = scraper.parse_productos(html_capilar)
    assert len(productos) == 3


def test_marca_como_dict_y_como_texto(html_capilar):
    marcas = [p["marca"] for p in scraper.parse_productos(html_capilar)]
    assert marcas == ["Olaplex", "Everyday Love", "Anyeluz"]


def test_marca_por_defecto_cuando_falta():
    assert scraper.obtener_marca({}) == "Cromantic"
    assert scraper.obtener_marca({"brand": "  "}) == "Cromantic"


def test_precio_numerico_desde_offer_y_aggregateoffer(html_capilar):
    precios = [p["precio_cop"] for p in scraper.parse_productos(html_capilar)]
    assert precios == [165990.0, 49900.0, 44990.0]


def test_precio_invalido_devuelve_none():
    assert scraper.obtener_precio({"offers": {"price": "consultar"}}) is None
    assert scraper.obtener_precio({}) is None


def test_formato_pesos_colombianos():
    assert scraper.formatear_cop(1499900.0) == "$1.499.900"
    assert scraper.formatear_cop(None) == "No disponible"


def test_corrige_entidades_html(html_capilar):
    nombres = [p["nombre"] for p in scraper.parse_productos(html_capilar)]
    assert "Tónico Romero Anyeluz 110ml" in nombres


def test_paginacion_se_detiene_si_la_pagina_se_repite(html_capilar):
    """Reproduce el error del notebook: 12 páginas que devuelven lo mismo."""
    urls = []

    def falso_get(url):
        urls.append(url)
        return html_capilar

    productos = scraper.scrape_paginado(paginas=12, pausa=0,
                                        obtener_html=falso_get)
    assert len(productos) == 3
    assert len(urls) == 2  # la página 2 no trae nada nuevo y corta


def test_paginacion_salta_paginas_caidas(html_capilar):
    respuestas = iter([None, html_capilar, None])

    productos = scraper.scrape_paginado(
        paginas=3, pausa=0, obtener_html=lambda url: next(respuestas))
    assert len(productos) == 3
