
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

# --- Configuración de la página y carga de datos ---

st.set_page_config(page_title="Análisis de Crecimiento de Aves", layout="wide")

# Cargar el logo
try:
    logo = Image.open('ARCHIVOS/log_PEQ.png')
except FileNotFoundError:
    st.error("No se encontró el archivo del logo en la ruta 'ARCHIVOS/log_PEQ.png'")
    logo = None

# Funciones para cargar los datos con caché para mejorar el rendimiento
@st.cache_data
def load_data(file_path):
    """Carga un archivo CSV desde la ruta especificada, usando punto y coma como separador."""
    try:
        return pd.read_csv(file_path, sep=';')
    except FileNotFoundError:
        st.error(f"Error: No se encontró el archivo {file_path}. Asegúrate de que esté en la carpeta 'ARCHIVOS'.")
        return None

df_guia = load_data('ARCHIVOS/ROSS_COBB_HUBBARD_2025.csv')
df_poly_coeffs = load_data('ARCHIVOS/Cons_Acum_Peso.csv')
df_poly_coeffs_15 = load_data('ARCHIVOS/Cons_Acum_Peso_15.csv')

# --- Encabezado de la Aplicación ---

if logo:
    st.image(logo, width=150)

st.title("ALBATEQ S. A. - Dirección Técnica")
st.subheader("Cálculos de Consumos vs la Línea Genética (Restricción) y Peso Estimado de acuerdo con el Consumo Real en granjas.")
st.markdown("---")

# --- Barra Lateral de Entradas (Inputs) ---

st.sidebar.header("Panel de Control")

if df_guia is not None:
    # Obtener listas únicas para los selectbox
    razas_disponibles = df_guia['RAZA'].unique()
    sexos_disponibles = df_guia['SEXO'].unique()

    raza_seleccionada = st.sidebar.selectbox("Seleccione la Línea Genética (RAZA):", razas_disponibles)
    sexo_seleccionado = st.sidebar.selectbox("Seleccione el SEXO:", sexos_disponibles)
else:
    st.sidebar.error("No se pudieron cargar las opciones de RAZA y SEXO.")
    razas_disponibles = ["No disponible"]
    sexos_disponibles = ["No disponible"]
    raza_seleccionada = razas_disponibles[0]
    sexo_seleccionado = sexos_disponibles[0]


dia_input = st.sidebar.number_input("Día:", min_value=1, max_value=100, value=35, step=1)
consumo_real_input = st.sidebar.number_input("Consumo Acumulado Real (gramos):", min_value=0, value=3500, step=100)
peso_real_input = st.sidebar.number_input("Peso Real (gramos):", min_value=0, value=2000, step=50)
mortalidad_input = st.sidebar.number_input("Mortalidad (%):", min_value=0.0, value=3.5, format="%.2f")

st.sidebar.markdown("---")
granja_tipo = st.sidebar.radio("Tipo de Granja:", ('TUNEL', 'MEJORADA', 'NATURAL'))
altitud_tipo = st.sidebar.radio("Altitud (ASNM):", ('ALTA >2000 msnm', 'MEDIA <2000 y >1000 msnm', 'BAJA < 1000 msnm'))

# Botón para ejecutar los cálculos
calcular_btn = st.sidebar.button("Generar Análisis y Gráficas")

# --- Lógica Principal y Visualización de Resultados ---

