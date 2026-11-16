-- ============================================================================
-- Operacion OLAP: DICE (Subcubo multidimensional)
-- Descripcion: Filtrar simultaneamente por multiples dimensiones y rangos
--              (ej. Paises seleccionados, Rango de fechas y Categoria de productos)
-- Motor: DuckDB
-- ============================================================================

SELECT
    p.nombre_pais,
    pr.categoria,
    f.nombre_trimestre,
    COUNT(DISTINCT v.numero_factura) AS total_transacciones,
    COUNT(DISTINCT v.id_cliente) AS total_clientes,
    SUM(v.cantidad) AS unidades_vendidas,
    ROUND(SUM(v.monto_total), 2) AS ventas_netas,
    ROUND(SUM(v.monto_cancelacion), 2) AS monto_cancelaciones,
    ROUND(SUM(v.monto_total) / NULLIF(COUNT(DISTINCT v.numero_factura), 0), 2) AS ticket_promedio
FROM fact_ventas v
JOIN dim_pais p ON v.id_pais = p.id_pais
JOIN dim_producto pr ON v.id_producto = pr.id_producto
JOIN dim_fecha f ON v.id_fecha = f.id_fecha
WHERE p.nombre_pais IN ('France', 'Germany', 'Spain')
  AND pr.categoria IN ('DECORACION_HOGAR', 'MENAJE_COCINA')
  AND f.anio = 2011
  AND f.trimestre IN (3, 4)
GROUP BY p.nombre_pais, pr.categoria, f.nombre_trimestre
ORDER BY p.nombre_pais, pr.categoria, f.nombre_trimestre;
