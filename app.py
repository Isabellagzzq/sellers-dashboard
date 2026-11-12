from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Dashboard de vendedores", page_icon="📊", layout="wide")

DATA_PATH = Path(__file__).parent / "sellers.xlsx"

# Nombres de columna del archivo -> etiquetas para mostrar
COLS = {
    "SOLD UNITS": "Units Sold",
    "TOTAL SALES": "Total Sales",
    "SALES AVERAGE": "Average Sales",
}
FORMATS = {"Units Sold": ",.0f", "Total Sales": "$,.0f", "Average Sales": ".1%"}


@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)
    df = df.rename(columns={"REGION": "Region", "ID": "ID", "NAME": "Nombre",
                            "LASTNAME": "Apellido", "INCOME": "Income", **COLS})
    df["Vendedor"] = df["Nombre"] + " " + df["Apellido"]
    return df


df = load_data(DATA_PATH)

# ---------- Sidebar: filtros ----------
with st.sidebar:
    st.header("Filtros")
    regiones = sorted(df["Region"].unique())
    sel_regiones = st.multiselect("Region", regiones, default=regiones)
    rango_ventas = st.slider(
        "Rango de Total Sales",
        int(df["Total Sales"].min()), int(df["Total Sales"].max()),
        (int(df["Total Sales"].min()), int(df["Total Sales"].max())),
    )
    st.caption(f"Fuente: {DATA_PATH.name} · {len(df)} vendedores")

fdf = df[
    df["Region"].isin(sel_regiones)
    & df["Total Sales"].between(*rango_ventas)
]

st.title("📊 Dashboard de vendedores")

if fdf.empty:
    st.warning("No hay vendedores con los filtros seleccionados.")
    st.stop()

# ---------- KPIs ----------
with st.container(border=True):
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Vendedores", f"{len(fdf)}")
    k2.metric("Units Sold", f"{fdf['Units Sold'].sum():,}")
    k3.metric("Total Sales", f"${fdf['Total Sales'].sum():,}")
    k4.metric("Ventas por vendedor (promedio)", f"${fdf['Total Sales'].mean():,.0f}")

tab_tabla, tab_graficas, tab_vendedor = st.tabs(["📋 Tabla", "📈 Gráficas", "🧑‍💼 Vendedor"])

# ---------- Tab 1: tabla ----------
with tab_tabla:
    busqueda = st.text_input("Buscar vendedor", placeholder="Nombre o apellido")
    tabla = fdf if not busqueda else fdf[fdf["Vendedor"].str.contains(busqueda, case=False)]
    orden = st.selectbox("Ordenar por", ["Region", "Units Sold", "Total Sales", "Average Sales", "Income"])
    desc = st.toggle("Descendente", value=orden != "Region")
    tabla = tabla.sort_values(orden, ascending=not desc)

    st.dataframe(
        tabla[["Region", "ID", "Vendedor", "Income", "Units Sold", "Total Sales", "Average Sales"]],
        hide_index=True,
        width='stretch',
        column_config={
            "Income": st.column_config.NumberColumn(format="$%d"),
            "Total Sales": st.column_config.NumberColumn(format="$%d"),
            "Average Sales": st.column_config.NumberColumn(format="percent"),
        },
    )
    st.caption(f"{len(tabla)} registros")
    st.download_button(
        "⬇️ Descargar datos filtrados (CSV)",
        tabla.to_csv(index=False).encode("utf-8-sig"),
        file_name="sellers_filtrado.csv",
        mime="text/csv",
    )

