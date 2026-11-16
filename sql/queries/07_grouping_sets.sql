-- ============================================================================
-- Operacion OLAP: GROUPING SETS (Agregaciones selectivas multicombinacion)
-- Descripcion: Calculo eficiente en un solo barrido de tabla de agregaciones
--              especificas requeridas por la direccion comercial:
--              1. Por Pais
--              2. Por Categoria de Producto
--              3. Por Anio y Trimestre
--              4. Total Global
-- Motor: DuckDB (Sintaxis nativa GROUP BY GROUPING SETS)
-- ============================================================================

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
WHERE p.nombre_pais IN ('United Kingdom', 'Germany', 'France', 'EIRE', 'Spain')
GROUP BY GROUPING SETS (
    (p.nombre_pais),
    (pr.categoria),
    (f.anio, f.nombre_trimestre),
    ()
)
ORDER BY
    grp_periodo DESC,
    grp_categoria DESC,
    grp_pais DESC,
    ventas_netas DESC;
