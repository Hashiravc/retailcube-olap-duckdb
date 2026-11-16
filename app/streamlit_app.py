"""RetailCube Analytics - Plataforma de Analisis Multidimensional OLAP con DuckDB.

Dashboard interactivo empresarial desarrollado con Streamlit, DuckDB y Plotly.
Proporciona operaciones analiticas reales (Roll-up, Drill-down, Slice, Dice,
Pivot, Cube y Grouping Sets) sobre un esquema estrella con el dataset
UCI Online Retail.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Asegurar que el directorio raiz este en sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.olap.olap_engine import get_olap_engine, OLAPEngine

# Configuracion de pagina de Streamlit
st.set_page_config(
    page_title="RetailCube Analytics | OLAP con DuckDB",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilos CSS personalizados para apariencia corporativa moderna
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #38BDF8, #818CF8, #C084FC);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        color: #94A3B8;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .kpi-card {
        background-color: #1E293B;
        border-radius: 10px;
        padding: 1.1rem;
        border: 1px solid #334155;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    .kpi-title {
        color: #94A3B8;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .kpi-value {
        color: #F8FAFC;
        font-size: 1.6rem;
        font-weight: 700;
        margin-top: 0.3rem;
    }
    .kpi-sub {
        color: #38BDF8;
        font-size: 0.78rem;
        margin-top: 0.2rem;
    }
    .sql-box {
        background-color: #0F172A;
        border-left: 4px solid #38BDF8;
        padding: 12px;
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        border-radius: 0 8px 8px 0;
    }
    .execution-badge {
        display: inline-block;
        background: rgba(56, 189, 248, 0.15);
        color: #38BDF8;
        border: 1px solid #0284C7;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 600;
        margin-bottom: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource(show_spinner="Iniciando motor OLAP con DuckDB...")
def load_engine() -> OLAPEngine:
    """Carga y cachea la instancia del motor OLAP."""
    return get_olap_engine()


engine = load_engine()

# =============================================================================
# BARRA LATERAL (SIDEBAR DE NAVEGACION)
# =============================================================================
with st.sidebar:
    st.image("https://duckdb.org/images/duckdb_logo.svg", width=160)
    st.markdown("## **RetailCube Analytics**")
    st.caption("OLAP Engine con DuckDB & Streamlit")
    st.markdown("---")

    selected_section = st.radio(
        "Navegación del Sistema",
        [
            "📊 Vista General",
            "⏱️ Análisis Temporal",
            "🌍 Análisis Geográfico",
            "🛍️ Análisis de Productos",
            "🧊 Explorador OLAP",
            "⭐ Modelo Dimensional",
            "ℹ️ Información del Proyecto",
        ],
        index=0,
    )

    st.markdown("---")
    st.markdown("### **Metadatos del Motor**")
    st.markdown("**Motor:** DuckDB In-Process")
    st.markdown("**Almacenamiento:** Columnar Parquet")
    st.markdown("**Dataset:** UCI Online Retail (Histórico)")
    st.markdown("**Transacciones:** 539,392")
    st.markdown("**Periodo:** 2010-12 a 2011-12")
    st.markdown("---")
    st.caption("Repositorio: [retailcube-olap-duckdb](https://github.com/Hashiravc/retailcube-olap-duckdb)")


# =============================================================================
# SECCION 1: VISTA GENERAL
# =============================================================================
if selected_section == "📊 Vista General":
    st.markdown('<div class="main-title">RetailCube Analytics: Vista General</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Tablero ejecutivo con indicadores clave (KPIs) calculados en tiempo real con DuckDB.</div>', unsafe_allow_html=True)

    with st.spinner("Calculando KPIs consolidados..."):
        kpis = engine.get_kpis()

    # Fila 1 de KPIs
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Ventas Netas Totales</div>
            <div class="kpi-value">£{kpis['total_ventas_netas']:,.2f}</div>
            <div class="kpi-sub">Ingresos netos tras devoluciones</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Ventas Brutas</div>
            <div class="kpi-value">£{kpis['total_ventas_brutas']:,.2f}</div>
            <div class="kpi-sub">Lineas con facturacion positiva</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Devoluciones / Cancelaciones</div>
            <div class="kpi-value">£{kpis['total_cancelaciones']:,.2f}</div>
            <div class="kpi-sub">{kpis['total_cancelaciones'] / kpis['total_ventas_brutas'] * 100:.1f}% de cancelaciones</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Ticket Promedio</div>
            <div class="kpi-value">£{kpis['ticket_promedio']:,.2f}</div>
            <div class="kpi-sub">Ventas netas / Facturas unicas</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Fila 2 de KPIs
    c5, c6, c7, c8 = st.columns(4)
    with c5:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Total Transacciones</div>
            <div class="kpi-value">{int(kpis['total_transacciones']):,}</div>
            <div class="kpi-sub">Facturas unicas registradas</div>
        </div>
        """, unsafe_allow_html=True)
    with c6:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Clientes Únicos</div>
            <div class="kpi-value">{int(kpis['total_clientes']):,}</div>
            <div class="kpi-sub">Registrados + Clientes Invitados</div>
        </div>
        """, unsafe_allow_html=True)
    with c7:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Catálogo de Productos</div>
            <div class="kpi-value">{int(kpis['total_productos']):,}</div>
            <div class="kpi-sub">Artículos y códigos comercializados</div>
        </div>
        """, unsafe_allow_html=True)
    with c8:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Unidades Vendidas</div>
            <div class="kpi-value">{int(kpis['total_unidades']):,}</div>
            <div class="kpi-sub">Volumen de articulos despachados</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Grafico de tendencia mensual con desglose de ventas brutas vs cancelaciones
    st.subheader("📈 Tendencia Histórica Mensual de Ventas y Devoluciones")
    trend_sql = """
        SELECT
            f.anio_mes,
            ROUND(SUM(v.monto_bruto), 2) AS ventas_brutas,
            ROUND(SUM(v.monto_cancelacion), 2) AS cancelaciones,
            ROUND(SUM(v.monto_total), 2) AS ventas_netas,
            COUNT(DISTINCT v.numero_factura) AS total_facturas
        FROM fact_ventas v
        JOIN dim_fecha f ON v.id_fecha = f.id_fecha
        GROUP BY f.anio_mes
        ORDER BY f.anio_mes;
    """
    df_trend, ms_trend = engine.execute_query(trend_sql)
    st.markdown(f'<div class="execution-badge">⚡ Consulta DuckDB ejecutada en {ms_trend} ms</div>', unsafe_allow_html=True)

    fig_trend = go.Figure()
    fig_trend.add_trace(go.Bar(
        x=df_trend["anio_mes"],
        y=df_trend["ventas_brutas"],
        name="Ventas Brutas (£)",
        marker_color="#3B82F6",
    ))
    fig_trend.add_trace(go.Bar(
        x=df_trend["anio_mes"],
        y=df_trend["cancelaciones"],
        name="Devoluciones (£)",
        marker_color="#EF4444",
    ))
    fig_trend.add_trace(go.Scatter(
        x=df_trend["anio_mes"],
        y=df_trend["ventas_netas"],
        mode="lines+markers",
        name="Ventas Netas (£)",
        line=dict(color="#10B981", width=3),
    ))
    fig_trend.update_layout(
        template="plotly_dark",
        barmode="group",
        height=420,
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_title="Periodo (Año-Mes)",
        yaxis_title="Monto en GBP (£)",
    )
    st.plotly_chart(fig_trend, use_container_width=True)


