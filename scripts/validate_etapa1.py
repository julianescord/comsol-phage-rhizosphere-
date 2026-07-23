"""
Validacion de la Etapa 1: FEM (COMSOL) vs. solucion analitica de Crank.

Caso de referencia: esfera de radio a con concentracion inicial uniforme c0
liberando por difusion en un medio infinito con el mismo D (Crank, "The
Mathematics of Diffusion", 2a ed., seccion 3.3):

    c(r,t)/c0 = 1/2 [ erf((a-r)/(2*sqrt(Dt))) + erf((a+r)/(2*sqrt(Dt))) ]
                - sqrt(Dt)/(r*sqrt(pi)) * [ exp(-(a-r)^2/(4Dt))
                                            - exp(-(a+r)^2/(4Dt)) ]

La formula se autoverifica aqui mismo por conservacion de masa antes de
usarse como referencia.

La comparacion se hace en TODOS los nodos de la malla, no solo sobre una
linea: como la solucion analitica depende solo de R = sqrt(r^2+z^2), el
test verifica simultaneamente la precision radial y la simetria esferica
de la solucion FEM.

Uso:
    ./mcp_server/venv/bin/python scripts/validate_etapa1.py
"""
import sys

import numpy as np
from scipy.special import erf
from scipy.integrate import quad

import mph

MPH = "/home/julianescord/Documentos/COMSOL/models/etapa1_difusion_pura.mph"
SOLVED = "/home/julianescord/Documentos/COMSOL/models/etapa1_difusion_pura_solved.mph"
OUT_CSV = "/home/julianescord/Documentos/COMSOL/models/etapa1_validacion.csv"
OUT_PNG = "/home/julianescord/Documentos/COMSOL/models/etapa1_validacion.png"


def crank_sphere(r, t, a, D, c0=1.0):
    """c(r,t) para una esfera con c0 uniforme liberando en medio infinito."""
    r = np.atleast_1d(np.asarray(r, float)).copy()
    r[r < 1e-15] = 1e-15                      # evita la singularidad 1/r
    s = 2.0 * np.sqrt(D * t)
    return c0 * (
        0.5 * (erf((a - r) / s) + erf((a + r) / s))
        - np.sqrt(D * t) / (r * np.sqrt(np.pi))
        * (np.exp(-((a - r) ** 2) / (4 * D * t))
           - np.exp(-((a + r) ** 2) / (4 * D * t)))
    )


def selfcheck(a, D):
    """La referencia debe conservar la masa inicial c0*(4/3)pi a^3."""
    M0 = 4.0 / 3.0 * np.pi * a ** 3
    print("--- autoverificacion de la solucion analitica ---")
    ok = True
    for t in (60.0, 3600.0, 86400.0):
        M, _ = quad(lambda r: 4 * np.pi * r ** 2 * crank_sphere(r, t, a, D)[0],
                    1e-12, a + 12 * np.sqrt(D * t), limit=400)
        err = M / M0 - 1
        ok &= abs(err) < 1e-3
        print(f"  t={t:8.0f} s   masa/masa0 - 1 = {err:+.3e}")
    print(f"  autoverificacion: {'OK' if ok else 'FALLO'}\n")
    return ok


