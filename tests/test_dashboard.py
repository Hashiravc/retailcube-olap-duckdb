"""Pruebas del dashboard y componentes de Streamlit."""

import pytest
from src.olap.olap_engine import get_olap_engine


def test_dashboard_engine_kpis():
    """Valida que el motor responda correctamente a las solicitudes de metricas del dashboard."""
    engine = get_olap_engine()
    kpis = engine.get_kpis()
    
    assert "total_ventas_netas" in kpis
    assert "total_transacciones" in kpis
    assert "ticket_promedio" in kpis
    assert kpis["total_ventas_netas"] > 9_000_000.0
    assert kpis["total_transacciones"] > 20_000


def test_dashboard_filter_dimension_values():
    """Valida que los selectores de dimensiones devuelvan listas validas y no vacias."""
    engine = get_olap_engine()
    paises = engine.get_dimension_values("pais")
    categorias = engine.get_dimension_values("categoria")
    regiones = engine.get_dimension_values("region")
    
    assert len(paises) >= 35
    assert "United Kingdom" in paises
    assert "Germany" in paises
    assert len(categorias) >= 5
    assert len(regiones) >= 4