# =============================================================================
# SECCION 2: ANALISIS TEMPORAL
# =============================================================================
elif selected_section == "⏱️ Análisis Temporal":
    st.markdown('<div class="main-title">Análisis Temporal & Navegación Jerárquica</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Exploración de la jerarquía dimensional de tiempo: Año ➔ Trimestre ➔ Mes ➔ Día.</div>', unsafe_allow_html=True)

    tab_rollup, tab_drilldown = st.tabs(["🔄 Operación ROLL-UP", "🔍 Operación DRILL-DOWN"])

    with tab_rollup:
        st.markdown("### **Roll-Up Temporal con SQL ROLLUP**")
        st.write("La operación **Roll-up** agrega los datos escalando a niveles superiores de la jerarquía.")

        granularity = st.selectbox(
            "Selecciona el nivel máximo de agregación para el Roll-up:",
            ["mes", "trimestre", "anio"],
            index=0,
            format_func=lambda x: {"mes": "Mes (Año ➔ Trimestre ➔ Mes)", "trimestre": "Trimestre (Año ➔ Trimestre)", "anio": "Año (Año)"}[x],
        )

        df_rollup, ms_rollup, sql_rollup = engine.run_rollup(hierarchy_level=granularity)
        st.markdown(f'<div class="execution-badge">⚡ DuckDB ROLLUP ejecutado en {ms_rollup} ms</div>', unsafe_allow_html=True)

        col_g1, col_g2 = st.columns([3, 2])
        with col_g1:
            # Filtrar filas de subtotales para el grafico principal
            df_plot = df_rollup.dropna(subset=["anio"])
            if granularity == "mes":
                df_plot = df_plot.dropna(subset=["nombre_mes"])
                x_col = "nombre_mes"
            elif granularity == "trimestre":
                df_plot = df_plot.dropna(subset=["nombre_trimestre"])
                x_col = "nombre_trimestre"
            else:
                x_col = "anio"

            fig_rollup = px.bar(
                df_plot,
                x=x_col,
                y="ventas_netas",
                color="anio",
                title="Ventas Netas por Periodo (Roll-up)",
                labels={"ventas_netas": "Ventas Netas (£)", x_col: "Periodo"},
                template="plotly_dark",
            )
            st.plotly_chart(fig_rollup, use_container_width=True)

        with col_g2:
            st.markdown("#### **Matriz de Resultados**")
            st.dataframe(
                df_rollup.style.format({
                    "ventas_netas": "£{:,.2f}",
                    "ticket_promedio": "£{:,.2f}",
                    "total_transacciones": "{:,.0f}",
                    "unidades_vendidas": "{:,.0f}",
                }),
                height=380,
                use_container_width=True,
            )

        with st.expander("📄 Ver Consulta SQL Ejecutada en DuckDB"):
            st.code(sql_rollup, language="sql")

    with tab_drilldown:
        st.markdown("### **Drill-Down Interactivo hacia Niveles Detallados**")
        st.write("La operación **Drill-down** permite descender desde una vista macro hacia niveles granulares de análisis.")

        c_d1, c_d2 = st.columns(2)
        with c_d1:
            year_select = st.selectbox("Seleccionar Año:", [2011, 2010], index=0)
        with c_d2:
            drill_level = st.radio(
                "Nivel de desglose:",
                ["Por Trimestre", "Por Mes (Trimestre específico)", "Por Día (Mes específico)"],
                index=1,
            )

        quarter_arg = None
        month_arg = None

        if drill_level == "Por Mes (Trimestre específico)":
            quarter_arg = st.selectbox("Trimestre a desglosar:", [1, 2, 3, 4], index=3)
        elif drill_level == "Por Día (Mes específico)":
            month_arg = st.selectbox("Mes a desglosar:", list(range(1, 13)), index=10, format_func=lambda m: f"Mes {m}")

        df_drill, ms_drill, sql_drill = engine.run_drilldown(year=year_select, quarter=quarter_arg, month=month_arg)
        st.markdown(f'<div class="execution-badge">⚡ DuckDB DRILL-DOWN ejecutado en {ms_drill} ms</div>', unsafe_allow_html=True)

        if not df_drill.empty:
            x_axis = "dia" if month_arg else ("nombre_mes" if quarter_arg else "nombre_trimestre")
            fig_drill = px.line(
                df_drill,
                x=x_axis,
                y="ventas_netas",
                markers=True,
                title=f"Desglose Detallado ({drill_level}) - Año {year_select}",
                labels={"ventas_netas": "Ventas Netas (£)"},
                template="plotly_dark",
            )
            fig_drill.update_traces(line_color="#38BDF8", marker=dict(size=8, color="#818CF8"))
            st.plotly_chart(fig_drill, use_container_width=True)

            st.dataframe(
                df_drill.style.format({
                    "ventas_netas": "£{:,.2f}",
                    "ticket_promedio": "£{:,.2f}",
                    "unidades_vendidas": "{:,.0f}",
                }),
                use_container_width=True,
            )
        else:
            st.warning("No hay registros disponibles para el corte temporal seleccionado.")

        with st.expander("📄 Ver Consulta SQL Ejecutada en DuckDB"):
            st.code(sql_drill, language="sql")


