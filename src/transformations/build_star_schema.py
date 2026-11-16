"""Transformacion y construccion del Data Warehouse Dimensional (Esquema Estrella) con DuckDB.

Genera las dimensiones dim_fecha, dim_producto, dim_cliente, dim_pais
y la tabla de hechos fact_ventas, asegurando integridad referencial,
claves sustitutas y metricas analiticas para OLAP.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Dict, Any

import duckdb
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("RetailCube.Transformations")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
CLEAN_PARQUET = PROCESSED_DIR / "clean_retail_transactions.parquet"
DUCKDB_PATH = PROCESSED_DIR / "retailcube.duckdb"
SCHEMA_SQL_PATH = BASE_DIR / "sql" / "schema" / "star_schema.sql"

# Mapeo de paises a codigo ISO y region geografica
COUNTRY_METADATA: Dict[str, tuple[str, str]] = {
    "United Kingdom": ("GB", "Reino Unido"),
    "Germany": ("DE", "Europa Occidental"),
    "France": ("FR", "Europa Occidental"),
    "EIRE": ("IE", "Europa Occidental"),
    "Spain": ("ES", "Europa del Sur"),
    "Netherlands": ("NL", "Europa Occidental"),
    "Belgium": ("BE", "Europa Occidental"),
    "Switzerland": ("CH", "Europa Central"),
    "Portugal": ("PT", "Europa del Sur"),
    "Australia": ("AU", "Oceania"),
    "Norway": ("NO", "Escandinavia"),
    "Italy": ("IT", "Europa del Sur"),
    "Channel Islands": ("JE", "Reino Unido / Dependencias"),
    "Finland": ("FI", "Escandinavia"),
    "Cyprus": ("CY", "Europa del Sur / Mediterraneo"),
    "Sweden": ("SE", "Escandinavia"),
    "Austria": ("AT", "Europa Central"),
    "Denmark": ("DK", "Escandinavia"),
    "Japan": ("JP", "Asia"),
    "Poland": ("PL", "Europa del Este"),
    "USA": ("US", "Norteamerica"),
    "Israel": ("IL", "Medio Oriente"),
    "Hong Kong": ("HK", "Asia"),
    "Singapore": ("SG", "Asia"),
    "Iceland": ("IS", "Europa del Norte"),
    "Canada": ("CA", "Norteamerica"),
    "Greece": ("GR", "Europa del Sur"),
    "Malta": ("MT", "Europa del Sur / Mediterraneo"),
    "United Arab Emirates": ("AE", "Medio Oriente"),
    "European Community": ("EU", "Europa General"),
    "RSA": ("ZA", "Africa"),
    "Lebanon": ("LB", "Medio Oriente"),
    "Lithuania": ("LT", "Europa del Este"),
    "Brazil": ("BR", "Sudamerica"),
    "Czech Republic": ("CZ", "Europa del Este"),
    "Bahrain": ("BH", "Medio Oriente"),
    "Saudi Arabia": ("SA", "Medio Oriente"),
    "Unspecified": ("XX", "No Especificado"),
    "Unknown": ("XX", "No Especificado"),
}

SPANISH_MONTHS = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

SPANISH_DAYS = {
    1: "Lunes", 2: "Martes", 3: "Miercoles", 4: "Jueves",
    5: "Viernes", 6: "Sabado", 7: "Domingo"
}


def build_star_schema(clean_parquet_path: Path = CLEAN_PARQUET, db_path: Path = DUCKDB_PATH) -> Dict[str, Any]:
    """Lee las transacciones limpias y genera las tablas del esquema estrella en DuckDB y Parquet."""
    if not clean_parquet_path.exists():
        raise FileNotFoundError(f"No existe el archivo de transacciones limpias: {clean_parquet_path}")

    logger.info(f"Cargando dataset limpio desde {clean_parquet_path}...")
    df = pd.read_parquet(clean_parquet_path)
    logger.info(f"Registros disponibles: {len(df):,}")

    # =========================================================================
    # 1. CONSTRUCCION DE dim_fecha
    # =========================================================================
    logger.info("Construyendo dim_fecha...")
    dates_series = df["InvoiceDate"].dt.floor("D").drop_duplicates().sort_values()
    
    dim_fecha_rows = []
    for dt in dates_series:
        year = dt.year
        month = dt.month
        day = dt.day
        quarter = (month - 1) // 3 + 1
        dayofweek = dt.isoweekday()  # 1 = Lunes, 7 = Domingo
        id_fecha = year * 10000 + month * 100 + day
        dim_fecha_rows.append({
            "id_fecha": int(id_fecha),
            "fecha": dt.date(),
            "anio": int(year),
            "trimestre": int(quarter),
            "nombre_trimestre": f"T{quarter}",
            "mes": int(month),
            "nombre_mes": SPANISH_MONTHS[month],
            "dia": int(day),
            "dia_semana": int(dayofweek),
            "nombre_dia_semana": SPANISH_DAYS[dayofweek],
            "es_fin_de_semana": bool(dayofweek in [6, 7]),
            "anio_mes": f"{year}-{month:02d}",
        })
    df_dim_fecha = pd.DataFrame(dim_fecha_rows)
    logger.info(f"dim_fecha construida: {len(df_dim_fecha):,} fechas unicas.")

    # =========================================================================
    # 2. CONSTRUCCION DE dim_producto
    # =========================================================================
    logger.info("Construyendo dim_producto...")
    # Agrupamos por StockCode y tomamos la descripcion mas frecuente y precio promedio
    prod_grouped = df.groupby("StockCode").agg(
        descripcion=("Description", lambda s: s.mode()[0] if not s.mode().empty else s.iloc[0]),
        precio_unitario_referencia=("UnitPrice", "median")
    ).reset_index()

    # Clasificacion funcional sin inventar categorias falsas
    def categorize_product(stock_code: str, desc: str) -> str:
        s_code = stock_code.upper()
        s_desc = desc.upper()
        if s_code in ["POST", "DOT", "M", "D", "BANK CHARGES", "AMAZONFEE", "CRUK"]:
            return "CARGO_ADMINISTRATIVO"
        if any(w in s_desc for w in ["HEART", "STAR", "LIGHT", "CANDLE", "HOLDER", "DECORATION", "HANGING"]):
            return "DECORACION_HOGAR"
        if any(w in s_desc for w in ["MUG", "CUP", "PLATE", "BOWL", "JAR", "BOTTLE", "KITCHEN", "TIN"]):
            return "MENAJE_COCINA"
        if any(w in s_desc for w in ["BAG", "BOX", "CASE", "WALLET", "LUNCH"]):
            return "BOLSOS_Y_ESTUCHES"
        if any(w in s_desc for w in ["PEN", "PENCIL", "NOTEBOOK", "PAPER", "CARD", "STICKER", "TAPE"]):
            return "PAPELERIA_Y_REGALOS"
        if any(w in s_desc for w in ["TOY", "GAME", "PLUSH", "CHILD", "DOLL"]):
            return "JUGUETES_Y_NINOS"
        return "ARTICULOS_VARIOS"

    prod_grouped["categoria"] = prod_grouped.apply(
        lambda r: categorize_product(r["StockCode"], r["descripcion"]), axis=1
    )
    prod_grouped["id_producto"] = range(1, len(prod_grouped) + 1)
    df_dim_producto = prod_grouped[[
        "id_producto", "StockCode", "descripcion", "categoria", "precio_unitario_referencia"
    ]].rename(columns={"StockCode": "codigo_stock"})
    df_dim_producto["precio_unitario_referencia"] = df_dim_producto["precio_unitario_referencia"].round(2)
    logger.info(f"dim_producto construida: {len(df_dim_producto):,} productos unicos.")

    # =========================================================================
    # 3. CONSTRUCCION DE dim_cliente
    # =========================================================================
    logger.info("Construyendo dim_cliente...")
    cust_grouped = df.groupby("CustomerID").agg(
        pais_origen=("Country", lambda s: s.mode()[0] if not s.mode().empty else s.iloc[0])
    ).reset_index()

    dim_cliente_rows = []
    for _, row in cust_grouped.iterrows():
        cid = int(row["CustomerID"])
        if cid == -1:
            dim_cliente_rows.append({
                "id_cliente": -1,
                "codigo_cliente": "INVITADO",
                "tipo_cliente": "INVITADO",
                "pais_origen": row["pais_origen"] or "No Especificado",
            })
        else:
            dim_cliente_rows.append({
                "id_cliente": cid,
                "codigo_cliente": f"CLI-{cid}",
                "tipo_cliente": "REGISTRADO",
                "pais_origen": row["pais_origen"],
            })
    df_dim_cliente = pd.DataFrame(dim_cliente_rows).sort_values("id_cliente").reset_index(drop=True)
    logger.info(f"dim_cliente construida: {len(df_dim_cliente):,} clientes unicos (incluye cliente invitado).")

    # =========================================================================
    # 4. CONSTRUCCION DE dim_pais
    # =========================================================================
    logger.info("Construyendo dim_pais...")
    unique_countries = sorted(df["Country"].unique().tolist())
    dim_pais_rows = []
    for idx, cname in enumerate(unique_countries, start=1):
        iso_code, region = COUNTRY_METADATA.get(cname, ("XX", "Otras Regiones"))
        dim_pais_rows.append({
            "id_pais": int(idx),
            "nombre_pais": cname,
            "codigo_iso": iso_code,
            "region": region,
        })
    df_dim_pais = pd.DataFrame(dim_pais_rows)
    logger.info(f"dim_pais construida: {len(df_dim_pais):,} paises.")

    # =========================================================================
    # 5. CONSTRUCCION DE fact_ventas
    # =========================================================================
    logger.info("Construyendo fact_ventas con integridad referencial...")

    # Mappings para claves foraneas
    stock_to_id = dict(zip(df_dim_producto["codigo_stock"], df_dim_producto["id_producto"]))
    country_to_id = dict(zip(df_dim_pais["nombre_pais"], df_dim_pais["id_pais"]))

    fact_df = pd.DataFrame()
    fact_df["numero_factura"] = df["InvoiceNo"].astype(str)
    
    # id_fecha YYYYMMDD
    fact_df["id_fecha"] = (
        df["InvoiceDate"].dt.year * 10000 +
        df["InvoiceDate"].dt.month * 100 +
        df["InvoiceDate"].dt.day
    ).astype(int)

    fact_df["id_producto"] = df["StockCode"].map(stock_to_id).astype(int)
    fact_df["id_cliente"] = df["CustomerID"].astype(int)
    fact_df["id_pais"] = df["Country"].map(country_to_id).astype(int)
    fact_df["hora_transaccion"] = df["InvoiceDate"].dt.strftime("%H:%M:%S")
    fact_df["cantidad"] = df["Quantity"].astype(int)
    fact_df["precio_unitario"] = df["UnitPrice"].astype(float).round(2)
    fact_df["monto_total"] = df["line_total"].astype(float).round(2)
    fact_df["monto_bruto"] = fact_df["monto_total"].apply(lambda x: max(x, 0.0)).round(2)
    fact_df["monto_cancelacion"] = fact_df["monto_total"].apply(lambda x: abs(min(x, 0.0))).round(2)
    fact_df["es_cancelacion"] = df["is_cancellation"].astype(bool)
    fact_df["tipo_transaccion"] = df["transaction_type"].astype(str)
    fact_df["id_venta"] = range(1, len(fact_df) + 1)

    # Reordenar columnas de fact_ventas
    fact_cols = [
        "id_venta",
        "numero_factura",
        "id_fecha",
        "id_producto",
        "id_cliente",
        "id_pais",
        "hora_transaccion",
        "cantidad",
        "precio_unitario",
        "monto_total",
        "monto_bruto",
        "monto_cancelacion",
        "es_cancelacion",
        "tipo_transaccion",
    ]
    fact_df = fact_df[fact_cols]
    logger.info(f"fact_ventas construida: {len(fact_df):,} lineas transaccionales.")

    # =========================================================================
    # 6. GUARDAR TABLAS EN PARQUET
    # =========================================================================
    logger.info("Guardando tablas dimensionales en archivos Parquet...")
    df_dim_fecha.to_parquet(PROCESSED_DIR / "dim_fecha.parquet", index=False)
    df_dim_producto.to_parquet(PROCESSED_DIR / "dim_producto.parquet", index=False)
    df_dim_cliente.to_parquet(PROCESSED_DIR / "dim_cliente.parquet", index=False)
    df_dim_pais.to_parquet(PROCESSED_DIR / "dim_pais.parquet", index=False)
    fact_df.to_parquet(PROCESSED_DIR / "fact_ventas.parquet", index=False)

    # =========================================================================
    # 7. INICIALIZAR Y POBLAR BASE DE DATOS DUCKDB
    # =========================================================================
    logger.info(f"Creando base de datos DuckDB en {db_path}...")
    if db_path.exists():
        db_path.unlink()

    conn = duckdb.connect(str(db_path))
    with open(SCHEMA_SQL_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    conn.execute(schema_sql)

    # Cargar DataFrames en las tablas DuckDB
    conn.register("tmp_fecha", df_dim_fecha)
    conn.execute("INSERT INTO dim_fecha SELECT * FROM tmp_fecha")
    conn.unregister("tmp_fecha")

    conn.register("tmp_producto", df_dim_producto)
    conn.execute("INSERT INTO dim_producto SELECT * FROM tmp_producto")
    conn.unregister("tmp_producto")

    conn.register("tmp_cliente", df_dim_cliente)
    conn.execute("INSERT INTO dim_cliente SELECT * FROM tmp_cliente")
    conn.unregister("tmp_cliente")

    conn.register("tmp_pais", df_dim_pais)
    conn.execute("INSERT INTO dim_pais SELECT * FROM tmp_pais")
    conn.unregister("tmp_pais")

    conn.register("tmp_fact", fact_df)
    conn.execute("INSERT INTO fact_ventas SELECT * FROM tmp_fact")
    conn.unregister("tmp_fact")

    # Validacion rapida
    counts = conn.execute("""
        SELECT
            (SELECT COUNT(*) FROM dim_fecha) AS count_fecha,
            (SELECT COUNT(*) FROM dim_producto) AS count_producto,
            (SELECT COUNT(*) FROM dim_cliente) AS count_cliente,
            (SELECT COUNT(*) FROM dim_pais) AS count_pais,
            (SELECT COUNT(*) FROM fact_ventas) AS count_fact,
            (SELECT ROUND(SUM(monto_total), 2) FROM fact_ventas) AS net_revenue
    """).fetchone()
    conn.close()

    summary = {
        "count_fecha": counts[0],
        "count_producto": counts[1],
        "count_cliente": counts[2],
        "count_pais": counts[3],
        "count_fact": counts[4],
        "net_revenue": counts[5],
        "duckdb_size_mb": round(db_path.stat().st_size / (1024 * 1024), 2),
    }

    logger.info(f"Esquema estrella verificado exitosamente en DuckDB:")
    logger.info(f"- dim_fecha: {summary['count_fecha']:,}")
    logger.info(f"- dim_producto: {summary['count_producto']:,}")
    logger.info(f"- dim_cliente: {summary['count_cliente']:,}")
    logger.info(f"- dim_pais: {summary['count_pais']:,}")
    logger.info(f"- fact_ventas: {summary['count_fact']:,}")
    logger.info(f"- Ingreso neto verificado: £{summary['net_revenue']:,.2f}")
    logger.info(f"- Tamano archivo DuckDB: {summary['duckdb_size_mb']} MB")

    return summary


if __name__ == "__main__":
    build_star_schema()
