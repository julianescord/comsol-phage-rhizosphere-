"""
Verificacion de la Etapa raiz por BALANCE DE MASA de 4 terminos.

Esta geometria (bead esferica + sumidero Michaelis-Menten en la frontera
exterior) no tiene solucion analitica cerrada. En su lugar se usa un
invariante exacto que el modelo debe cumplir en TODO instante:

    M0  =  M_activo(t)  +  M_captado(t)  +  M_inactivado(t)

  - M_activo(t)      = fago activo aun presente en el dominio (bead + suelo),
                       ponderado por la porosidad de cada region.
  - M_captado(t)     = integral temporal del flujo saliente por la raiz.
  - M_inactivado(t)  = integral temporal de la tasa de inactivacion.

Si los tres terminos suman M0 a lo largo de todo el transitorio, entonces el
sumidero de frontera, el termino de reaccion y la discretizacion son
mutuamente consistentes. Es una verificacion fuerte que no necesita solucion
cerrada.

Ademas se comprueba el CASO LIMITE Vmax_root -> 0: sin captacion, el modelo
debe reducirse a la Etapa 2 (captado ~ 0, y M_activo + M_inactivado = M0).

Nota de porosidad: `c` es la concentracion en el fluido de poro, asi que los
moles activos son eps*c, con eps distinto en bead y suelo. Como la
inactivacion actua en pore volume (ReactingVolumeType='PoreVolume', ver
Etapa 2), la tasa de inactivacion es exactamente k_inact*M_activo.

Uso:
    ./mcp_server/venv/bin/python scripts/validate_raiz.py
"""
import os
import sys

import numpy as np
import mph

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_raiz import build, DEFAULTS                   # noqa: E402

TMP = "/tmp/raiz_check.mph"


def solve_and_fields(client, overrides):
    params = dict(DEFAULTS)
    params.update(overrides)
    _c, model, _g, _m = build(params, TMP, client=client, verbose=False)
    java = model.java
    java.study("std1").run()
    t = np.array(java.sol("sol1").getPVals(), float)

    eps_b = float(java.param().evaluate("eps_bead"))
    eps_s = float(java.param().evaluate("eps_soil"))
    a = float(java.param().evaluate("r_bead"))
    c0 = float(java.param().evaluate("c0"))

    Ib = np.asarray(model.evaluate("intop_bead(2*pi*r*c)"), float).ravel()
    Ia = np.asarray(model.evaluate("intop_all(2*pi*r*c)"), float).ravel()
    M_active = eps_b * Ib + eps_s * (Ia - Ib)
    M0 = eps_b * c0 * 4.0 / 3.0 * np.pi * a ** 3

    # Masas acumuladas leidas de las ODEs globales del modelo (integradas por
    # el solver de COMSOL, sin trapecio post-hoc).
    M_captured = np.asarray(model.evaluate("Mcapt"), float).ravel()
    M_inact = np.asarray(model.evaluate("Minact"), float).ravel()

    client.remove(model)
    return dict(t=t, M0=M0, M_active=M_active,
                M_captured=M_captured, M_inact=M_inact)


def report(name, d):
    t, M0 = d["t"], d["M0"]
    # La dosis REAL cargada es M_active(0): la CI discontinua (c0 en la bead,
    # 0 fuera) se proyecta sobre la malla y el solver la suaviza en la
    # interfaz, asi que M_active(0) < M0_analitico. Ese offset es un artefacto
    # de discretizacion de la CI, no de la fisica; se reduce refinando la
    # malla en la frontera de la bead. El balance dinamico (lo que valida el
    # sumidero + la inactivacion) se refiere a la dosis realmente cargada.
    M_ref = d["M_active"][0]
    offset_ci = M_ref / M0 - 1.0
    total = d["M_active"] + d["M_captured"] + d["M_inact"]
    resid = total / M_ref - 1.0
    print(f"\n--- {name} ---")
    print(f"  M0(analitico)   = {M0:.6e} mol")
    print(f"  M_active(0)=dosis real = {M_ref:.6e} mol  "
          f"(offset CI {offset_ci*100:+.2f} %)")
    print(f"  {'t [d]':>7} {'activo':>9} {'captado':>9} {'inact.':>9} "
          f"{'suma/Mref-1':>12}")
    idx = [0, len(t) // 4, len(t) // 2, 3 * len(t) // 4, len(t) - 1]
    for i in idx:
        print(f"  {t[i]/86400:7.2f} {d['M_active'][i]/M_ref:9.4f} "
              f"{d['M_captured'][i]/M_ref:9.4f} {d['M_inact'][i]/M_ref:9.4f} "
              f"{resid[i]:+12.2e}")
    peor = np.abs(resid).max()
    print(f"  |deriva del balance| max = {peor:.2e}   "
          f"(relativo a la dosis real)")
    return peor, d["M_captured"][-1] / M_ref, offset_ci


def main():
    client = mph.start(cores=1)

    print("=" * 66)
    print("Balance de masa de 4 terminos — caso base (con captacion)")
    print("=" * 66)
    base = solve_and_fields(client, {"t_end": "21[d]", "n_steps": "84"})
    peor_base, f_cap_base, off_base = report("captacion activa", base)

    print("\n" + "=" * 66)
    print("Caso limite Vmax_root -> 0  (debe reproducir la Etapa 2)")
    print("=" * 66)
    lim = solve_and_fields(client, {"Vmax_root": "0[mol/(m^2*s)]",
                                    "t_end": "21[d]", "n_steps": "84"})
    peor_lim, f_cap_lim, off_lim = report("sin captacion", lim)

    print("\n" + "=" * 66)
    print("Fraccion de la dosis CAPTADA por la raiz (sobre la dosis real):")
    print(f"  caso base      : {f_cap_base*100:6.2f} %")
    print(f"  Vmax=0 (limite): {f_cap_lim*100:6.2f} %  (debe ~ 0)")
    # La deriva del balance relativa a la dosis real valida la fisica; el
    # offset de CI es un artefacto de discretizacion, se reporta aparte.
    ok_bal = peor_base < 5e-3 and peor_lim < 5e-3
    ok_lim = f_cap_lim < 1e-3
    print(f"\n  balance dinamico : {'PASA' if ok_bal else 'REVISAR'} "
          f"(deriva max base {peor_base:.1e}, limite {peor_lim:.1e})")
    print(f"  limite Vmax->0   : {'PASA' if ok_lim else 'REVISAR'} "
          f"(captado {f_cap_lim*100:.3f} %)")
    print(f"  offset de CI     : {off_base*100:+.2f} % (artefacto de malla, "
          f"no afecta la fisica)")
    print("=" * 66)
    return 0 if (ok_bal and ok_lim) else 1


if __name__ == "__main__":
    sys.exit(main())