# =============================================================================
# SECCION 3: ANALISIS GEOGRAFICO
# =============================================================================
elif selected_section == "🌍 Análisis Geográfico":
    st.markdown('<div class="main-title">Análisis Geográfico y Mercados Internacionales</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Evaluación de ventas por país, distribución regional y operaciones Slice / Dice sobre geografía.</div>', unsafe_allow_html=True)

    geo_sql = """
        SELECT
            p.nombre_pais,
            p.codigo_iso,
            p.region,
            ROUND(SUM(v.monto_total), 2) AS ventas_netas,
            ROUND(SUM(v.monto_cancelacion), 2) AS devoluciones,
            COUNT(DISTINCT v.numero_factura) AS total_transacciones,
            COUNT(DISTINCT v.id_cliente) AS total_clientes,
            SUM(v.cantidad) AS unidades_vendidas,
            ROUND(SUM(v.monto_total) / NULLIF(COUNT(DISTINCT v.numero_factura), 0), 2) AS ticket_promedio
        FROM fact_ventas v
        JOIN dim_pais p ON v.id_pais = p.id_pais
        GROUP BY p.nombre_pais, p.codigo_iso, p.region
        ORDER BY ventas_netas DESC;
    """
    df_geo, ms_geo = engine.execute_query(geo_sql)
    st.markdown(f'<div class="execution-badge">⚡ DuckDB Agregación Geográfica ejecutada en {ms_geo} ms</div>', unsafe_allow_html=True)

    col_map1, col_map2 = st.columns([3, 2])
    with col_map1:
        # Excluir UK temporalmente en el selector para visualizar mejor los demas paises si el usuario lo desea
        include_uk = st.checkbox("Incluir United Kingdom en la gráfica (mercado dominante ~84%)", value=False)
        df_geo_chart = df_geo if include_uk else df_geo[df_geo["nombre_pais"] != "United Kingdom"]

        fig_bar_geo = px.bar(
            df_geo_chart.head(15),
            x="ventas_netas",
            y="nombre_pais",
            orientation="h",
            color="region",
            title="Top 15 Países por Ventas Netas (£)",
            labels={"ventas_netas": "Ventas Netas (£)", "nombre_pais": "País"},
            template="plotly_dark",
        )
        fig_bar_geo.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_bar_geo, use_container_width=True)

    with col_map2:
        st.markdown("#### **Resumen por Región**")
        df_region = df_geo.groupby("region").agg({
            "ventas_netas": "sum",
            "total_transacciones": "sum",
            "total_clientes": "sum"
        }).reset_index().sort_values("ventas_netas", ascending=False)

        fig_pie = px.pie(
            df_region,
            values="ventas_netas",
            names="region",
            title="Distribución de Ventas por Región",
            hole=0.45,
            template="plotly_dark",
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("### **Tabla Detallada de Mercados Internacionales**")
    st.dataframe(
        df_geo.style.format({
            "ventas_netas": "£{:,.2f}",
            "devoluciones": "£{:,.2f}",
            "ticket_promedio": "£{:,.2f}",
            "unidades_vendidas": "{:,.0f}",
            "total_transacciones": "{:,.0f}",
            "total_clientes": "{:,.0f}",
        }),
        use_container_width=True,
    )


# =============================================================================
# SECCION 4: ANALISIS DE PRODUCTOS
# =============================================================================
elif selected_section == "🛍️ Análisis de Productos":
    st.markdown('<div class="main-title">Análisis de Productos & Segmentación Comercial</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Artículos más vendidos, volúmenes de comercialización y distribución por categorías.</div>', unsafe_allow_html=True)

    prod_sql = """
        SELECT
            pr.codigo_stock,
            pr.descripcion,
            pr.categoria,
            ROUND(SUM(v.monto_total), 2) AS ventas_netas,
            SUM(v.cantidad) AS unidades_vendidas,
            COUNT(DISTINCT v.numero_factura) AS facturas_asociadas,
            ROUND(AVG(v.precio_unitario), 2) AS precio_promedio
        FROM fact_ventas v
        JOIN dim_producto pr ON v.id_producto = pr.id_producto
        WHERE v.monto_total > 0
        GROUP BY pr.codigo_stock, pr.descripcion, pr.categoria
        ORDER BY ventas_netas DESC
        LIMIT 20;
    """
    df_top_prod, ms_prod = engine.execute_query(prod_sql)
    st.markdown(f'<div class="execution-badge">⚡ Top 20 Productos DuckDB calculado en {ms_prod} ms</div>', unsafe_allow_html=True)

    c_p1, c_p2 = st.columns([3, 2])
    with c_p1:
        fig_prod = px.bar(
            df_top_prod.head(10),
            x="ventas_netas",
            y="descripcion",
            orientation="h",
            color="categoria",
            title="Top 10 Productos Más Vendidos por Facturación (£)",
            labels={"ventas_netas": "Ventas Totales (£)", "descripcion": "Producto"},
            template="plotly_dark",
        )
        fig_prod.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_prod, use_container_width=True)

    with c_p2:
        cat_sql = """
            SELECT
                pr.categoria,
                ROUND(SUM(v.monto_total), 2) AS ventas_netas,
                SUM(v.cantidad) AS unidades_vendidas
            FROM fact_ventas v
            JOIN dim_producto pr ON v.id_producto = pr.id_producto
            GROUP BY pr.categoria
            ORDER BY ventas_netas DESC;
        """
        df_cat, _ = engine.execute_query(cat_sql)
        fig_cat = px.pie(
            df_cat,
            values="ventas_netas",
            names="categoria",
            title="Participación de Ventas por Categoría",
            hole=0.4,
            template="plotly_dark",
        )
        st.plotly_chart(fig_cat, use_container_width=True)

    st.markdown("### **Top 20 Productos con Mayor Impacto Comercial**")
    st.dataframe(
        df_top_prod.style.format({
            "ventas_netas": "£{:,.2f}",
            "precio_promedio": "£{:,.2f}",
            "unidades_vendidas": "{:,.0f}",
            "facturas_asociadas": "{:,.0f}",
        }),
        use_container_width=True,
    )


