"""
Verificacion de la Etapa 2, por partes y contra soluciones exactas.

La estrategia es la misma que en la Etapa 1: llevar el modelo a una
configuracion DEGENERADA en la que existe solucion analitica, verificar ahi
cada termino nuevo por separado, y solo entonces usarlo en la configuracion
realista.

  Check A — inactivacion. Medio uniforme (sin nodo de bead), tortuosidad
    tau=1, porosidad eps != 1, k_inact > 0. Como el decaimiento es uniforme,
    la solucion exacta es Crank(r,t) * exp(-k_ef*t). Sirve para determinar
    EMPIRICAMENTE si COMSOL aplica la tasa como k o como k/eps, en vez de
    confiar en la documentacion del nodo Reactions.

  Check B — tortuosidad de Millington-Quirk. Medio uniforme, k_inact = 0,
    porosidad eps != 1 con el modelo MQ. La solucion exacta es Crank con una
    difusividad APARENTE D_app. Se determina D_app por ajuste y se compara
    contra las formas candidatas eps^m * D para identificar cual usa COMSOL.

Ambos checks son necesarios porque una convencion equivocada en cualquiera de
los dos escalaria silenciosamente todos los resultados de la Etapa 2.

Uso:
    ./mcp_server/venv/bin/python scripts/validate_etapa2.py
"""
import os
import sys

import numpy as np
import mph

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analytic import crank_sphere, selfcheck            # noqa: E402
from build_etapa2 import build, DEFAULTS                 # noqa: E402

TMP = "/tmp/etapa2_check.mph"


def solve_case(client, overrides, tortuosity_soil, uniform_medium):
    """Construye y resuelve una variante, devolviendo campos nodales."""
    params = dict(DEFAULTS)
    params.update(overrides)
    _client, model, _geom, _mesh = build(
        params, TMP, tortuosity_soil, uniform_medium, client=client, verbose=False)
    return model, params


def fields(model):
    java = model.java
    java.study("std1").run()
    times = np.array(java.sol("sol1").getPVals(), float)
    cs = np.asarray(model.evaluate("c"))
    rr = np.asarray(model.evaluate("r"))
    zz = np.asarray(model.evaluate("z"))
    if rr.ndim > 1:
        rr, zz = rr[0], zz[0]
    return times, cs, np.sqrt(rr ** 2 + zz ** 2)


def err_vs(cs, times, R, a, D_app, k_eff, c0, r_dom, D_ref):
    """Error maximo normalizado entre el FEM y Crank(D_app)*exp(-k_eff t)."""
    peor = 0.0
    for i, t in enumerate(times):
        if t <= 0:
            continue
        valid = R < min(r_dom * 0.9, a + 6 * np.sqrt(D_ref * t))
        if valid.sum() < 10:
            continue
        ana = crank_sphere(R[valid], t, a, D_app, c0) * np.exp(-k_eff * t)
        peor = max(peor, np.abs(cs[i][valid] - ana).max() / c0)
    return peor


def main():
    client = mph.start(cores=1)
    a = 250e-6
    D_w = 2.2e-12
    eps = 0.45
    c0 = 1.0
    r_dom = 20 * a

    if not selfcheck(a, D_w):
        print("La referencia analitica no pasa su propia verificacion.")
        return 1

    # ================= Check A: inactivacion =========================
    print("=" * 68)
    print("Check A — termino de inactivacion (medio uniforme, tau=1)")
    print("=" * 68)
    k = 0.5 / 86400.0                      # 0.5 1/d en 1/s
    model, _ = solve_case(
        client,
        {"eps_soil": str(eps), "eps_bead": str(eps), "D_water": "2.2e-12[m^2/s]",
         "k_inact": "0.5[1/d]", "k_att": "0[1/d]",
         "t_end": "24[h]", "n_steps": "48", "n_dom": "20"},
        tortuosity_soil="uniforme", uniform_medium=True)
    times, cs, R = fields(model)
    print(f"  pasos: {len(times)} | nodos: {R.size}")

    cands = {"k_ef = k_inact": k, "k_ef = k_inact/eps": k / eps,
             "k_ef = k_inact*eps": k * eps, "k_ef = 0 (sin reaccion)": 0.0}
    resA = {name: err_vs(cs, times, R, a, D_w, kk, c0, r_dom, D_w)
            for name, kk in cands.items()}
    for name, e in sorted(resA.items(), key=lambda kv: kv[1]):
        print(f"    {name:28s} error max = {e:.3e}")
    bestA = min(resA, key=resA.get)
    print(f"\n  --> COMSOL aplica: {bestA}  (error {resA[bestA]:.3e})")
    okA = resA[bestA] < 0.02 and bestA == "k_ef = k_inact"
    print(f"  Check A: {'PASA' if okA else 'REVISAR'} "
          f"— se esperaba que ReactingVolumeType='PoreVolume' diera k_ef = k_inact")
    client.remove(model)

    # ================= Check B: Millington-Quirk =====================
    print("\n" + "=" * 68)
    print("Check B — difusividad efectiva de Millington-Quirk")
    print("=" * 68)
    model, _ = solve_case(
        client,
        {"eps_soil": str(eps), "eps_bead": str(eps), "D_water": "2.2e-12[m^2/s]",
         "k_inact": "0[1/d]", "k_att": "0[1/d]",
         "t_end": "24[h]", "n_steps": "48", "n_dom": "20"},
        tortuosity_soil="mq", uniform_medium=True)
    times, cs, R = fields(model)

    print("  formas candidatas D_app = eps^m * D_water:")
    resB = {}
    for m in (0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0, 4.0 / 3.0, 7.0 / 3.0):
        D_app = D_w * eps ** m
        resB[m] = err_vs(cs, times, R, a, D_app, 0.0, c0, r_dom, D_w)
        print(f"    m = {m:5.3f}  D_app = {D_app:.4e}   error max = {resB[m]:.3e}")
    bestm = min(resB, key=resB.get)

    # Ajuste libre, por si ninguna forma candidata es la correcta
    grid = D_w * np.logspace(-1, 0.3, 60)
    errs = [err_vs(cs, times, R, a, d, 0.0, c0, r_dom, D_w) for d in grid]
    D_fit = grid[int(np.argmin(errs))]
    print(f"\n  ajuste libre: D_app = {D_fit:.4e} m^2/s "
          f"= eps^{np.log(D_fit/D_w)/np.log(eps):.3f} * D_water")
    print(f"  mejor candidato: m = {bestm:.3f} (error {resB[bestm]:.3e})")
    okB = resB[bestm] < 0.02
    print(f"  Check B: {'PASA' if okB else 'REVISAR'}")
    client.remove(model)

    print("\n" + "=" * 68)
    print(f"RESULTADO: Check A {'PASA' if okA else 'REVISAR'} | "
          f"Check B {'PASA' if okB else 'REVISAR'}")
    print("=" * 68)
    return 0 if (okA and okB) else 1


if __name__ == "__main__":
    sys.exit(main())
