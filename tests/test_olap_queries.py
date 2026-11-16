"""Pruebas funcionales de las 7 Operaciones OLAP en DuckDB."""

import pytest
from src.olap.olap_engine import get_olap_engine


@pytest.fixture(scope="module")
def engine():
    return get_olap_engine()


def test_olap_rollup(engine):
    """Valida la operacion ROLL-UP temporal en diferentes niveles jerarquicos."""
    df_rollup, ms, sql = engine.run_rollup(hierarchy_level="mes")
    assert not df_rollup.empty, "El resultado de ROLLUP no debe estar vacio"
    assert "ventas_netas" in df_rollup.columns
    assert "total_transacciones" in df_rollup.columns
    assert "ROLLUP" in sql.upper()
    assert ms < 3000, f"La consulta ROLLUP debe tardar menos de 3s (tardo {ms}ms)"
    
    # Validar que la ultima fila o agrupacion represente el total global
    total_row = df_rollup[df_rollup["anio"].isna()]
    if not total_row.empty:
        global_net = total_row["ventas_netas"].iloc[0]
        # Control query
        df_control, _ = engine.execute_query("SELECT ROUND(SUM(monto_total), 2) AS total FROM fact_ventas;")
        assert abs(global_net - df_control["total"].iloc[0]) < 0.05


def test_olap_drilldown(engine):
    """Valida la operacion DRILL-DOWN desglosando un periodo especifico."""
    df_drill, ms, sql = engine.run_drilldown(year=2011, quarter=4)
    assert not df_drill.empty, "El resultado de DRILL-DOWN no debe estar vacio"
    assert "nombre_mes" in df_drill.columns
    assert ms < 2000

    # Desglose a nivel de dia para un mes especifico
    df_drill_day, ms2, sql2 = engine.run_drilldown(year=2011, month=11)
    assert not df_drill_day.empty
    assert "dia" in df_drill_day.columns
    assert "nombre_dia_semana" in df_drill_day.columns


def test_olap_slice(engine):
    """Valida la operacion SLICE fijando una dimension (ej. Pais = 'Germany')."""
    df_slice, ms, sql = engine.run_slice(dimension="pais", value="Germany")
    assert not df_slice.empty, "SLICE para Germany no debe estar vacio"
    assert (df_slice["dimension_fijada"] == "Germany").all()
    assert "ventas_netas" in df_slice.columns

    # Validar contra consulta de control directa
    df_control, _ = engine.execute_query("""
        SELECT ROUND(SUM(v.monto_total), 2) AS total
        FROM fact_ventas v
        JOIN dim_pais p ON v.id_pais = p.id_pais
        WHERE p.nombre_pais = 'Germany';
    """)
    sum_slice = round(df_slice["ventas_netas"].sum(), 2)
    assert abs(sum_slice - df_control["total"].iloc[0]) < 0.05


def test_olap_dice(engine):
    """Valida la operacion DICE aplicando filtros simultaneos sobre paises, categorias y periodos."""
    countries = ["France", "Germany"]
    categories = ["DECORACION_HOGAR", "MENAJE_COCINA"]
    quarters = [3, 4]
    
    df_dice, ms, sql = engine.run_dice(
        countries=countries,
        categories=categories,
        year=2011,
        quarters=quarters,
    )
    assert not df_dice.empty, "DICE no debe retornar conjunto vacio para estos filtros"
    assert set(df_dice["nombre_pais"].unique()).issubset(set(countries))
    assert set(df_dice["categoria"].unique()).issubset(set(categories))


def test_olap_pivot(engine):
    """Valida la operacion PIVOT nativa en DuckDB cruzando paises y trimestres."""
    df_pivot, ms, sql = engine.run_pivot(top_countries=5)
    assert not df_pivot.empty
    assert "nombre_pais" in df_pivot.columns
    # Debe tener columnas para trimestres generados dinamicamente
    quarter_cols = [c for c in df_pivot.columns if "-" in c]
    assert len(quarter_cols) >= 3, "Debe tener al menos 3 periodos pivotados"


def test_olap_cube(engine):
    """Valida la operacion CUBE con GROUP BY CUBE sobre Region, Categoria y Anio."""
    df_cube, ms, sql = engine.run_cube(selected_regions=["Reino Unido", "Europa Occidental"])
    assert not df_cube.empty
    assert "CUBE" in sql.upper()
    # Debe contener filas con subtotales (identificables por el texto comodin)
    has_subtotals = (df_cube["region"].str.contains("TODAS") | df_cube["categoria"].str.contains("TODAS")).any()
    assert has_subtotals, "CUBE debe generar filas de subtotales combinados"


def test_olap_grouping_sets(engine):
    """Valida la operacion GROUP BY GROUPING SETS sobre agrupaciones selectivas."""
    df_gs, ms, sql = engine.run_grouping_sets(top_countries=["United Kingdom", "Germany", "France"])
    assert not df_gs.empty
    assert "GROUPING SETS" in sql.upper()
    assert "grp_pais" in df_gs.columns
    assert "grp_categoria" in df_gs.columns
    assert "grp_periodo" in df_gs.columns