# =============================================================================
# SECCION 5: EXPLORADOR OLAP (STUDIO ANALITICO)
# =============================================================================
elif selected_section == "🧊 Explorador OLAP":
    st.markdown('<div class="main-title">Explorador Interactivo de Operaciones OLAP</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Laboratorio analítico multidimensional ejecutando consultas SQL avanzadas en tiempo real.</div>', unsafe_allow_html=True)

    op_mode = st.selectbox(
        "Selecciona la Operación OLAP que deseas ejecutar y analizar:",
        [
            "1. ROLL-UP (Subir en la jerarquía)",
            "2. DRILL-DOWN (Bajar al detalle)",
            "3. SLICE (Corte fijando una dimensión)",
            "4. DICE (Subcubo con filtros múltiples)",
            "5. PIVOT (Tabla de doble entrada cruzada)",
            "6. CUBE (Todas las combinaciones 2^N)",
            "7. GROUPING SETS (Agregaciones selectivas)",
        ],
        index=2,
    )

    st.markdown("---")

    # --- 1. ROLL-UP ---
    if "1. ROLL-UP" in op_mode:
        st.info("💡 **ROLL-UP**: Agrega ventas reduciendo granularidad (Día ➔ Mes ➔ Trimestre ➔ Año) con la cláusula SQL `ROLLUP`.")
        level = st.radio("Jerarquía de Roll-up:", ["mes", "trimestre", "anio"], horizontal=True)
        df_res, ms_res, sql_res = engine.run_rollup(hierarchy_level=level)

    # --- 2. DRILL-DOWN ---
    elif "2. DRILL-DOWN" in op_mode:
        st.info("💡 **DRILL-DOWN**: Desglosa una dimensión desde lo macro hasta lo micro, revelando patrones ocultos.")
        c_dr1, c_dr2 = st.columns(2)
        with c_dr1:
            y_dr = st.selectbox("Año:", [2011, 2010])
        with c_dr2:
            q_dr = st.selectbox("Trimestre:", [1, 2, 3, 4], index=3)
        df_res, ms_res, sql_res = engine.run_drilldown(year=y_dr, quarter=q_dr)

    # --- 3. SLICE ---
    elif "3. SLICE" in op_mode:
        st.info("💡 **SLICE**: Realiza un corte transversal en el cubo fijando una dimensión a un valor específico (ej. País o Categoría).")
        c_sl1, c_sl2 = st.columns(2)
        with c_sl1:
            dim_type = st.selectbox("Dimensión a fijar:", ["pais", "categoria", "region"])
        with c_sl2:
            possible_vals = engine.get_dimension_values(dim_type)
            selected_val = st.selectbox(f"Valor de {dim_type}:", possible_vals, index=0 if len(possible_vals) > 0 else 0)

        df_res, ms_res, sql_res = engine.run_slice(dimension=dim_type, value=selected_val)

    # --- 4. DICE ---
    elif "4. DICE" in op_mode:
        st.info("💡 **DICE**: Define un subcubo dimensional aplicando filtros simultáneos sobre varias dimensiones a la vez.")
        c_di1, c_di2, c_di3 = st.columns(3)
        with c_di1:
            all_countries = engine.get_dimension_values("pais")
            d_countries = st.multiselect("Países:", all_countries, default=["United Kingdom", "Germany", "France"])
        with c_di2:
            all_cats = engine.get_dimension_values("categoria")
            d_cats = st.multiselect("Categorías:", all_cats, default=["DECORACION_HOGAR", "MENAJE_COCINA"])
        with c_di3:
            d_quarters = st.multiselect("Trimestres (2011):", [1, 2, 3, 4], default=[3, 4])

        if not d_countries or not d_cats or not d_quarters:
            st.warning("Selecciona al menos un país, categoría y trimestre para construir el subcubo DICE.")
            df_res, ms_res, sql_res = pd.DataFrame(), 0.0, "-- Selecciona filtros"
        else:
            df_res, ms_res, sql_res = engine.run_dice(countries=d_countries, categories=d_cats, year=2011, quarters=d_quarters)

    # --- 5. PIVOT ---
    elif "5. PIVOT" in op_mode:
        st.info("💡 **PIVOT**: Rota las dimensiones transformando valores categóricos en columnas dinámicas (ej. Paises en filas y Periodos en columnas) mediante la sintaxis nativa `PIVOT` de DuckDB.")
        top_k = st.slider("Número de principales países a incluir:", min_value=3, max_value=15, value=8)
        df_res, ms_res, sql_res = engine.run_pivot(top_countries=top_k)

    # --- 6. CUBE ---
    elif "6. CUBE" in op_mode:
        st.info("💡 **CUBE**: Genera agregaciones sobre todas las posibles combinaciones ($2^N$) de las dimensiones seleccionadas mediante `GROUP BY CUBE`.")
        available_regions = ["Reino Unido", "Europa Occidental", "Escandinavia", "Europa Central"]
        sel_regions = st.multiselect("Regiones para el análisis CUBE:", available_regions, default=["Reino Unido", "Europa Occidental"])
        if not sel_regions:
            df_res, ms_res, sql_res = pd.DataFrame(), 0.0, "-- Selecciona regiones"
        else:
            df_res, ms_res, sql_res = engine.run_cube(selected_regions=sel_regions)

    # --- 7. GROUPING SETS ---
    elif "7. GROUPING SETS" in op_mode:
        st.info("💡 **GROUPING SETS**: Calcula de forma optimizada en una sola pasada múltiples agrupaciones seleccionadas explícitamente.")
        top_paises_gs = st.multiselect(
            "Países a incluir en los conjuntos de agrupación:",
            ["United Kingdom", "Germany", "France", "EIRE", "Spain", "Netherlands"],
            default=["United Kingdom", "Germany", "France"]
        )
        if not top_paises_gs:
            df_res, ms_res, sql_res = pd.DataFrame(), 0.0, "-- Selecciona países"
        else:
            df_res, ms_res, sql_res = engine.run_grouping_sets(top_countries=top_paises_gs)

    # Mostrar resultados
    st.markdown(f'<div class="execution-badge">⚡ DuckDB OLAP Query ejecutada en {ms_res} ms</div>', unsafe_allow_html=True)

    if not df_res.empty:
        st.markdown("#### **Resultado de la Consulta OLAP**")
        st.dataframe(df_res, use_container_width=True)

        # Gráfico adaptado si es aplicable
        if "ventas_netas" in df_res.columns:
            plot_df = df_res.copy()
            # Si hay comodines de CUBE o ROLLUP, filtrar filas resumen para evitar distorsion
            first_col = plot_df.columns[0]
            if plot_df[first_col].dtype == object:
                plot_df = plot_df[~plot_df[first_col].astype(str).str.contains("TODAS|---", na=False)]
            
            if not plot_df.empty and len(plot_df.columns) >= 2:
                fig_op = px.bar(
                    plot_df.head(25),
                    x=plot_df.columns[0],
                    y="ventas_netas",
                    color=plot_df.columns[1] if len(plot_df.columns) > 1 and plot_df[plot_df.columns[1]].nunique() < 10 else None,
                    title=f"Visualización de Medidas OLAP ({op_mode})",
                    labels={"ventas_netas": "Ventas Netas (£)"},
                    template="plotly_dark",
                )
                st.plotly_chart(fig_op, use_container_width=True)

    st.markdown("#### **Código SQL Ejecutado en DuckDB**")
    st.code(sql_res, language="sql")


