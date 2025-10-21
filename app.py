import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
from datetime import datetime

# --- Configuración general ---
st.set_page_config(layout="wide", page_title="Guía Práctica 1 - Compras Públicas API")

API_URL = "https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/api/get_analysis"

# --- Función de carga desde API ---
@st.cache_data
def load_api(year=None):
    """Carga datos desde el API, solo usando el parámetro 'year'."""
    try:
        params = {}
        if year:
            params["year"] = year

        resp = requests.get(API_URL, params=params, timeout=20)
        st.write(f"📡 Consultando: {resp.url} (status {resp.status_code})")

        if resp.status_code != 200:
            st.warning(f"⚠️ Código HTTP {resp.status_code}: el servidor no devolvió datos válidos.")
            return pd.DataFrame()

        data = resp.json()
        if not data:
            st.warning("⚠️ El API devolvió una lista vacía. Prueba con otro año.")
            return pd.DataFrame()

        df = pd.DataFrame(data)
        return df

    except Exception as e:
        st.error(f"❌ Error al conectar con el API: {e}")
        return pd.DataFrame()

# --- Título ---
st.title("Guía Práctica 1 - Análisis de Compras Públicas (Ecuador)")
st.markdown("Aplicación Streamlit conectada al **API de datos abiertos** de compras públicas de Ecuador. "
            "Se usa el parámetro `year` para obtener los registros.")

# --- Sidebar: selección de año ---
st.sidebar.header("Parámetros del API")
year = st.sidebar.selectbox("Selecciona el año:", [2020, 2021, 2022, 2023, 2024, 2025], index=3)
load_btn = st.sidebar.button("🔄 Cargar datos")

# --- Cargar datos ---
if load_btn:
    with st.spinner("Cargando datos desde el API..."):
        df = load_api(year)

    if df.empty:
        st.stop()

    # --- Preprocesamiento mínimo ---
    df.columns = [c.strip().lower() for c in df.columns]

    # Crear columnas faltantes
    if "year" not in df.columns:
        df["year"] = year
    if "date" not in df.columns:
        df["date"] = pd.to_datetime(df["year"].astype(str) + "-" + df["month"].astype(str) + "-01")
    if "province" not in df.columns:
        df["province"] = "Desconocido"

    # Tipos correctos
    df["month"] = pd.to_numeric(df["month"], errors="coerce")
    df["total"] = pd.to_numeric(df["total"], errors="coerce")
    df["contracts"] = pd.to_numeric(df["contracts"], errors="coerce")
    df["internal_type"] = df["internal_type"].astype(str)

    # --- Filtros locales ---
    st.sidebar.markdown("---")
    st.sidebar.header("Filtros locales")
    tipos = sorted(df["internal_type"].unique())
    selected_types = st.sidebar.multiselect("Filtrar por tipo de contratación:", tipos, default=tipos)

    df_filtered = df[df["internal_type"].isin(selected_types)]

    # --- KPIs ---
    st.subheader("Indicadores clave")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Registros", len(df_filtered))
    c2.metric("Monto total (USD)", f"{df_filtered['total'].sum():,.0f}")
    c3.metric("Promedio", f"{df_filtered['total'].mean():,.0f}")
    c4.metric("Máximo", f"{df_filtered['total'].max():,.0f}")

    # --- Visualizaciones ---
    st.subheader("Visualizaciones")

    # Total por tipo
    agg = df_filtered.groupby("internal_type", as_index=False)["total"].sum().sort_values("total", ascending=False)
    fig1 = px.bar(agg, x="internal_type", y="total", title="Monto total por tipo de contratación")
    st.plotly_chart(fig1, use_container_width=True)

    # Evolución mensual
    monthly = df_filtered.groupby("month", as_index=False)["total"].sum().sort_values("month")
    fig2 = px.line(monthly, x="month", y="total", markers=True, title="Evolución mensual del monto total")
    st.plotly_chart(fig2, use_container_width=True)

    # Dispersión contratos vs total
    fig3 = px.scatter(df_filtered, x="contracts", y="total", color="internal_type",
                      title="Relación entre cantidad de contratos y monto total")
    st.plotly_chart(fig3, use_container_width=True)

    # Heatmap mes x tipo
    heat = df_filtered.groupby(["month", "internal_type"])["total"].sum().reset_index()
    pivot = heat.pivot(index="internal_type", columns="month", values="total").fillna(0)
    fig4 = px.imshow(pivot, text_auto=True, aspect="auto",
                     labels=dict(x="Mes", y="Tipo de contratación", color="Monto total (USD)"))
    st.plotly_chart(fig4, use_container_width=True)

    # --- Datos y exportación ---
    st.subheader("Datos procesados")
    st.dataframe(df_filtered.head(100))

    csv = df_filtered.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Descargar CSV procesado", data=csv, file_name="compras_publicas_procesado.csv", mime="text/csv")

else:
    st.info("Selecciona un año y presiona **Cargar datos** para iniciar.")
