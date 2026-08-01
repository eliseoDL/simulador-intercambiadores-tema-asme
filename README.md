# 🔄 TEMA & ASME Heat Exchanger Digital Twin & Multicriteria Optimizer

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![CoolProp](https://img.shields.io/badge/Thermodynamics-CoolProp%20%2F%20IF97-008080)](http://www.coolprop.org/)
[![ASME](https://img.shields.io/badge/Code-ASME%20BPVC%20VIII%20%2F%20II--D-003366)](https://www.asme.org/)
[![OpenPyXL](https://img.shields.io/badge/Spreadsheets-LibreOffice%20Calc%20%2F%20Excel-1D6F42)](https://openpyxl.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Plataforma computacional de simulación termodinámica multifluido, ciclo de dimensionamiento y verificación convectiva (*Sizing & Rating*), diseño mecánico con selección de aleaciones y optimización combinatoria de costos (`CAPEX [USD]`) para Intercambiadores de Calor de Casco y Tubos industriales.**

---

## 🎯 Propuesta de Valor y Ciclo de Diseño (Sizing vs. Rating)

En el diseño industrial de intercambiadores bajo norma **TEMA / ASME BPVC VIII**, el cálculo del coeficiente global de transferencia $U$ presenta una iteración matemática obligatoria descrita por **Ray Sinnott & Gavin Towler** (*Chemical Engineering Design*, Cap. 12.3):

1. **Dimensionamiento (*Sizing*):** Se inicia el cálculo asumiendo un **Coeficiente $U_{\text{trial}}$ estimado de prueba `[W/m²·K]`** (Sinnott, Tabla 12.1) en función de la pareja de fluidos, con el fin de fijar la geometría física preliminar (área instalada, cantidad y longitud de tubos, diámetro de carcasa $D_s$ y espaciado de bafles).
2. **Verificación Convectiva (*Rating de Kern*):** Con la geometría ya establecida, el motor evalúa los regímenes hidrodinámicos (números de Reynolds y Nusselt) para obtener los coeficientes de película reales convectivos interior ($h_i$) y exterior ($h_o$), incorporando la conductividad del metal ($k_{\text{metal}}$) y la resistencia de ensuciamiento normada ($R_f$). Finalmente, determina el **$U_{\text{real}}$ calculado `[W/m²·K]`** y verifica que el equipo cuente con un **Margen de Seguridad Térmica `[%]`** positivo.

---

## 🧪 Rigor Termodinámico (`CoolProp`) y Materiales (ASME Sec. II-D)

El sistema se integra de forma nativa con la librería de código abierto **`CoolProp`**, resolviendo entalpías, viscosidades, densidades y calores específicos ($C_p$) reales mediante ecuaciones de estado Helmholtz/IAPWS para los principales fluidos de proceso en la industria química, Oil & Gas y energía:
*   `Agua Desmineralizada (Water)` | `Amoníaco Anhidro (Ammonia)` | `Etanol (Ethanol)`
*   `Propano Industrial (Propane)` | `Metano / Gas Natural (Methane)` | `Dióxido de Carbono (CO2)`
*   `Aire Seco (Air)` | `Benceno (Benzene)` | `Tolueno (Toluene)`

El módulo mecánico permite **seleccionar independientemente** los materiales normalizados para la **carcasa** y el **haz de tubos**, aplicando automáticamente su tensión admisible ($S$) para el espesor por presión interna y su conductividad térmica ($k_{\text{metal}}$) para la pared tubular:
*   `Acero al Carbono SA-516 Gr. 70 / SA-179` ($k = 50.0 \text{ W/m·K}$)
*   `Acero Inoxidable Austenítico Type 316 / 316L` ($k = 16.3 \text{ W/m·K}$)
*   `Cuproníquel SB-111 Cu-Ni 90/10` ($k = 52.0 \text{ W/m·K}$)
*   `Titanio SB-338 Gr. 2` ($k = 21.9 \text{ W/m·K}$)

---

## 🛠️ Arquitectura y Modos de Operación

La interfaz en **Streamlit** ofrece dos modalidades de trabajo profesional:

*   **⚙️ Modo 1 — Verificación y Simulación Manual:** Permite dimensionar un equipo dada una geometría específica elegida por el usuario, evaluando el perfil térmico en contracorriente y curvas de sensibilidad económica en tiempo real.
*   **🚀 Modo 2 — Optimizador e Inteligencia de Catálogo (*Grid Search*):** Ejecuta un barrido combinatorio automático sobre piezas normalizadas (**TEMA / BWG / longitudes estándar**), eliminando geometrías inviables por esbeltez estructural ($3 \le L/D_s \le 10$) o margen térmico negativo. Emite un ranking con **3 Tarjetas Top** (*Económico, Compacto y Operativo*) y genera una **Frontera de Pareto (CAPEX vs. Área)** para facilitar decisiones en ingeniería básica (*AACE Class 4/5 Estimate*).

---

## 📚 Normas, Estándares y Bases de Cálculo

| Parámetro / Módulo | Norma / Referencia | Base Técnica / Ecuación |
| :--- | :--- | :--- |
| **Propiedades de Fluido** | **CoolProp / IAPWS-IF97** | Entalpía, $C_p$, viscosidad $\mu$ y densidad $\rho$ a temperatura media de película. |
| **Sizing & Geometría** | **Sinnott & Towler (Cap. 12)** | Método de Kern, LMTD en contracorriente, factor $F_t$ de Bowman, bafles ($0.4 \cdot D_s$) y Tabla 12.1 para $U_{\text{trial}}$. |
| **Verificación ($U_{\text{real}}$)** | **Kern Rating (Sinnott Cap. 12.9)**| Ecuación **12.31** (Dittus-Boelter tubos), Eq. **12.39** (Kern casco), pared tubular y fouling de Tabla 12.2 ($R_f = 0.0003$). |
| **Estándar Constructivo** | **Norma TEMA Class R/C** | Nomenclatura constructiva de cabezales y carcasas (`BEM`, `AES`, `BEU`). |
| **Espesores y Materiales** | **ASME BPVC VIII / Sec. II-D**| Tensión admisible $S$ `[MPa]` por aleación, **UG-27(c)(1)** para casco y **UG-31 / BWG** para tubos. |
| **Estimación Económica** | **Sinnott & Towler (Cap. 6)** | Ecuación factorial de costo de adquisición (*AACE Class 4/5*): escalado por ley de potencia ($0.68$) sobre el área `[m²]` y factor de presión. |

---

## 📊 Emisión Oficial de Especificaciones (Equipment Data Sheet)

El software permite descargar en un clic la especificación del equipo diseñado o del candidato optimizado en dos formatos industriales con unidades explícitas (`[kW]`, `[kg/s]`, `[°C]`, `[mm]`, `[W/m²·K]`, `[USD]`):
*   **Planilla Editable (`.xlsx`):** Compatible 100% con **LibreOffice Calc** y Microsoft Excel, lista para personalizaciones o revisiones de proyecto.
*   **Reporte Inmutable (`.pdf`):** Pliego técnico formato A4 de página única normado bajo directrices API/ASME, listo para adjuntar a memorias de cálculo de licitación.

---

## 🚀 Demo en Vivo

> **🔗 [Ejecutar App Interactiva en Streamlit Community Cloud](https://simulador-intercambiadores-tema-asme-q97fjg4w7y49xnmnxnghcx.streamlit.app/)**  
> *(Nota: Reemplaza este enlace al desplegar tu app en la nube).*

---

## 💻 Instalación y Ejecución Local

### 1. Clonar el repositorio
```bash
git clone [https://github.com/tu-usuario/intercambiador-tema-asme.git](https://github.com/tu-usuario/intercambiador-tema-asme.git)
cd intercambiador-tema-asme