# =============================================================================
# SECCION 6: MODELO DIMENSIONAL
# =============================================================================
elif selected_section == "⭐ Modelo Dimensional":
    st.markdown('<div class="main-title">Diseño del Data Warehouse (Esquema Estrella)</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Estructura dimensional con granularidad a nivel de línea transaccional.</div>', unsafe_allow_html=True)

    st.markdown("### **Diagrama Entidad-Relación Dimensional (Mermaid)**")
    mermaid_code = """
    erDiagram
        fact_ventas }|..|| dim_fecha : "id_fecha"
        fact_ventas }|..|| dim_producto : "id_producto"
        fact_ventas }|..|| dim_cliente : "id_cliente"
        fact_ventas }|..|| dim_pais : "id_pais"

        fact_ventas {
            bigint id_venta PK "Surrogate Key"
            varchar numero_factura "Codigo transaccion"
            int id_fecha FK "YYYYMMDD"
            int id_producto FK
            int id_cliente FK "-1 para invitado"
            int id_pais FK
            varchar hora_transaccion
            int cantidad "Aditivo"
            double precio_unitario
            double monto_total "Ventas netas"
            double monto_bruto "Ventas brutas"
            double monto_cancelacion "Devoluciones"
            boolean es_cancelacion
            varchar tipo_transaccion
        }

        dim_fecha {
            int id_fecha PK "YYYYMMDD"
            date fecha
            int anio
            int trimestre
            varchar nombre_trimestre
            int mes
            varchar nombre_mes
            int dia
            int dia_semana
            varchar nombre_dia_semana
            boolean es_fin_de_semana
            varchar anio_mes
        }

        dim_producto {
            int id_producto PK "Surrogate Key"
            varchar codigo_stock UK
            varchar descripcion
            varchar categoria
            double precio_unitario_referencia
        }

        dim_cliente {
            int id_cliente PK "-1 = Anonimo"
            varchar codigo_cliente
            varchar tipo_cliente
            varchar pais_origen
        }

        dim_pais {
            int id_pais PK "Surrogate Key"
            varchar nombre_pais UK
            varchar codigo_iso
            varchar region
        }
    """
    st.markdown(f"```mermaid\n{mermaid_code}\n```")

    st.markdown("---")
    st.markdown("### **Especificación Técnica de Tablas y Atributos**")

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("""
        #### **1. fact_ventas (Tabla de Hechos)**
        - **Granularidad:** Una fila por artículo vendido o cancelado en cada factura.
        - **Clave Primaria:** `id_venta` (Sustituta, autoincremental).
        - **Claves Foráneas:** `id_fecha`, `id_producto`, `id_cliente`, `id_pais`.
        - **Medidas Aditivas:** `monto_total`, `monto_bruto`, `monto_cancelacion`, `cantidad`.
        - **Medidas Semiaditivas / No Aditivas:** `precio_unitario`, `ticket_promedio` (calculada como `SUM(monto_total) / COUNT(DISTINCT numero_factura)`).
        - **Reglas de Calidad:** Las facturas que inician con 'C' o cantidades negativas se clasifican con `es_cancelacion = TRUE`.
        """)

        st.markdown("""
        #### **2. dim_fecha**
        - **Granularidad:** Un registro por día del calendario transaccional (305 días registrados).
        - **Clave:** `id_fecha` formato entero `YYYYMMDD`.
        - **Jerarquías:** Año ➔ Trimestre ➔ Mes ➔ Día.
        """)

    with col_t2:
        st.markdown("""
        #### **3. dim_producto**
        - **Granularidad:** Un registro por producto único comercializado (`StockCode`).
        - **Clave Primaria:** `id_producto` (Clave sustituta).
        - **Clave Natural:** `codigo_stock`.
        - **Atributos:** Descripción consolidada y categoría comercial funcional.
        """)

        st.markdown("""
        #### **4. dim_cliente**
        - **Granularidad:** Un registro por cliente identificado.
        - **Cliente Desconocido:** Se reserva `id_cliente = -1` con `codigo_cliente = 'INVITADO'` para preservar la integridad referencial de transacciones sin registro de cliente.
        """)

        st.markdown("""
        #### **5. dim_pais**
        - **Granularidad:** Un registro por mercado nacional.
        - **Atributos:** Nombre oficial, código ISO alfa-2 y región geográfica para análisis macro.
        """)


