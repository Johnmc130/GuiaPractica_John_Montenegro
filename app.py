import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="Guía Práctica 1 - Compras Públicas (Ecuador)")

API_URL = "https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/api/get_analysis"

# --- FUNCIÓN PARA CARGAR DATOS ---
@st.cache_data
def load_api(year=None):
    """
    Carga datos desde el API o usa un JSON local con el mismo formato.
    """
    try:
        params = {}
        if year:
            params["year"] = year

        resp = requests.get(API_URL, params=params, timeout=20)
        st.write(f"📡 Consultando: {resp.url} (status {resp.status_code})")

        if resp.status_code != 200:
            st.warning(f"⚠️ Código HTTP {resp.status_code}. Puede que el servidor no devuelva datos.")
            return pd.DataFrame()

        data = resp.json()
        if not data:
            st.warning("⚠️ El API devolvió una lista vacía.")
            return pd.DataFrame(data)

        return pd.DataFrame(data)

    except Exception as e:
        st.error(f"❌ Error al conectar con el API: {e}")
        return pd.DataFrame()

@st.cache_data
def load_local_json(uploaded_file):
    """Carga el JSON que subiste (get_analysis.json)"""
    df = pd.read_json(uploaded_file)
    return df

# --- INTERFAZ PRINCIPAL ---
st.title("Guía Práctica 1 - Análisis de Compras Públicas")
st.markdown("Esta app visualiza los datos del **API o del archivo JSON** de Compras Públicas del Ecuador.")

# Sidebar
st.sidebar.header("Fuente de datos")
data_source = st.sidebar.radio("Selecciona la fuente:", ["Archivo JSON local", "API en línea"])
year = st.sidebar.selectbox("Año (solo para API)", [2021, 2022, 2023, 2024, 2025], index=3)
load_button = st.sidebar.button("🔄 Cargar datos")

if not load_button:
    st.info("Selecciona la fuente y presiona **Cargar datos**.")
    st.stop()

# --- CARGAR DATOS ---
if data_source == "Archivo JSON local":
    uploaded_file = st.sidebar.file_uploader("Sube tu archivo get_analysis.json", type=["json"])
    if uploaded_file is not None:
        df = load_local_json(uploaded_file)
    else:
        st.warning("Sube el archivo JSON primero.")
        st.stop()
else:
    df = load_api(year)

if df.empty:
    st.warning("⚠️ No hay datos disponibles.")
    st.stop()

# --- LIMPIEZA Y PREPROCESAMIENTO ---
df.columns = [c.strip().lower() for c in df.columns]

# Convertir tipos
df["month"] = pd.to_numeric(df["month"], errors="coerce")
df["contracts"] = pd.to_numeric(df["contracts"], errors="coerce")
df["total"] = pd.to_numeric(df["total"], errors="coerce")

# Crear columnas faltantes
df["year"] = year if "year" not in df.columns else df["year"]
df["date"] = pd.to_datetime(df["year"].astype(str) + "-" + df["month"].astype(str) + "-01")
df["province"] = "Desconocido"

# --- FILTROS LOCALES ---
st.sidebar.header("Filtros locales")
types = sorted(df["internal_type"].dropna().unique())
selected_types = st.sidebar.multiselect("Tipo de contratación", types, default=types)

df_filtered = df[df["internal_type"].isin(selected_types)]

# --- KPIs ---
st.subheader("Indicadores Clave (KPI)")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Registros", len(df_filtered))
col2.metric("Monto total (USD)", f"{df_filtered['total'].sum():,.0f}")
col3.metric("Promedio (USD)", f"{df_filtered['total'].mean():,.0f}")
col4.metric("Máximo (USD)", f"{df_filtered['total'].max():,.0f}")

# --- VISUALIZACIONES ---
st.subheader("Visualizaciones")

# 1️⃣ Monto total por tipo
agg = df_filtered.groupby("internal_type", as_index=False)["total"].sum().sort_values("total", ascending=False)
fig1 = px.bar(agg, x="internal_type", y="total",
              title="Monto total por tipo de contratación",
              labels={"internal_type": "Tipo", "total": "Monto (USD)"})
st.plotly_chart(fig1, use_container_width=True)

# 2️⃣ Evolución mensual
monthly = df_filtered.groupby("month", as_index=False)["total"].sum().sort_values("month")
fig2 = px.line(monthly, x="month", y="total", markers=True,
               title="Evolución mensual del monto total")
st.plotly_chart(fig2, use_container_width=True)

# 3️⃣ Dispersión
fig3 = px.scatter(df_filtered, x="contracts", y="total", color="internal_type",
                  title="Relación entre cantidad de contratos y monto total",
                  labels={"contracts": "Contratos", "total": "Monto total (USD)"})
st.plotly_chart(fig3, use_container_width=True)

# 4️⃣ Heatmap mes × tipo
heat = df_filtered.groupby(["month", "internal_type"])["total"].sum().reset_index()
pivot = heat.pivot(index="internal_type", columns="month", values="total").fillna(0)
fig4 = px.imshow(pivot, text_auto=True, aspect="auto",
                 labels=dict(x="Mes", y="Tipo de contratación", color="Monto total (USD)"))
st.plotly_chart(fig4, use_container_width=True)

# --- DATOS Y DESCARGA ---
st.subheader("Datos procesados")
st.dataframe(df_filtered.head(100))

csv = df_filtered.to_csv(index=False).encode("utf-8")
st.download_button("📥 Descargar CSV procesado", data=csv,
                   file_name="compras_publicas_procesado.csv", mime="text/csv")

st.subheader("Conclusiones")
st.text_area("Escribe tus conclusiones aquí:", height=120,
             placeholder="Ejemplo: Los tipos de contratación con mayores montos son ...")
