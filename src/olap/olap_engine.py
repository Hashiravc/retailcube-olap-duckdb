"""Motor analitico OLAP con DuckDB para RetailCube Analytics.

Gestiona conexiones eficientes, ejecucion de operaciones multidimensionales
(ROLL-UP, DRILL-DOWN, SLICE, DICE, PIVOT, CUBE, GROUPING SETS) y optimizacion
de consultas sobre Parquet y DuckDB.
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import duckdb
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("RetailCube.OLAPEngine")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
DUCKDB_FILE = PROCESSED_DIR / "retailcube.duckdb"
QUERIES_DIR = BASE_DIR / "sql" / "queries"


class OLAPEngine:
    """Motor de analisis OLAP que encapsula consultas SQL analiticas en DuckDB."""

    _instance: Optional["OLAPEngine"] = None

    def __init__(self, db_path: Optional[Path] = None, use_parquet_views: bool = False):
        self.db_path = db_path or DUCKDB_FILE
        self.use_parquet_views = use_parquet_views
        self.conn = self._init_connection()

    def _init_connection(self) -> duckdb.DuckDBPyConnection:
        """Inicializa la conexion a DuckDB."""
        # Si existe el archivo DuckDB y no forzamos vistas Parquet, conectamos directamente en modo solo lectura
        if self.db_path.exists() and not self.use_parquet_views:
            logger.info(f"Conectando a base de datos DuckDB existente: {self.db_path}")
            conn = duckdb.connect(str(self.db_path), read_only=True)
            return conn

        # De lo contrario (ej. en despliegue SaaS ligero), conectamos en memoria y creamos vistas sobre Parquet
        logger.info("Inicializando DuckDB en memoria con vistas sobre archivos Parquet...")
        conn = duckdb.connect(":memory:")

        parquet_files = {
            "dim_fecha": PROCESSED_DIR / "dim_fecha.parquet",
            "dim_producto": PROCESSED_DIR / "dim_producto.parquet",
            "dim_cliente": PROCESSED_DIR / "dim_cliente.parquet",
            "dim_pais": PROCESSED_DIR / "dim_pais.parquet",
            "fact_ventas": PROCESSED_DIR / "fact_ventas.parquet",
        }

        for table_name, p_path in parquet_files.items():
            if not p_path.exists():
                raise FileNotFoundError(f"Archivo requerido no encontrado: {p_path}")
            # DuckDB lee directamente Parquet usando rutas normalizadas
            clean_p = str(p_path).replace("\\", "/")
            conn.execute(f"CREATE OR REPLACE VIEW {table_name} AS SELECT * FROM read_parquet('{clean_p}');")
            logger.info(f"Vista creada: {table_name} -> {clean_p}")

        return conn

    def execute_query(self, sql: str, params: Optional[List[Any]] = None) -> Tuple[pd.DataFrame, float]:
        """Ejecuta una consulta SQL y retorna un DataFrame junto con el tiempo de ejecucion en milisegundos."""
        start_time = time.perf_counter()
        try:
            if params:
                df = self.conn.execute(sql, params).df()
            else:
                df = self.conn.execute(sql).df()
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return df, round(elapsed_ms, 2)
        except Exception as e:
            logger.error(f"Error ejecutando consulta SQL: {e}\nSQL:\n{sql}")
            raise

    def get_kpis(self) -> Dict[str, Any]:
        """Retorna las metricas principales de ventas del Data Warehouse."""
        sql = """
            SELECT
                ROUND(SUM(monto_total), 2) AS total_ventas_netas,
                ROUND(SUM(monto_bruto), 2) AS total_ventas_brutas,
                ROUND(SUM(monto_cancelacion), 2) AS total_cancelaciones,
                COUNT(DISTINCT numero_factura) AS total_transacciones,
                COUNT(DISTINCT id_cliente) AS total_clientes,
                COUNT(DISTINCT id_producto) AS total_productos,
                COUNT(DISTINCT id_pais) AS total_paises,
                SUM(cantidad) AS total_unidades,
                ROUND(SUM(monto_total) / NULLIF(COUNT(DISTINCT numero_factura), 0), 2) AS ticket_promedio
            FROM fact_ventas;
        """
        df, _ = self.execute_query(sql)
        return df.iloc[0].to_dict()

    def get_dimension_values(self, dimension: str) -> List[Any]:
        """Retorna los valores distintos de una dimension para alimentar selectores UI."""
        if dimension == "pais":
            sql = "SELECT DISTINCT nombre_pais FROM dim_pais ORDER BY nombre_pais;"
            df, _ = self.execute_query(sql)
            return df["nombre_pais"].tolist()
        elif dimension == "categoria":
            sql = "SELECT DISTINCT categoria FROM dim_producto ORDER BY categoria;"
            df, _ = self.execute_query(sql)
            return df["categoria"].tolist()
        elif dimension == "region":
            sql = "SELECT DISTINCT region FROM dim_pais ORDER BY region;"
            df, _ = self.execute_query(sql)
            return df["region"].tolist()
        elif dimension == "anio":
            sql = "SELECT DISTINCT anio FROM dim_fecha ORDER BY anio;"
            df, _ = self.execute_query(sql)
            return df["anio"].tolist()
        elif dimension == "trimestre":
            sql = "SELECT DISTINCT trimestre FROM dim_fecha ORDER BY trimestre;"
            df, _ = self.execute_query(sql)
            return df["trimestre"].tolist()
        return []

    # =========================================================================
    # OPERACIONES OLAP ESPECIFICAS
    # =========================================================================

    def run_rollup(self, hierarchy_level: str = "mes") -> Tuple[pd.DataFrame, float, str]:
        """Ejecuta una operacion ROLL-UP temporal: Dia -> Mes -> Trimestre -> Anio."""
        if hierarchy_level == "anio":
            group_cols = "f.anio"
            order_cols = "f.anio NULLS LAST"
        elif hierarchy_level == "trimestre":
            group_cols = "f.anio, f.nombre_trimestre"
            order_cols = "f.anio NULLS LAST, f.nombre_trimestre NULLS LAST"
        elif hierarchy_level == "mes":
            group_cols = "f.anio, f.nombre_trimestre, f.mes, f.nombre_mes"
            order_cols = "f.anio NULLS LAST, f.mes NULLS LAST"
        else:  # dia
            group_cols = "f.anio, f.nombre_trimestre, f.mes, f.nombre_mes, f.fecha"
            order_cols = "f.anio NULLS LAST, f.mes NULLS LAST, f.fecha NULLS LAST"

        sql = f"""
            SELECT
                {group_cols},
                COUNT(DISTINCT v.numero_factura) AS total_transacciones,
                COUNT(DISTINCT v.id_cliente) AS total_clientes,
                SUM(v.cantidad) AS unidades_vendidas,
                ROUND(SUM(v.monto_total), 2) AS ventas_netas,
                ROUND(SUM(v.monto_cancelacion), 2) AS cancelaciones,
                ROUND(SUM(v.monto_total) / NULLIF(COUNT(DISTINCT v.numero_factura), 0), 2) AS ticket_promedio
            FROM fact_ventas v
            JOIN dim_fecha f ON v.id_fecha = f.id_fecha
            GROUP BY ROLLUP ({group_cols})
            ORDER BY {order_cols};
        """
        df, ms = self.execute_query(sql)
        return df, ms, sql

    def run_drilldown(self, year: int, quarter: Optional[int] = None, month: Optional[int] = None) -> Tuple[pd.DataFrame, float, str]:
        """Ejecuta una operacion DRILL-DOWN bajando de nivel jerarquico."""
        filters = [f"f.anio = {year}"]
        if quarter is not None:
            filters.append(f"f.trimestre = {quarter}")
        if month is not None:
            filters.append(f"f.mes = {month}")

        where_clause = " AND ".join(filters)

        # Si especificamos mes, bajamos a nivel dia
        if month is not None:
            select_cols = "f.anio, f.nombre_mes, f.dia, f.nombre_dia_semana, f.fecha"
            group_cols = "f.anio, f.nombre_mes, f.dia, f.nombre_dia_semana, f.fecha"
            order_cols = "f.fecha"
        elif quarter is not None:
            # Si especificamos trimestre, bajamos a nivel mes
            select_cols = "f.anio, f.nombre_trimestre, f.mes, f.nombre_mes"
            group_cols = "f.anio, f.nombre_trimestre, f.mes, f.nombre_mes"
            order_cols = "f.mes"
        else:
            # Si solo especificamos anio, bajamos a nivel trimestre
            select_cols = "f.anio, f.trimestre, f.nombre_trimestre"
            group_cols = "f.anio, f.trimestre, f.nombre_trimestre"
            order_cols = "f.trimestre"

        sql = f"""
            SELECT
                {select_cols},
                COUNT(DISTINCT v.numero_factura) AS total_transacciones,
                COUNT(DISTINCT v.id_cliente) AS total_clientes,
                SUM(v.cantidad) AS unidades_vendidas,
                ROUND(SUM(v.monto_total), 2) AS ventas_netas,
                ROUND(SUM(v.monto_cancelacion), 2) AS cancelaciones,
                ROUND(SUM(v.monto_total) / NULLIF(COUNT(DISTINCT v.numero_factura), 0), 2) AS ticket_promedio
            FROM fact_ventas v
            JOIN dim_fecha f ON v.id_fecha = f.id_fecha
            WHERE {where_clause}
            GROUP BY {group_cols}
            ORDER BY {order_cols};
        """
        df, ms = self.execute_query(sql)
        return df, ms, sql

    def run_slice(self, dimension: str, value: str) -> Tuple[pd.DataFrame, float, str]:
        """Ejecuta una operacion SLICE fijando una dimension a un unico valor."""
        if dimension == "pais":
            where_condition = "p.nombre_pais = ?"
            group_clause = "f.anio_mes, pr.categoria"
            select_dim = "p.nombre_pais AS dimension_fijada, f.anio_mes, pr.categoria"
            order_clause = "f.anio_mes, ventas_netas DESC"
        elif dimension == "categoria":
            where_condition = "pr.categoria = ?"
            group_clause = "p.nombre_pais, f.anio_mes"
            select_dim = "pr.categoria AS dimension_fijada, p.nombre_pais, f.anio_mes"
            order_clause = "ventas_netas DESC"
        elif dimension == "region":
            where_condition = "p.region = ?"
            group_clause = "p.nombre_pais, pr.categoria"
            select_dim = "p.region AS dimension_fijada, p.nombre_pais, pr.categoria"
            order_clause = "ventas_netas DESC"
        else:
            raise ValueError(f"Dimension no soportada para SLICE: {dimension}")

        sql = f"""
            SELECT
                {select_dim},
                COUNT(DISTINCT v.numero_factura) AS total_transacciones,
                COUNT(DISTINCT v.id_cliente) AS total_clientes,
                SUM(v.cantidad) AS unidades_vendidas,
                ROUND(SUM(v.monto_total), 2) AS ventas_netas,
                ROUND(SUM(v.monto_cancelacion), 2) AS devoluciones,
                ROUND(SUM(v.monto_total) / NULLIF(COUNT(DISTINCT v.numero_factura), 0), 2) AS ticket_promedio
            FROM fact_ventas v
            JOIN dim_pais p ON v.id_pais = p.id_pais
            JOIN dim_producto pr ON v.id_producto = pr.id_producto
            JOIN dim_fecha f ON v.id_fecha = f.id_fecha
            WHERE {where_condition}
            GROUP BY 1, 2, 3
            ORDER BY {order_clause};
        """
        df, ms = self.execute_query(sql, [value])
        return df, ms, sql.replace("?", f"'{value}'")

    def run_dice(
        self,
        countries: List[str],
        categories: List[str],
        year: int,
        quarters: List[int],
    ) -> Tuple[pd.DataFrame, float, str]:
        """Ejecuta una operacion DICE filtrando simultaneamente multiples dimensiones."""
        escaped_countries = ", ".join(f"'{c}'" for c in countries)
        escaped_categories = ", ".join(f"'{cat}'" for cat in categories)
        escaped_quarters = ", ".join(str(q) for q in quarters)

        sql = f"""
            SELECT
                p.nombre_pais,
                pr.categoria,
                f.anio,
                f.nombre_trimestre,
                COUNT(DISTINCT v.numero_factura) AS total_transacciones,
                COUNT(DISTINCT v.id_cliente) AS total_clientes,
                SUM(v.cantidad) AS unidades_vendidas,
                ROUND(SUM(v.monto_total), 2) AS ventas_netas,
                ROUND(SUM(v.monto_cancelacion), 2) AS cancelaciones,
                ROUND(SUM(v.monto_total) / NULLIF(COUNT(DISTINCT v.numero_factura), 0), 2) AS ticket_promedio
            FROM fact_ventas v
            JOIN dim_pais p ON v.id_pais = p.id_pais
            JOIN dim_producto pr ON v.id_producto = pr.id_producto
            JOIN dim_fecha f ON v.id_fecha = f.id_fecha
            WHERE p.nombre_pais IN ({escaped_countries})
              AND pr.categoria IN ({escaped_categories})
              AND f.anio = {year}
              AND f.trimestre IN ({escaped_quarters})
            GROUP BY p.nombre_pais, pr.categoria, f.anio, f.nombre_trimestre
            ORDER BY p.nombre_pais, pr.categoria, f.nombre_trimestre;
        """
        df, ms = self.execute_query(sql)
        return df, ms, sql

    def run_pivot(self, top_countries: int = 10) -> Tuple[pd.DataFrame, float, str]:
        """Ejecuta una operacion PIVOT rotando Paises en filas y Periodos en columnas."""
        sql = f"""
            PIVOT (
                SELECT
                    p.nombre_pais,
                    f.anio || '-' || f.nombre_trimestre AS periodo,
                    v.monto_total
                FROM fact_ventas v
                JOIN dim_pais p ON v.id_pais = p.id_pais
                JOIN dim_fecha f ON v.id_fecha = f.id_fecha
                WHERE p.nombre_pais IN (
                    SELECT p2.nombre_pais
                    FROM fact_ventas v2
                    JOIN dim_pais p2 ON v2.id_pais = p2.id_pais
                    GROUP BY p2.nombre_pais
                    ORDER BY SUM(v2.monto_total) DESC
                    LIMIT {top_countries}
                )
            )
            ON periodo
            USING ROUND(SUM(monto_total), 2)
            GROUP BY nombre_pais
            ORDER BY nombre_pais;
        """
        df, ms = self.execute_query(sql)
        return df, ms, sql

    def run_cube(self, selected_regions: List[str]) -> Tuple[pd.DataFrame, float, str]:
        """Ejecuta una operacion CUBE con 2^3 agrupaciones sobre Region, Categoria y Anio."""
        escaped_regions = ", ".join(f"'{r}'" for r in selected_regions)
        sql = f"""
            SELECT
                COALESCE(p.region, '--- TODAS LAS REGIONES ---') AS region,
                COALESCE(pr.categoria, '--- TODAS LAS CATEGORIAS ---') AS categoria,
                COALESCE(CAST(f.anio AS VARCHAR), '--- TODOS LOS ANIOS ---') AS anio,
                COUNT(DISTINCT v.numero_factura) AS total_transacciones,
                COUNT(DISTINCT v.id_cliente) AS total_clientes,
                SUM(v.cantidad) AS unidades_vendidas,
                ROUND(SUM(v.monto_total), 2) AS ventas_netas,
                ROUND(SUM(v.monto_cancelacion), 2) AS devoluciones,
                ROUND(SUM(v.monto_total) / NULLIF(COUNT(DISTINCT v.numero_factura), 0), 2) AS ticket_promedio
            FROM fact_ventas v
            JOIN dim_pais p ON v.id_pais = p.id_pais
            JOIN dim_producto pr ON v.id_producto = pr.id_producto
            JOIN dim_fecha f ON v.id_fecha = f.id_fecha
            WHERE p.region IN ({escaped_regions})
            GROUP BY CUBE (p.region, pr.categoria, f.anio)
            ORDER BY p.region NULLS LAST, pr.categoria NULLS LAST, f.anio NULLS LAST;
        """
        df, ms = self.execute_query(sql)
        return df, ms, sql

    def run_grouping_sets(self, top_countries: List[str]) -> Tuple[pd.DataFrame, float, str]:
        """Ejecuta una consulta GROUP BY GROUPING SETS sobre combinaciones analiticas selectivas."""
        escaped_countries = ", ".join(f"'{c}'" for c in top_countries)
        sql = f"""
            SELECT
                COALESCE(p.nombre_pais, '--- TODOS LOS PAISES ---') AS pais,
                COALESCE(pr.categoria, '--- TODAS LAS CATEGORIAS ---') AS categoria,
                COALESCE(CAST(f.anio AS VARCHAR), '---') AS anio,
                COALESCE(f.nombre_trimestre, '---') AS trimestre,
                GROUPING(p.nombre_pais) AS grp_pais,
                GROUPING(pr.categoria) AS grp_categoria,
                GROUPING(f.anio, f.nombre_trimestre) AS grp_periodo,
                COUNT(DISTINCT v.numero_factura) AS total_transacciones,
                SUM(v.cantidad) AS unidades_vendidas,
                ROUND(SUM(v.monto_total), 2) AS ventas_netas,
                ROUND(SUM(v.monto_cancelacion), 2) AS devoluciones,
                ROUND(SUM(v.monto_total) / NULLIF(COUNT(DISTINCT v.numero_factura), 0), 2) AS ticket_promedio
            FROM fact_ventas v
            JOIN dim_pais p ON v.id_pais = p.id_pais
            JOIN dim_producto pr ON v.id_producto = pr.id_producto
            JOIN dim_fecha f ON v.id_fecha = f.id_fecha
            WHERE p.nombre_pais IN ({escaped_countries})
            GROUP BY GROUPING SETS (
                (p.nombre_pais),
                (pr.categoria),
                (f.anio, f.nombre_trimestre),
                ()
            )
            ORDER BY grp_periodo DESC, grp_categoria DESC, grp_pais DESC, ventas_netas DESC;
        """
        df, ms = self.execute_query(sql)
        return df, ms, sql


def get_olap_engine() -> OLAPEngine:
    """Fabrica o singleton para obtener la instancia del motor OLAP."""
    if OLAPEngine._instance is None:
        OLAPEngine._instance = OLAPEngine()
    return OLAPEngine._instance


if __name__ == "__main__":
    engine = get_olap_engine()
    kpis = engine.get_kpis()
    print("KPIs calculados exitosamente:")
    for k, v in kpis.items():
        print(f"  {k}: {v}")