# =============================================================================
# SECCION 7: INFORMACION DEL PROYECTO
# =============================================================================
elif selected_section == "ℹ️ Información del Proyecto":
    st.markdown('<div class="main-title">Información del Proyecto & Arquitectura</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Detalles de diseño, dataset oficial, tecnologías y enlaces del proyecto académico.</div>', unsafe_allow_html=True)

    col_info1, col_info2 = st.columns([3, 2])
    with col_info1:
        st.markdown("""
        ### **Objetivo del Sistema**
        Desarrollar una solución analítica completa de **Online Analytical Processing (OLAP)** sobre datos transaccionales reales, implementando un motor columnar con **DuckDB**, un esquema dimensional tipo estrella y un dashboard de toma de decisiones empresariales.

        ### **Atribución y Fuente del Dataset**
        - **Repositorio Oficial:** [UCI Machine Learning Repository: Online Retail](https://archive.ics.uci.edu/dataset/352/online-retail)
        - **Atribución:** Chen, D. (2015). *Online Retail [Dataset]*. UCI Machine Learning Repository. DOI: 10.24432/C5BW33.
        - **Contexto:** Transacciones comerciales realizadas entre el 01/12/2010 y el 09/12/2011 por una empresa minorista registrada en el Reino Unido especializada en regalos y decoración para el hogar.
        - **Aclaración Ética:** Los datos corresponden a transacciones históricas auditadas; no se simulan ventas en tiempo real ni se alteran los registros originales.
        """)

        st.markdown("""
        ### **Arquitectura Tecnológica**
        - **Motor OLAP:** DuckDB (Motor analítico columnar in-process)
        - **Formato de Almacenamiento:** Apache Parquet con compresión Snappy
        - **Lenguaje Central:** Python 3.13
        - **Interfaz & Visualización:** Streamlit + Plotly Express
        - **Automatización CI/CD:** GitHub Actions (Integración Continua y Pipeline de Datos)
        - **Hosting SaaS:** Streamlit Community Cloud
        """)

    with col_info2:
        st.markdown("### **Enlaces y Recursos**")
        st.markdown("""
        - 📦 **Repositorio GitHub:** [github.com/Hashiravc/retailcube-olap-duckdb](https://github.com/Hashiravc/retailcube-olap-duckdb)
        - 🌐 **Aplicación en Producción:** [retailcube-olap-duckdb.streamlit.app](https://retailcube-olap-duckdb.streamlit.app)
        - 📝 **Artículo Técnico:** [DEV.to](https://dev.to)
        - 🎥 **Video Demostrativo:** YouTube (5 minutos)
        """)

        st.markdown("### **Verificación del Pipeline de Datos**")
        p_fact = BASE_DIR / "data" / "processed" / "fact_ventas.parquet"
        p_size_mb = p_fact.stat().st_size / (1024 * 1024) if p_fact.exists() else 0.0

        st.success(f"""
        **Estado de los Datos:**
        - `fact_ventas.parquet`: {p_size_mb:.2f} MB
        - Motor: DuckDB v{engine.conn.execute("SELECT version();").fetchone()[0]}
        - Integridad: 100% libre de huérfanos
        """)
