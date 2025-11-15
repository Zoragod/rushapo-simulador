from flask import Flask, render_template, request
from simulador_rushapo import run_simulacion_completa, params as default_params

app = Flask(__name__)


def _to_float(val, default):
    try:
        if val is None or val == "":
            return float(default)
        return float(str(val).replace(",", "."))
    except Exception:
        return float(default)


def _to_int(val, default):
    try:
        return int(val)
    except Exception:
        return int(default)


@app.route("/", methods=["GET"])
@app.route("/simular", methods=["GET", "POST"])
def simular():
    resumen = None
    top_scores = []
    current = default_params.copy()
    odds_current = {
        "Local": request.form.get("odds_Local", ""),
        "Empate": request.form.get("odds_Empate", ""),
        "Visitante": request.form.get("odds_Visitante", ""),
        "Over 2.5": request.form.get("odds_Over 2.5", ""),
        "Under 2.5": request.form.get("odds_Under 2.5", ""),
        "Over 3.5": request.form.get("odds_Over 3.5", ""),
        "Under 3.5": request.form.get("odds_Under 3.5", ""),
        "BTTS": request.form.get("odds_BTTS", ""),
        "BTTS No": request.form.get("odds_BTTS No", ""),
    }

    if request.method == "POST":
        form = request.form
        p = {
            "equipo_local": form.get("equipo_local", current["equipo_local"]),
            "equipo_visit": form.get("equipo_visit", current["equipo_visit"]),
            "xGF_local_prom": _to_float(form.get("xGF_local_prom"), current["xGF_local_prom"]),
            "xGA_local_prom": _to_float(form.get("xGA_local_prom"), current["xGA_local_prom"]),
            "xGF_visit_prom": _to_float(form.get("xGF_visit_prom"), current["xGF_visit_prom"]),
            "xGA_visit_prom": _to_float(form.get("xGA_visit_prom"), current["xGA_visit_prom"]),
            # Nuevos: goles últimos 10 (prom por partido)
            "gf_local_10": _to_float(form.get("gf_local_10"), current.get("gf_local_10") or current["xGF_local_prom"]),
            "ga_local_10": _to_float(form.get("ga_local_10"), current.get("ga_local_10") or current["xGA_local_prom"]),
            "gf_visit_10": _to_float(form.get("gf_visit_10"), current.get("gf_visit_10") or current["xGF_visit_prom"]),
            "ga_visit_10": _to_float(form.get("ga_visit_10"), current.get("ga_visit_10") or current["xGA_visit_prom"]),
            # Promedio de goles totales de la liga (si se da, derivamos xG liga = goles/2)
            "goles_liga_prom": _to_float(form.get("goles_liga_prom"), current.get("goles_liga_prom") or 2*current["xG_liga_equipo"]),
            "xG_liga_equipo": _to_float(form.get("xG_liga_equipo"), current["xG_liga_equipo"]),
            "HFA": _to_float(form.get("HFA"), current["HFA"]),
            "sigma": _to_float(form.get("sigma"), current["sigma"]),
            "n_sims": _to_int(form.get("n_sims"), current["n_sims"]),
            "seed": current.get("seed", 42),
        }

        # Recalcular xG liga si se proporcionó goles_liga_prom válido
        if p.get("goles_liga_prom") and p["goles_liga_prom"] > 0:
            p["xG_liga_equipo"] = p["goles_liga_prom"] / 2.0
        result = run_simulacion_completa(p, mostrar_graficos=False, exportar_excel=False)
        resumen = result["resumen"].to_dict()
        top_scores = result["top_scores"].to_dict(orient="records")

        # Calcular cuotas justas y EV con odds ingresadas (si están)
        cuotas_base = result["cuotas_base"]
        # Convertimos a dict para fácil lookup
        prob_map = {row["Mercado"]: row["Prob"] for _, row in cuotas_base.iterrows()}

        rows = []
        for mercado, prob in prob_map.items():
            cuota_book_str = odds_current.get(mercado, "").strip()
            try:
                cuota_book = float(cuota_book_str.replace(",", ".")) if cuota_book_str else None
            except Exception:
                cuota_book = None
            row = {
                "Mercado": mercado,
                "Prob (sim)": prob,
                "Cuota justa": (1.0 / prob) if prob > 0 else None,
                "Cuota book": cuota_book,
                "Prob implícita": (1.0 / cuota_book) if cuota_book and cuota_book > 0 else None,
                "EV": (prob * cuota_book - 1.0) if cuota_book and cuota_book > 0 else None,
            }
            rows.append(row)
        cuotas_view = rows
        current = p
    else:
        cuotas_view = []

    return render_template(
        "index.html",
        resumen=resumen,
        top_scores=top_scores,
        current=current,
        odds_current=odds_current,
        cuotas=cuotas_view,
    )


if __name__ == "__main__":
    # Ejecutar servidor local
    app.run(host="0.0.0.0", port=5000, debug=True)
