# =======================================================
# 🎯 SIMULADOR MONTECARLO RUSHAPO – Versión Completa
# =======================================================
"""
Simulador Monte Carlo basado en xG para estimar resultados probables en un partido.

Mejoras realizadas:
- Bloque main para permitir importarlo desde otras apps (web/API) sin ejecutar gráficos.
- Función de exportación a Excel con fallback si no está instalado xlsxwriter.
- Pequeñas validaciones y docstrings.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from itertools import product

try:
    from google.colab import files
except:
    files = None

# ---------- PARÁMETROS DE ENTRADA (ejemplo por defecto) ----------
params = {
    "equipo_local": "Boca Juniors",
    "equipo_visit": "River Plate",
    "xGF_local_prom": 1.65,
    "xGA_local_prom": 1.14,
    "xGF_visit_prom": 1.39,
    "xGA_visit_prom": 1.22,
    # Nuevos (promedio por partido en los últimos 10, opcional)
    "gf_local_10": None,
    "ga_local_10": None,
    "gf_visit_10": None,
    "ga_visit_10": None,
    # Promedio de goles totales por partido de la liga (para derivar xG_liga_equipo = goles_liga_prom/2)
    "goles_liga_prom": None,
    "xG_liga_equipo": 0.98,
    "HFA": 1.09,
    "sigma": 0.3,
    "n_sims": 10000,
    "seed": 42
}

# ---------- FUNCIONES ----------
def shock_lognormal(size, sigma):
    """Devuelve choques multiplicativos lognormales con media 1.

    mean(log) = -0.5*sigma^2 asegura E[shock]=1.
    """
    mu = -0.5 * sigma**2
    return np.random.lognormal(mean=mu, sigma=sigma, size=size)

def sim_partido_xg(p):
    """Simula marcadores g_loc y g_vis a partir de parámetros tipo xG.

    p: dict con claves esperadas
       - xGF_local_prom, xGA_local_prom, xGF_visit_prom, xGA_visit_prom
       - xG_liga_equipo, HFA, sigma, n_sims, seed
    """
    if p.get("seed") is not None:
        np.random.seed(p["seed"])
    n = int(p.get("n_sims", 10000))
    sigma = float(p.get("sigma", 0.3))
    HFA = float(p.get("HFA", 1.0))
    xG_liga = float(p.get("xG_liga_equipo", 1.0)) or 1.0

    # Mezcla xG con goles recientes (prom últimos 10) si están disponibles
    def _blend(xg, goles):
        try:
            return 0.7 * float(xg) + 0.3 * float(goles)
        except (TypeError, ValueError):
            return float(xg)

    xGF_local_adj = _blend(p.get("xGF_local_prom"), p.get("gf_local_10"))
    xGA_local_adj = _blend(p.get("xGA_local_prom"), p.get("ga_local_10"))
    xGF_visit_adj = _blend(p.get("xGF_visit_prom"), p.get("gf_visit_10"))
    xGA_visit_adj = _blend(p.get("xGA_visit_prom"), p.get("ga_visit_10"))

    # Ajuste con choques lognormales
    xGF_loc_draw = xGF_local_adj * shock_lognormal(n, sigma)
    xGA_vis_draw = xGA_visit_adj * shock_lognormal(n, sigma)
    xGF_vis_draw = xGF_visit_adj * shock_lognormal(n, sigma)
    xGA_loc_draw = xGA_local_adj * shock_lognormal(n, sigma)

    lam_loc = np.clip(HFA * (xGF_loc_draw * xGA_vis_draw) / xG_liga, 1e-6, None)
    lam_vis = np.clip((1.0/HFA) * (xGF_vis_draw * xGA_loc_draw) / xG_liga, 1e-6, None)

    g_loc = np.random.poisson(lam=lam_loc)
    g_vis = np.random.poisson(lam=lam_vis)
    df = pd.DataFrame({"g_loc": g_loc, "g_vis": g_vis})
    df["res"] = np.select([df.g_loc>df.g_vis, df.g_loc<df.g_vis], ["Local","Visitante"], default="Empate")
    df["over25"] = (df.g_loc+df.g_vis)>2
    df["btts"] = (df.g_loc>0)&(df.g_vis>0)
    return df

def resumen_estadistico(df):
    """Genera métricas resumidas a partir del dataframe de simulación."""
    resumen = pd.Series({
        "% Local": (df.res=="Local").mean(),
        "% Empate": (df.res=="Empate").mean(),
        "% Visitante": (df.res=="Visitante").mean(),
        "% Over 2.5": df.over25.mean(),
        "% BTTS": df.btts.mean(),
        "Goles loc": df.g_loc.mean(),
        "Goles vis": df.g_vis.mean(),
        "Goles tot": (df.g_loc+df.g_vis).mean()
    })
    # Over 3.5
    resumen["% Over 3.5"] = ((df.g_loc + df.g_vis) > 3).mean()
    goles_sum = resumen["Goles loc"] + resumen["Goles vis"]
    if goles_sum > 0:
        resumen["Efectividad local"] = resumen["Goles loc"]/goles_sum
        resumen["Efectividad visitante"] = resumen["Goles vis"]/goles_sum
    else:
        resumen["Efectividad local"] = 0.0
        resumen["Efectividad visitante"] = 0.0
    return resumen

def export_rushapo_excel(params,resumen,top_scores,sens_df,cuotas_df,df,file_name="Rushapo_Simulacion_Completa.xlsx"):
    """Exporta un reporte a Excel.

    Usa xlsxwriter si está disponible para formatear. Si no, exporta una versión simple.
    """
    try:
        import xlsxwriter  # noqa: F401
        engine = "xlsxwriter"
        styled = True
    except Exception:
        engine = None  # Deja que Pandas elija (normalmente openpyxl)
        styled = False

    if styled:
        with pd.ExcelWriter(file_name, engine="xlsxwriter") as writer:
            wb = writer.book
            negro, dorado, gris = "#0B0B0C", "#D4AF37", "#F2F2F2"
            fmt_t = wb.add_format({"bold": True, "font_size": 20, "font_color": dorado, "bg_color": negro, "align": "center"})
            fmt_h = wb.add_format({"bold": True, "font_color": "#000000", "bg_color": gris, "border": 1, "align": "center"})
            pct = wb.add_format({"num_format": "0.00%", "border": 1, "align": "center"})
            num = wb.add_format({"num_format": "0.00", "border": 1, "align": "center"})
            txt = wb.add_format({"border": 1, "align": "center"})

            # --- RESUMEN ---
            resumen_df = resumen.rename("Valor").to_frame().reset_index(); resumen_df.columns = ["Métrica", "Valor"]
            resumen_df.to_excel(writer, sheet_name="Resumen", index=False, startrow=10, startcol=1)
            ws = writer.sheets["Resumen"]
            ws.merge_range(1, 1, 2, 9, f"RUSHAPO – Simulación Monte Carlo (xG)", fmt_t)
            ws.write(4, 1, "Partido", fmt_h); ws.merge_range(4, 2, 4, 6, f'{params["equipo_local"]} vs {params["equipo_visit"]}', txt)
            ws.write(5, 1, "Fecha", fmt_h); ws.merge_range(5, 2, 5, 6, datetime.now().strftime("%Y-%m-%d %H:%M"), txt)
            ws.write(6, 1, "HFA", fmt_h); ws.write(6, 2, params["HFA"], num)
            ws.write(6, 3, "σ (volatilidad)", fmt_h); ws.write(6, 4, params["sigma"], num)
            ws.write(6, 5, "Simulaciones", fmt_h); ws.write(6, 6, params["n_sims"], num)
            for r in range(len(resumen_df)):
                label = resumen_df.iloc[r, 0]; val = float(resumen_df.iloc[r, 1])
                ws.write(11 + r, 1, label, txt)
                ws.write(11 + r, 2, val, pct if "%" in label else num)

            # --- MARCADORES ---
            top_scores.to_excel(writer, sheet_name="Marcadores", index=False, startrow=3, startcol=1)
            ws2 = writer.sheets["Marcadores"]
            ws2.merge_range(1, 1, 1, 5, "RUSHAPO – Marcadores más probables", fmt_t)
            for c, h in enumerate(top_scores.columns, start=1): ws2.write(3, c, h, fmt_h)
            ws2.set_column(1, 3, 15)

            # --- SENSIBILIDAD ---
            sens_df.to_excel(writer, sheet_name="Sensibilidad", index=False, startrow=3, startcol=1)
            ws3 = writer.sheets["Sensibilidad"]
            ws3.merge_range(1, 1, 1, 6, "RUSHAPO – Análisis de Sensibilidad", fmt_t)
            for c, h in enumerate(sens_df.columns, start=1): ws3.write(3, c, h, fmt_h)
            ws3.set_column(1, 6, 15)

            # --- CUOTAS & EV ---
            cuotas_df.to_excel(writer, sheet_name="Cuotas & EV", index=False, startrow=3, startcol=1)
            ws4 = writer.sheets["Cuotas & EV"]
            ws4.merge_range(1, 1, 1, 8, "RUSHAPO – Cuotas & Value Bets", fmt_t)
            for c, h in enumerate(cuotas_df.columns, start=1): ws4.write(3, c, h, fmt_h)
            ws4.set_column(1, 8, 15)

            # --- SIMULACIONES (opcional) ---
            df.to_excel(writer, sheet_name="Simulaciones", index=False)
    else:
        # Exportación simple sin estilos
        with pd.ExcelWriter(file_name) as writer:
            resumen.rename("Valor").to_frame().reset_index().to_excel(writer, sheet_name="Resumen", index=False)
            top_scores.to_excel(writer, sheet_name="Marcadores", index=False)
            sens_df.to_excel(writer, sheet_name="Sensibilidad", index=False)
            cuotas_df.to_excel(writer, sheet_name="Cuotas & EV", index=False)
            df.to_excel(writer, sheet_name="Simulaciones", index=False)

    return file_name


def run_simulacion_completa(p=None, mostrar_graficos=True, exportar_excel=True):
    """Ejecuta la simulación completa con gráficos y exportación opcional.

    Retorna un diccionario con objetos claves de la corrida.
    """
    p = p or params
    df = sim_partido_xg(p)
    resumen = resumen_estadistico(df)
    # Añadir al resumen los parámetros ajustados para transparencia
    def _blend(xg, goles):
        try:
            return 0.7 * float(xg) + 0.3 * float(goles)
        except (TypeError, ValueError):
            return float(xg)
    xGF_local_adj = _blend(p.get("xGF_local_prom"), p.get("gf_local_10"))
    xGA_local_adj = _blend(p.get("xGA_local_prom"), p.get("ga_local_10"))
    xGF_visit_adj = _blend(p.get("xGF_visit_prom"), p.get("gf_visit_10"))
    xGA_visit_adj = _blend(p.get("xGA_visit_prom"), p.get("ga_visit_10"))
    resumen["xGF local (ajust)"] = xGF_local_adj
    resumen["xGA local (ajust)"] = xGA_local_adj
    resumen["xGF visit (ajust)"] = xGF_visit_adj
    resumen["xGA visit (ajust)"] = xGA_visit_adj
    score_counts = df.groupby(["g_loc", "g_vis"]).size().sort_values(ascending=False)
    top_scores = (score_counts.head(10) / len(df)).rename("Prob").reset_index()

    # ---------- CUOTAS Y VALUE BETS BASE (sin odds externas) ----------
    # Se calculan cuotas justas a partir de las probabilidades simuladas.
    mercados_prob = {
        "Local": resumen.get("% Local"),
        "Empate": resumen.get("% Empate"),
        "Visitante": resumen.get("% Visitante"),
        "Over 2.5": resumen.get("% Over 2.5"),
        "BTTS": resumen.get("% BTTS"),
        "Under 2.5": 1 - resumen.get("% Over 2.5", 0),
        "BTTS No": 1 - resumen.get("% BTTS", 0),
        "Over 3.5": resumen.get("% Over 3.5"),
        "Under 3.5": 1 - resumen.get("% Over 3.5", 0),
    }
    cuotas_base_rows = []
    for mercado, pmerc in mercados_prob.items():
        if pmerc and pmerc > 0:
            cuotas_base_rows.append({
                "Mercado": mercado,
                "Prob": pmerc,
                "Cuota justa": 1 / pmerc,
            })
    cuotas_df = pd.DataFrame(cuotas_base_rows)

    # ---------- SENSIBILIDAD ----------
    HFA_values, sigma_values = [1.05, 1.10, 1.15], [0.2, 0.3, 0.4]
    sensibilidad = []
    for h, s in product(HFA_values, sigma_values):
        p2 = p.copy(); p2["HFA"] = h; p2["sigma"] = s
        df_temp = sim_partido_xg(p2); r = resumen_estadistico(df_temp)
        sensibilidad.append({
            "HFA": h, "σ": s, "Local": r["% Local"], "Empate": r["% Empate"], "Visitante": r["% Visitante"]
        })
    sens_df = pd.DataFrame(sensibilidad)

    if mostrar_graficos:
        try:
            plt.figure(figsize=(6, 4))
            plt.hist(df.g_loc + df.g_vis, bins=range(0, 8), rwidth=0.8)
            plt.title("Distribución de Goles Totales")
            plt.xlabel("Goles"); plt.ylabel("Frecuencia"); plt.show()

            res_counts = df.res.value_counts(normalize=True)
            res_counts.plot(kind="bar", color=["#66bb6a", "#ffee58", "#ef5350"])
            plt.title("Probabilidad de Resultado"); plt.ylabel("Probabilidad"); plt.show()

            sns.heatmap(
                sens_df.pivot(index="HFA", columns="σ", values="Local"),
                annot=True,
                cmap="YlGnBu"
            )
            plt.title("Probabilidad de Victoria Local (Sensibilidad)"); plt.show()
        except Exception as e:
            print("[Aviso] No se pudieron mostrar gráficos:", e)

    excel_path = None
    if exportar_excel:
        try:
            excel_path = export_rushapo_excel(p, resumen, top_scores, sens_df, cuotas_df, df)
            print("✅ Archivo generado:", excel_path)
            if files:
                files.download(excel_path)
        except Exception as e:
            print("[Aviso] Falló la exportación a Excel:", e)

    return {
        "df": df,
        "resumen": resumen,
        "top_scores": top_scores,
        "cuotas_base": cuotas_df,
        "sens_df": sens_df,
        "excel": excel_path,
    }


if __name__ == "__main__":
    # Ejecución directa de ejemplo
    resultados = run_simulacion_completa(params, mostrar_graficos=True, exportar_excel=True)
    print(resultados["resumen"])
