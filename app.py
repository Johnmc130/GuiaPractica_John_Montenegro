import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
from datetime import datetime

# Configuración base
st.set_page_config(layout="wide", page_title="Guía Práctica 1 - Compras Públicas API")

API_URL = "https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/api/get_analysis"

# --- Función para cargar desde API ---
@st.cache_data
def load_api(year=None, region=None, contract_type=None):
    params = {}
    if year: params["year"] = year
    if region: params["region"] = region
    if contract_type: params["type"] = contract_type

    resp = requests.get(API_URL, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    return pd.DataFrame(data)

# --- Título ---
st.title("Guía Práctica 1 - Análisis de Compras Públicas (Ecuador)")
st.markdown("Este panel obtiene datos desde el **API de compras públicas** de Ecuador. "
            "La API requiere parámetros como año, región o tipo de contratación para devolver datos.")

# --- Sidebar: filtros de usuario ---
st.sidebar.header("Filtros para el API")

year = st.sidebar.selectbox("Año", [2021, 2022, 2023, 2024, 2025], index=2)
region = st.sidebar.text_input("Región o provincia (opcional)", "")
contract_type = st.sidebar.selectbox("Tipo de contratación (opcional)", ["", "Compra", "Licitación", "Contratación directa"])
st.sidebar.markdown("---")
st.sidebar.info("Presiona el botón para cargar datos del API.")
load_btn = st.sidebar.button("Cargar datos del API")

# --- Cargar datos ---
if load_btn:
    with st.spinner("Consultando API..."):
        df = load_api(year=year, region=region if region else None,
                      contract_type=contract_type if contract_type else None)

    if df.empty:
        st.warning("⚠️ El API no devolvió datos con esos parámetros. Prueba con otro año o tipo.")
        st.stop()

    # --- Preprocesamiento mínimo ---
    df.columns = [c.strip().lower() for c in df.columns]

    if "year" not in df.columns:
        df["year"] = year
    if "date" not in df.columns:
        df["date"] = pd.to_datetime(df["year"].astype(str) + "-" + df["month"].astype(str) + "-01")
    if "province" not in df.columns:
        df["province"] = region if region else "Desconocido"

    df["month"] = pd.to_numeric(df["month"], errors="coerce")
    df["total"] = pd.to_numeric(df["total"], errors="coerce")
    df["contracts"] = pd.to_numeric(df["contracts"], errors="coerce")

    # --- KPIs ---
    st.subheader("Indicadores clave")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Registros", len(df))
    c2.metric("Monto total (USD)", f"{df['total'].sum():,.0f}")
    c3.metric("Promedio", f"{df['total'].mean():,.0f}")
    c4.metric("Máximo", f"{df['total'].max():,.0f}")

    # --- Gráficos ---
    st.subheader("Visualizaciones")

    agg = df.groupby("internal_type", as_index=False)["total"].sum().sort_values("total", ascending=False)
    fig1 = px.bar(agg, x="internal_type", y="total", title="Monto total por tipo de contratación")
    st.plotly_chart(fig1, use_container_width=True)

    monthly = df.groupby("month", as_index=False)["total"].sum().sort_values("month")
    fig2 = px.line(monthly, x="month", y="total", markers=True, title="Evolución mensual del monto total")
    st.plotly_chart(fig2, use_container_width=True)

    fig3 = px.scatter(df, x="contracts", y="total", color="internal_type",
                      title="Relación entre cantidad de contratos y monto total")
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("Datos procesados")
    st.dataframe(df.head(50))

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Descargar CSV procesado", data=csv, file_name="compras_publicas_procesado.csv", mime="text/csv")

else:
    st.info("Selecciona parámetros y presiona **Cargar datos del API** para iniciar.")
