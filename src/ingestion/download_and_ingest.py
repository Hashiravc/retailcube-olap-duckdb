"""Script de ingestion y limpieza de datos para RetailCube Analytics.

Fuente oficial:
UCI Machine Learning Repository - Online Retail
https://archive.ics.uci.edu/dataset/352/online-retail
Atribucion: Chen, D. (2015). Online Retail. UCI Machine Learning Repository.
"""

from __future__ import annotations

import logging
import os
import sys
import zipfile
from pathlib import Path
from typing import Dict, Any

import pandas as pd
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("RetailCube.Ingestion")

UCI_URL = "https://archive.ics.uci.edu/static/public/352/online+retail.zip"
BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
ZIP_PATH = RAW_DIR / "online_retail.zip"
EXCEL_PATH = RAW_DIR / "Online Retail.xlsx"
PARQUET_CLEAN_PATH = PROCESSED_DIR / "clean_retail_transactions.parquet"

EXPECTED_COLUMNS = [
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
    "Country",
]


def ensure_directories() -> None:
    """Crea los directorios necesarios si no existen."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def download_dataset(force: bool = False) -> Path:
    """Descarga el archivo zip desde el repositorio oficial de UCI."""
    ensure_directories()
    if EXCEL_PATH.exists() and not force:
        logger.info(f"Archivo Excel ya existe en: {EXCEL_PATH}")
        return EXCEL_PATH

    if not ZIP_PATH.exists() or force:
        logger.info(f"Descargando dataset desde {UCI_URL} ...")
        response = requests.get(UCI_URL, stream=True, timeout=60)
        response.raise_for_status()
        with open(ZIP_PATH, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
        logger.info(f"Descarga completada: {ZIP_PATH} ({ZIP_PATH.stat().st_size / (1024*1024):.2f} MB)")

    logger.info(f"Extrayendo archivo zip...")
    with zipfile.ZipFile(ZIP_PATH, "r") as zip_ref:
        zip_ref.extractall(RAW_DIR)
    
    if not EXCEL_PATH.exists():
        # Puede que el nombre en el zip tenga diferente capitalizacion
        found = list(RAW_DIR.glob("*.xlsx"))
        if found:
            return found[0]
        raise FileNotFoundError("No se encontro archivo .xlsx dentro del zip descargado.")

    logger.info(f"Archivo extraido correctamente: {EXCEL_PATH}")
    return EXCEL_PATH


def validate_schema(df: pd.DataFrame) -> None:
    """Valida la presencia de las columnas esperadas en el dataset."""
    missing = [col for col in EXPECTED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Columnas faltantes en el dataset: {missing}")
    logger.info("Validacion de esquema exitosa. Todas las columnas requeridas estan presentes.")


def process_and_clean_data(file_path: Path) -> tuple[pd.DataFrame, Dict[str, Any]]:
    """Carga, valida, audita y limpia las transacciones del dataset de UCI Online Retail."""
    logger.info(f"Leyendo dataset original desde {file_path} ...")
    df_raw = pd.read_excel(file_path, engine="openpyxl")
    total_raw_rows = len(df_raw)
    logger.info(f"Total de filas leidas en crudo: {total_raw_rows:,}")

    validate_schema(df_raw)

    metrics: Dict[str, Any] = {
        "total_raw_rows": total_raw_rows,
        "null_customer_ids": int(df_raw["CustomerID"].isna().sum()),
        "null_descriptions": int(df_raw["Description"].isna().sum()),
        "null_unit_prices": int(df_raw["UnitPrice"].isna().sum()),
        "null_quantities": int(df_raw["Quantity"].isna().sum()),
    }

    df = df_raw.copy()

    # Normalizar InvoiceNo y detectar cancelaciones
    df["InvoiceNo"] = df["InvoiceNo"].astype(str).str.strip()
    df["StockCode"] = df["StockCode"].astype(str).str.strip()
    
    # Flags de calidad y clasificacion
    is_cancel_code = df["InvoiceNo"].str.upper().str.startswith("C")
    is_neg_quantity = df["Quantity"] < 0
    df["is_cancellation"] = is_cancel_code | is_neg_quantity

    # Tratamiento de tipo de transaccion
    def classify_row(row):
        if row["is_cancellation"]:
            return "CANCELACION"
        if row["UnitPrice"] <= 0:
            return "AJUSTE_PRECIO_CERO"
        return "VENTA_REGULAR"

    df["transaction_type"] = df.apply(classify_row, axis=1)

    # Filtrar registros anomalos sin valor comercial real (ej. ajustes contables con precio 0 y sin descripcion)
    # Conservamos todas las ventas regulares y cancelaciones validas
    valid_mask = (df["UnitPrice"] > 0) & (df["Quantity"] != 0)
    invalid_rows = int((~valid_mask).sum())
    metrics["invalid_or_zero_price_rows"] = invalid_rows
    logger.info(f"Registros con precio <= 0 o cantidad 0 detectados: {invalid_rows:,}")

    df_cleaned = df[valid_mask].copy()

    # Tratamiento de valores nulos en CustomerID: asignar -1 (Cliente Invitado / Anonimo)
    # de modo que conservemos la transaccion en la tabla de hechos y respetemos la integridad dimensional
    df_cleaned["CustomerID"] = df_cleaned["CustomerID"].fillna(-1).astype(int)

    # Tratamiento de Descripcion nula
    df_cleaned["Description"] = df_cleaned["Description"].fillna("DESCRIPCION NO DISPONIBLE").astype(str).str.strip().str.upper()

    # Tratamiento de Pais
    df_cleaned["Country"] = df_cleaned["Country"].fillna("Unknown").astype(str).str.strip()

    # Conversion de InvoiceDate
    df_cleaned["InvoiceDate"] = pd.to_datetime(df_cleaned["InvoiceDate"])

    # Calculo de line_total (ventas en GBP £)
    df_cleaned["line_total"] = (df_cleaned["Quantity"] * df_cleaned["UnitPrice"]).round(2)

    metrics["clean_rows"] = len(df_cleaned)
    metrics["cancellations_count"] = int(df_cleaned["is_cancellation"].sum())
    metrics["regular_sales_count"] = int((df_cleaned["transaction_type"] == "VENTA_REGULAR").sum())
    metrics["unique_invoices"] = int(df_cleaned["InvoiceNo"].nunique())
    metrics["unique_products"] = int(df_cleaned["StockCode"].nunique())
    metrics["unique_customers"] = int(df_cleaned[df_cleaned["CustomerID"] != -1]["CustomerID"].nunique())
    metrics["unique_countries"] = int(df_cleaned["Country"].nunique())
    metrics["min_date"] = str(df_cleaned["InvoiceDate"].min())
    metrics["max_date"] = str(df_cleaned["InvoiceDate"].max())
    metrics["total_gross_revenue"] = float(df_cleaned[df_cleaned["line_total"] > 0]["line_total"].sum().round(2))
    metrics["total_cancellations_amount"] = float(abs(df_cleaned[df_cleaned["line_total"] < 0]["line_total"].sum()).round(2))
    metrics["total_net_revenue"] = float(df_cleaned["line_total"].sum().round(2))

    logger.info(f"Limpieza completada: {metrics['clean_rows']:,} filas limpias.")
    logger.info(f"Ventas regulares: {metrics['regular_sales_count']:,} | Cancelaciones: {metrics['cancellations_count']:,}")
    logger.info(f"Ingresos brutos: £{metrics['total_gross_revenue']:,.2f} | Devoluciones: £{metrics['total_cancellations_amount']:,.2f} | Ingresos netos: £{metrics['total_net_revenue']:,.2f}")

    return df_cleaned, metrics


def save_to_parquet(df: pd.DataFrame, output_path: Path = PARQUET_CLEAN_PATH) -> None:
    """Guarda el DataFrame procesado en formato Parquet comprimido con Snappy."""
    ensure_directories()
    df.to_parquet(output_path, engine="pyarrow", compression="snappy", index=False)
    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"Archivo Parquet guardado exitosamente en {output_path} ({size_mb:.2f} MB)")


def run_ingestion(force_download: bool = False) -> tuple[pd.DataFrame, Dict[str, Any]]:
    """Ejecuta el pipeline completo de ingestion de manera idempotente."""
    excel_path = download_dataset(force=force_download)
    df_cleaned, metrics = process_and_clean_data(excel_path)
    save_to_parquet(df_cleaned)
    return df_cleaned, metrics


if __name__ == "__main__":
    run_ingestion()