def main():
    client = mph.start(cores=1)
    model = client.load(MPH)
    java = model.java

    par = {k: v for k, v in model.parameters().items()}
    a = model.evaluate("r_bead") if False else None   # se lee via java abajo
    # Evaluar los parametros a numero en unidades SI:
    a = float(java.param().evaluate("r_bead"))
    D = float(java.param().evaluate("D_phage"))
    c0 = float(java.param().evaluate("c0"))
    r_dom = float(java.param().evaluate("r_dom"))
    print(f"a (r_bead) = {a:.4e} m | D = {D:.4e} m^2/s | c0 = {c0} | r_dom = {r_dom:.4e} m")

    if not selfcheck(a, D):
        print("La referencia analitica no pasa su propia verificacion; abortando.")
        return 1

    import os
    if os.path.exists(SOLVED) and os.path.getmtime(SOLVED) > os.path.getmtime(MPH):
        print("--- reutilizando solucion cacheada ---")
        client.remove(model)
        model = client.load(SOLVED)
        java = model.java
    else:
        print("--- resolviendo el estudio ---")
        java.study("std1").run()
        model.save(SOLVED)
        print("resuelto.\n")

    times = np.array(java.sol("sol1").getPVals(), float)

    # Integral de masa en el dominio (2D axisimetrico -> revolucion incluida)
    # Balance de masa. Se calculan las dos convenciones posibles del operador
    # de integracion axisimetrico y se elige la que reproduce la masa exacta
    # en t=0, en vez de asumir cual usa COMSOL.
    c0_ = float(java.param().evaluate("c0"))
    a_ = float(java.param().evaluate("r_bead"))
    M0 = c0_ * 4.0 / 3.0 * np.pi * a_ ** 3
    cand = {
        "intop_all(c)": np.asarray(model.evaluate("intop_all(c)"), float).ravel(),
        "intop_all(2*pi*r*c)": np.asarray(
            model.evaluate("intop_all(2*pi*r*c)"), float).ravel(),
    }
    for k, v in cand.items():
        print(f"  {k:24s} en t=0: {v[0]:.6e}  (masa exacta {M0:.6e})")
    conv = min(cand, key=lambda k: abs(cand[k][0] / M0 - 1))
    mass = cand[conv]
    print(f"  convencion adoptada: {conv}")

    # Campos nodales: c en cada paso de tiempo + coordenadas
    cs = model.evaluate("c")
    rr = np.asarray(model.evaluate("r"))
    zz = np.asarray(model.evaluate("z"))
    if rr.ndim > 1:
        rr, zz = rr[0], zz[0]
    cs = np.asarray(cs)
    R = np.sqrt(rr ** 2 + zz ** 2)

    print(f"pasos de tiempo: {len(times)} | nodos: {R.size} | shape c: {cs.shape}")

    M0 = c0 * 4.0 / 3.0 * np.pi * a ** 3
    print("\n--- balance de masa en el FEM ---")
    print(f"  masa inicial teorica = {M0:.6e} mol")
    for i in (0, len(times) // 2, len(times) - 1):
        print(f"  t={times[i]/3600:6.2f} h   masa FEM = {mass[i]:.6e} "
              f"| error rel = {mass[i]/M0 - 1:+.3e}")

    print("\n--- FEM vs. analitico (todos los nodos) ---")
    print(f"{'t [h]':>8} {'err.abs.max/c0':>16} {'RMS/c0':>12} {'nodos usados':>13}")
    rows = []
    for i, t in enumerate(times):
        if t <= 0:
            continue
        # Solo la region no afectada por la frontera exterior finita:
        # a 6*sqrt(D t) del frente la solucion infinita es indistinguible de 0.
        valid = R < min(r_dom * 0.9, a + 6 * np.sqrt(D * t))
        if valid.sum() < 10:
            continue
        ana = crank_sphere(R[valid], t, a, D, c0)
        fem = cs[i][valid]
        dif = np.abs(fem - ana) / c0
        rows.append((t, dif.max(), np.sqrt((dif ** 2).mean()), valid.sum()))
        if i % max(1, len(times) // 8) == 0 or i == len(times) - 1:
            print(f"{t/3600:8.2f} {dif.max():16.3e} "
                  f"{np.sqrt((dif**2).mean()):12.3e} {valid.sum():13d}")

    arr = np.array([(t, e, r_, n) for t, e, r_, n in rows])
    np.savetxt(OUT_CSV, arr, delimiter=",",
               header="t_s,err_abs_max_norm,err_rms_norm,n_nodos", comments="")
    print(f"\nCSV: {OUT_CSV}")

    peor = arr[:, 1].max()
    print(f"\nPEOR error absoluto normalizado en todo el transitorio: {peor:.3e}")
    print("VEREDICTO:", "PASA" if peor < 0.02 else "REVISAR (>2% de c0)")

    # --- Figura de control: perfiles radiales FEM vs. analitico ---
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
        idx = [max(1, len(times) // 12), len(times) // 4, len(times) // 2, len(times) - 1]
        colors = plt.cm.viridis(np.linspace(0, .85, len(idx)))
        rq = np.linspace(1e-9, min(r_dom * 0.9, a * 8), 400)
        for k, i in enumerate(idx):
            t = times[i]
            sel = R < a * 8
            o = np.argsort(R[sel])
            ax[0].plot(R[sel][o] / a, cs[i][sel][o] / c0, ".", ms=2,
                       color=colors[k], alpha=.5)
            ax[0].plot(rq / a, crank_sphere(rq, t, a, D, c0) / c0, "-",
                       color=colors[k], lw=1.6, label=f"t = {t/3600:.1f} h")
        ax[0].axvline(1, ls=":", c="k", lw=.8)
        ax[0].set_xlabel("R / a"); ax[0].set_ylabel("c / c$_0$")
        ax[0].set_title("Puntos: FEM (todos los nodos) — Línea: Crank")
        ax[0].legend(fontsize=8, frameon=False)

        ax[1].semilogy(arr[:, 0] / 3600, arr[:, 1], "-o", ms=3, label="máx. |err|")
        ax[1].semilogy(arr[:, 0] / 3600, arr[:, 2], "-s", ms=3, label="RMS")
        ax[1].axhline(0.02, ls="--", c="r", lw=.8, label="umbral 2%")
        ax[1].set_xlabel("t [h]"); ax[1].set_ylabel("error / c$_0$")
        ax[1].set_title("Error FEM vs. analítico")
        ax[1].legend(fontsize=8, frameon=False)
        fig.tight_layout(); fig.savefig(OUT_PNG, dpi=150)
        print(f"Figura: {OUT_PNG}")
    except Exception as e:
        print("(figura omitida:", e, ")")

    return 0


if __name__ == "__main__":
    sys.exit(main())
