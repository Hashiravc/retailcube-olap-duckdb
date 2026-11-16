"""Pruebas de integridad referencial y diseno del Esquema Estrella."""

import duckdb
import pandas as pd
import pytest
from pathlib import Path

from src.olap.olap_engine import get_olap_engine, PROCESSED_DIR


@pytest.fixture(scope="module")
def engine():
    return get_olap_engine()


def test_dimensional_tables_exist(engine):
    """Valida la presencia de las 4 dimensiones y la tabla de hechos en DuckDB."""
    tables_df, _ = engine.execute_query("SHOW TABLES;")
    table_names = set(tables_df["name"].tolist())
    
    expected_tables = {"dim_fecha", "dim_producto", "dim_cliente", "dim_pais", "fact_ventas"}
    assert expected_tables.issubset(table_names), f"Faltan tablas en DuckDB: {expected_tables - table_names}"


def test_primary_keys_uniqueness(engine):
    """Verifica que las claves primarias de cada dimension sean unicas y no nulas."""
    for table, pk in [
        ("dim_fecha", "id_fecha"),
        ("dim_producto", "id_producto"),
        ("dim_cliente", "id_cliente"),
        ("dim_pais", "id_pais"),
        ("fact_ventas", "id_venta"),
    ]:
        df, _ = engine.execute_query(f"""
            SELECT COUNT(*) AS total_rows, COUNT(DISTINCT {pk}) AS unique_pks
            FROM {table};
        """)
        assert df["total_rows"].iloc[0] == df["unique_pks"].iloc[0], f"Clave primaria duplicada en {table}.{pk}"


def test_foreign_keys_referential_integrity(engine):
    """Verifica que no existan registros huerfanos en fact_ventas hacia ninguna dimension."""
    # 1. Integridad hacia dim_fecha
    df_orphans_fecha, _ = engine.execute_query("""
        SELECT COUNT(*) AS count
        FROM fact_ventas v
        LEFT JOIN dim_fecha f ON v.id_fecha = f.id_fecha
        WHERE f.id_fecha IS NULL;
    """)
    assert df_orphans_fecha["count"].iloc[0] == 0, "Registros huerfanos detectados hacia dim_fecha"

    # 2. Integridad hacia dim_producto
    df_orphans_prod, _ = engine.execute_query("""
        SELECT COUNT(*) AS count
        FROM fact_ventas v
        LEFT JOIN dim_producto p ON v.id_producto = p.id_producto
        WHERE p.id_producto IS NULL;
    """)
    assert df_orphans_prod["count"].iloc[0] == 0, "Registros huerfanos detectados hacia dim_producto"

    # 3. Integridad hacia dim_cliente
    df_orphans_cust, _ = engine.execute_query("""
        SELECT COUNT(*) AS count
        FROM fact_ventas v
        LEFT JOIN dim_cliente c ON v.id_cliente = c.id_cliente
        WHERE c.id_cliente IS NULL;
    """)
    assert df_orphans_cust["count"].iloc[0] == 0, "Registros huerfanos detectados hacia dim_cliente"

    # 4. Integridad hacia dim_pais
    df_orphans_pais, _ = engine.execute_query("""
        SELECT COUNT(*) AS count
        FROM fact_ventas v
        LEFT JOIN dim_pais p ON v.id_pais = p.id_pais
        WHERE p.id_pais IS NULL;
    """)
    assert df_orphans_pais["count"].iloc[0] == 0, "Registros huerfanos detectados hacia dim_pais"


def test_revenue_conservation_and_cancel_consistency(engine):
    """Valida la consistencia matematica entre ventas brutas, devoluciones y ventas netas."""
    df, _ = engine.execute_query("""
        SELECT
            ROUND(SUM(monto_total), 2) AS net,
            ROUND(SUM(monto_bruto), 2) AS gross,
            ROUND(SUM(monto_cancelacion), 2) AS cancel,
            ROUND(SUM(monto_bruto) - SUM(monto_cancelacion), 2) AS calculated_net
        FROM fact_ventas;
    """)
    net = df["net"].iloc[0]
    gross = df["gross"].iloc[0]
    cancel = df["cancel"].iloc[0]
    calc_net = df["calculated_net"].iloc[0]

    assert abs(net - calc_net) < 0.05, f"Inconsistencia en balance neto: {net} vs {calc_net}"
    assert gross > cancel, "Las ventas brutas deben superar las devoluciones"
    assert cancel > 0, "Debe registrarse el monto de cancelaciones"