if calcular_btn and df_guia is not None and df_poly_coeffs is not None and df_poly_coeffs_15 is not None:
    
    # 1. Búsqueda del Consumo Guía
    guia_filtrada = df_guia[(df_guia['RAZA'] == raza_seleccionada) & (df_guia['SEXO'] == sexo_seleccionado) & (df_guia['Dia'] == dia_input)]
    
    if guia_filtrada.empty:
        st.warning(f"No se encontraron datos de guía para {raza_seleccionada} - {sexo_seleccionado} en el día {dia_input}.")
    else:
        consumo_guia = guia_filtrada['Cons_Acum'].iloc[0]
        peso_guia = guia_filtrada['Peso'].iloc[0] # Peso guía para la gráfica

        # 2. Cálculo del Peso Estimado con modelo polinómico
        if dia_input <= 15:
            df_coeffs_actual = df_poly_coeffs_15
        else:
            df_coeffs_actual = df_poly_coeffs
            
        coeffs_filtrados = df_coeffs_actual[(df_coeffs_actual['RAZA'] == raza_seleccionada) & (df_coeffs_actual['SEXO'] == sexo_seleccionado)]
        
        if coeffs_filtrados.empty:
            st.error(f"No se encontraron coeficientes para el cálculo de peso estimado para {raza_seleccionada} - {sexo_seleccionado}.")
        else:
            # Extraer coeficientes según la nueva definición (sin Coef_0)
            intercepto = coeffs_filtrados['Intercept'].iloc[0]
            c1 = coeffs_filtrados['Coef_1'].iloc[0]
            c2 = coeffs_filtrados['Coef_2'].iloc[0]
            c3 = coeffs_filtrados['Coef_3'].iloc[0]
            c4 = coeffs_filtrados['Coef_4'].iloc[0]
            
            # Aplicar la ecuación polinómica de 4to grado
            x = consumo_real_input
            peso_estimado = intercepto + (c1 * x) + (c2 * x**2) + (c3 * x**3) + (c4 * x**4)

            # 3. Cálculos comparativos
            cons_real_vs_guia_gr = consumo_real_input - consumo_guia
            cons_real_vs_guia_pct = (consumo_real_input / consumo_guia - 1) if consumo_guia != 0 else 0
            
            peso_real_vs_est_gr = peso_real_input - peso_estimado
            peso_real_vs_est_pct = (peso_real_input / peso_estimado - 1) if peso_estimado != 0 else 0
            
            conversion = consumo_real_input / peso_real_input if peso_real_input != 0 else 0

            # --- INICIO: Tabla de Referencia de la Guía ---
            st.subheader(f"Valores de Referencia GUIA {raza_seleccionada.upper()} {sexo_seleccionado.upper()} para el DÍA {dia_input}")

            # Filtrar el rango de días (3 antes y 3 después)
            dia_inicio = dia_input - 3
            dia_fin = dia_input + 3
            df_referencia = df_guia[
                (df_guia['RAZA'] == raza_seleccionada) &
                (df_guia['SEXO'] == sexo_seleccionado) &
                (df_guia['Dia'] >= dia_inicio) &
                (df_guia['Dia'] <= dia_fin)
            ]

            # Función para resaltar la fila del día seleccionado
            def highlight_day(row):
                if row['Dia'] == dia_input:
                    return ['background-color: #ffcccc'] * len(row)
                else:
                    return [''] * len(row)

            if not df_referencia.empty:
                # Calcular la columna de Conversión de la guía
                df_referencia.loc[:, 'Conversión'] = df_referencia['Cons_Acum'] / df_referencia['Peso']

                # Ocultar, reordenar y renombrar columnas para la visualización
                df_display = df_referencia.drop(columns=['RAZA', 'SEXO'])
                df_display = df_display[['Dia', 'Cons_Acum', 'Peso', 'Conversión']]
                df_display = df_display.rename(columns={'Cons_Acum': 'Consumo Acumulado'})

                # Aplicar el estilo y formato
                styled_df = df_display.style.apply(highlight_day, axis=1).format({
                    "Peso": "{:,.0f}",
                    "Consumo Acumulado": "{:,.0f}",
                    "Conversión": "{:.3f}"
                })
                st.dataframe(styled_df)
            else:
                st.warning("No se encontraron suficientes datos de referencia para mostrar la tabla de guías.")
            
            st.markdown("--- ") # Separador
            # --- FIN: Tabla de Referencia de la Guía ---

            # 4. Mostrar la tabla de resultados
            st.subheader(f"TABLA COMPARATIVA VALORES REALES VS GUÍA Y ESTIMADOS PARA CONSUMO – PESO, PARA {raza_seleccionada.upper()} Y {sexo_seleccionado.upper()} A LOS {dia_input} DÍAS")
            
            # Crear un DataFrame para la tabla horizontal
            resultados_df_horizontal = pd.DataFrame([{
                "Día": f"{dia_input}",
                "Consumo Real (gr)": f"{consumo_real_input:,.0f}",
                "Consumo Guía (gr)": f"{consumo_guia:,.0f}",
                "Consumo Real vs Guía (gr)": f"**{cons_real_vs_guia_gr:,.0f}**",
                "Consumo Real vs Guía (%)": f"**{cons_real_vs_guia_pct:.2%}**",
                "Peso Real (gr)": f"{peso_real_input:,.0f}",
                "Peso Estimado (gr)": f"{peso_estimado:,.2f}",
                "Peso Real vs Estimado (gr)": f"**{peso_real_vs_est_gr:,.2f}**",
                "Peso Real vs Estimado (%) ": f"**{peso_real_vs_est_pct:.2%}**",
                "Conversión Real": f"**{conversion:.3f}**"
            }])

            # Usar st.markdown para renderizar el DataFrame como una tabla HTML y poder usar negritas
            st.markdown(resultados_df_horizontal.to_markdown(index=False), unsafe_allow_html=True)

            st.markdown("---")

            # 5. Crear las gráficas
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Gráfica: Consumo Acumulado")
                fig1, ax1 = plt.subplots()
                
                # Datos de la guía para la gráfica
                guia_plot_data = df_guia[(df_guia['RAZA'] == raza_seleccionada) & (df_guia['SEXO'] == sexo_seleccionado)]
                
                ax1.plot(guia_plot_data['Dia'], guia_plot_data['Cons_Acum'], label='Consumo Guía', color='blue', linestyle='--')
                ax1.plot(dia_input, consumo_real_input, 'ro', label=f'Consumo Real (Día {dia_input})', markersize=8)
                
                ax1.set_xlabel("Día")
                ax1.set_ylabel("Consumo Acumulado (gramos)")
                ax1.set_title("Consumo Real vs. Consumo Guía")
                ax1.legend()
                ax1.grid(True, linestyle='--', alpha=0.6)
                
                if logo:
                    fig1.figimage(logo, xo=fig1.bbox.xmax*0.5 - logo.width*0.5, yo=fig1.bbox.ymax*0.5 - logo.height*0.5, alpha=0.15, zorder=1)

                st.pyplot(fig1)

            with col2:
                st.subheader("Gráfica: Peso")
                fig2, ax2 = plt.subplots()

                # Generar línea de peso estimado basada en un rango de consumos
                consumo_rango = np.linspace(guia_plot_data['Cons_Acum'].min(), guia_plot_data['Cons_Acum'].max(), 100)
                peso_estimado_rango = intercepto + (c1 * consumo_rango) + (c2 * consumo_rango**2) + (c3 * consumo_rango**3) + (c4 * consumo_rango**4)

                ax2.plot(consumo_rango, peso_estimado_rango, label='Peso Estimado (Modelo)', color='green')
                ax2.plot(consumo_real_input, peso_real_input, 'ro', label=f'Peso Real (Consumo {consumo_real_input:,.0f} gr)', markersize=8)
                
                ax2.set_xlabel("Consumo Acumulado (gramos)")
                ax2.set_ylabel("Peso (gramos)")
                ax2.set_title("Peso Real vs. Peso Estimado por Consumo")
                ax2.legend()
                ax2.grid(True, linestyle='--', alpha=0.6)

                if logo:
                    fig2.figimage(logo, xo=fig2.bbox.xmax*0.5 - logo.width*0.5, yo=fig2.bbox.ymax*0.5 - logo.height*0.5, alpha=0.15, zorder=1)

                st.pyplot(fig2)

# --- Pie de Página ---
st.markdown("---")
st.info(
    "**Nota de Responsabilidad:** Esta es una herramienta de apoyo para uso en granja. "
    "La utilización de los resultados es de su exclusiva responsabilidad. "
    "No sustituye la asesoría profesional y Albateq S.A. no se hace responsable por las decisiones tomadas con base en la información aquí presentada."
)
