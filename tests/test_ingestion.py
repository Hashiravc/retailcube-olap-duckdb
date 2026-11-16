"""Pruebas unitarias para el modulo de ingestion y calidad de datos."""

from pathlib import Path
import pandas as pd
import pytest

from src.ingestion.download_and_ingest import (
    EXPECTED_COLUMNS,
    validate_schema,
    PROCESSED_DIR,
    PARQUET_CLEAN_PATH,
)


def test_expected_columns_definition():
    """Valida que la lista de columnas esperadas sea completa."""
    assert len(EXPECTED_COLUMNS) == 8
    assert "InvoiceNo" in EXPECTED_COLUMNS
    assert "CustomerID" in EXPECTED_COLUMNS
    assert "UnitPrice" in EXPECTED_COLUMNS


def test_validate_schema_success():
    """Valida que un DataFrame con las columnas correctas pase la validacion."""
    df_valid = pd.DataFrame(columns=EXPECTED_COLUMNS)
    # No debe levantar excepcion
    validate_schema(df_valid)


def test_validate_schema_failure():
    """Valida que un DataFrame con columnas faltantes levante ValueError."""
    df_invalid = pd.DataFrame(columns=["InvoiceNo", "Quantity"])
    with pytest.raises(ValueError) as excinfo:
        validate_schema(df_invalid)
    assert "Columnas faltantes" in str(excinfo.value)


def test_clean_parquet_exists_and_valid():
    """Valida que el archivo parquet procesado exista y cumpla con las metricas esperadas."""
    assert PARQUET_CLEAN_PATH.exists(), f"No se encontro {PARQUET_CLEAN_PATH}"
    df = pd.read_parquet(PARQUET_CLEAN_PATH)
    
    assert len(df) > 500000, "El dataset procesado debe tener mas de 500,000 registros"
    assert "is_cancellation" in df.columns
    assert "line_total" in df.columns
    assert "transaction_type" in df.columns
    
    # Validar que no haya precios unitarios <= 0
    assert (df["UnitPrice"] <= 0).sum() == 0, "No deben existir registros con UnitPrice <= 0"
    
    # Validar que no haya cantidades en cero
    assert (df["Quantity"] == 0).sum() == 0, "No deben existir registros con Quantity == 0"
    
    # Validar clientes invitados representados con -1
    assert -1 in df["CustomerID"].values, "Debe existir la representacion de clientes invitados (-1)"
    
    # Validar consistencia de cancelaciones
    cancellations = df[df["is_cancellation"]]
    assert len(cancellations) > 0, "Deben haberse detectado transacciones canceladas"
    assert (cancellations["line_total"] < 0).all(), "Todas las cancelaciones deben tener line_total negativo"