# ---------- Tab 2: gráficas ----------
with tab_graficas:
    vista = st.radio("Agrupar por", ["Vendedor", "Region"], horizontal=True)
    metricas = list(COLS.values())

    if vista == "Vendedor":
        top_n = st.slider("Mostrar los N mejores vendedores", 5, max(5, len(fdf)), min(15, len(fdf)))
    sub_tabs = st.tabs(metricas)

    for tab, metrica in zip(sub_tabs, metricas):
        with tab:
            if vista == "Vendedor":
                datos = fdf.nlargest(top_n, metrica).sort_values(metrica)
                fig = px.bar(datos, x=metrica, y="Vendedor", color="Region", orientation="h",
                             hover_data={"Region": True, metrica: False})
                fig.update_layout(height=max(350, 28 * len(datos)))
            else:
                if metrica == "Average Sales":
                    datos = fdf.groupby("Region", as_index=False)[metrica].mean()
                else:
                    datos = fdf.groupby("Region", as_index=False)[metrica].sum()
                fig = px.bar(datos, x="Region", y=metrica, color="Region", text_auto=True)
                fig.update_layout(showlegend=False)
            eje = fig.update_xaxes if vista == "Vendedor" else fig.update_yaxes
            eje(tickformat=FORMATS[metrica].replace("$", ""))
            st.plotly_chart(fig, width='stretch', key=f"grafica_{vista}_{metrica}")

    if "Average Sales" in metricas:
        st.caption(
            "Average Sales = participación del vendedor en el Total Sales de su región "
            "(Total Sales del vendedor ÷ Total Sales de la región). Al agrupar por Region se muestra el promedio."
        )

    with st.expander("Relación entre unidades vendidas y ventas totales"):
        fig = px.scatter(fdf, x="Units Sold", y="Total Sales", color="Region",
                         hover_name="Vendedor", size="Income", size_max=18)
        st.plotly_chart(fig, width='stretch', key="dispersion")

# ---------- Tab 3: vendedor ----------
with tab_vendedor:
    # Se usa nombre + región como llave: el ID 9091 aparece en dos vendedores distintos.
    opciones = fdf.assign(Etiqueta=fdf["Vendedor"] + " · " + fdf["Region"]).sort_values("Vendedor")
    etiqueta = st.selectbox("Selecciona un vendedor", opciones["Etiqueta"])
    v = opciones[opciones["Etiqueta"] == etiqueta].iloc[0]
    reg = df[df["Region"] == v["Region"]]

    with st.container(border=True):
        st.subheader(f"{v['Vendedor']}  ·  {v['Region']}")
        st.caption(f"ID {v['ID']}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Income", f"${v['Income']:,}")
        m2.metric("Units Sold", f"{v['Units Sold']:,}",
                  f"{v['Units Sold'] - reg['Units Sold'].mean():+,.0f} vs prom. región")
        m3.metric("Total Sales", f"${v['Total Sales']:,}",
                  f"{v['Total Sales'] - reg['Total Sales'].mean():+,.0f} vs prom. región")
        m4.metric("Average Sales", f"{v['Average Sales']:.1%}")

        ranking = reg["Total Sales"].rank(ascending=False, method="min")[v.name]
        st.info(f"Lugar **{int(ranking)} de {len(reg)}** en Total Sales dentro de la región {v['Region']}.")

    if st.button("Comparar contra el promedio de su región"):
        comp = pd.DataFrame({
            "Métrica": ["Units Sold", "Total Sales"] * 2,
            "Grupo": [v["Vendedor"]] * 2 + [f"Promedio {v['Region']}"] * 2,
            "Valor": [v["Units Sold"], v["Total Sales"],
                      reg["Units Sold"].mean(), reg["Total Sales"].mean()],
        })
        fig = px.bar(comp, x="Métrica", y="Valor", color="Grupo", barmode="group", text_auto=",.0f")
        st.plotly_chart(fig, width='stretch', key="comparacion_vendedor")

    with st.expander("Ver todos los compañeros de la región"):
        st.dataframe(
            reg[["ID", "Vendedor", "Units Sold", "Total Sales", "Average Sales"]]
            .sort_values("Total Sales", ascending=False),
            hide_index=True, width='stretch',
            column_config={"Average Sales": st.column_config.NumberColumn(format="percent")},
        )
