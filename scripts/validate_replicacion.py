"""
Verificacion de la etapa replicacion.

El sistema acoplado no lineal (2 especies, reaccion-difusion depredador-presa)
no tiene solucion analitica cerrada. Se verifica de dos formas independientes:

  Check A — caso BIEN MEZCLADO vs ODE.  En un dominio pequeño con difusividades
    altas y CI uniformes, el campo se homogeniza y el sistema espacial se
    reduce a la ODE de Lotka-Volterra:
        dP/dt = b*kinf*P*H - kinact*P
        dH/dt = rH*H*(1-H/Kcap) - kinf*P*H
    Se integra esa ODE con scipy (referencia independiente) y se compara contra
    cP(t), cH(t) del FEM homogeneo. Verifica el termino de reaccion acoplado.

  Check B — invariante de acoplamiento y balance.  Por cada Ralstonia lisada se
    producen b fagos, luego el acumulado cumple  Mprod = b * Hinf  exactamente.
    Ademas el balance de fago cierra:
        M_fago(t) = M_fago(0) + Mprod(t) - Minact(t)   (frontera no-flujo)

  Check C — limite H0 -> 0.  Sin hospedador no hay replicacion; el fago solo
    difunde y se inactiva. La masa de fago debe seguir M(0)*exp(-kinact*t)
    (la inactivacion es uniforme, ver Etapa 1/2).

Uso:
    ./mcp_server/venv/bin/python scripts/validate_replicacion.py
"""
import os
import sys

import numpy as np
from scipy.integrate import solve_ivp
import mph

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_replicacion import build, DEFAULTS            # noqa: E402

TMP = "/tmp/replic_check.mph"


def masses(model):
    java = model.java
    eps_b = float(java.param().evaluate("eps_bead"))
    eps_s = float(java.param().evaluate("eps_soil"))

    def Mof(sp):
        Ib = np.asarray(model.evaluate(f"intop_bead(2*pi*r*{sp})"), float).ravel()
        Ia = np.asarray(model.evaluate(f"intop_all(2*pi*r*{sp})"), float).ravel()
        return eps_b * Ib + eps_s * (Ia - Ib)
    t = np.array(java.sol("sol1").getPVals(), float)
    return t, Mof("cP"), Mof("cH")


def check_A(client):
    """Bien mezclado vs ODE Lotka-Volterra."""
    print("=" * 66)
    print("Check A — bien mezclado vs ODE de Lotka-Volterra")
    print("=" * 66)
    # Dominio pequeño + D altas => homogeneo. Para que el campo medio sea
    # EXACTO hay que evitar anticorrelacion inicial: se sobrescribe la CI a
    # cP=c0 y cH=H0 UNIFORMES en todo (bead incluida), sin el contraste
    # bead/suelo del modelo real. Asi <cP*cH>=<cP><cH> desde t=0.
    ov = {"r_bead": "40[um]", "L_root": "0.1[mm]",
          "D_water": "1e-9[m^2/s]", "D_bead": "1e-9[m^2/s]", "D_host": "1e-9[m^2/s]",
          "eps_soil": "1", "eps_bead": "1",
          "H0": "0.5[mol/m^3]", "c0": "0.1[mol/m^3]",
          "k_att": "0[1/d]", "t_end": "10[d]", "n_steps": "80"}
    params = dict(DEFAULTS); params.update(ov)
    _c, model, _g, _m = build(params, TMP, client=client, verbose=False)
    j = model.java
    tds = j.component("comp1").physics("tds")
    tds.feature("init1").set("initc", ["c0", "H0"])   # todo uniforme
    tds.feature("init2").set("initc", ["c0", "H0"])   # bead sin contraste
    # El sistema amplifica ~170x; la tolerancia por defecto del solver
    # transitorio (~1e-3) se propaga a ~1% en el pico. Se aprieta para
    # comparar contra la ODE de referencia (rtol 1e-9) en igualdad.
    j.study("std1").feature("time").set("rtol", "1e-6")
    j.study("std1").run()
    t = np.array(j.sol("sol1").getPVals(), float)
    cP = np.asarray(model.evaluate("cP"), float).mean(axis=1)
    cH = np.asarray(model.evaluate("cH"), float).mean(axis=1)

    b = float(j.param().evaluate("b_burst"))
    kinf = float(j.param().evaluate("k_inf"))
    kin = float(j.param().evaluate("k_inact"))
    rH = float(j.param().evaluate("r_host"))
    K = float(j.param().evaluate("Kcap"))
    P0, H0 = cP[0], cH[0]

    def rhs(_t, y):
        P, H = y
        return [b * kinf * P * H - kin * P,
                rH * H * (1 - H / K) - kinf * P * H]
    sol = solve_ivp(rhs, (t[0], t[-1]), [P0, H0], t_eval=t,
                    rtol=1e-9, atol=1e-12, method="LSODA")
    Po, Ho = sol.y
    # error normalizado por la escala de cada variable
    eP = np.abs(cP - Po).max() / max(cP.max(), Po.max())
    eH = np.abs(cH - Ho).max() / max(cH.max(), Ho.max())
    print(f"  CI homogenea: cP0={P0:.4f}, cH0={H0:.4f}")
    print(f"  {'t[d]':>6} {'cP_FEM':>9} {'cP_ODE':>9} {'cH_FEM':>9} {'cH_ODE':>9}")
    for i in (0, len(t) // 4, len(t) // 2, 3 * len(t) // 4, len(t) - 1):
        print(f"  {t[i]/86400:6.2f} {cP[i]:9.4f} {Po[i]:9.4f} "
              f"{cH[i]:9.4f} {Ho[i]:9.4f}")
    print(f"  error max cP = {eP:.2e} | cH = {eH:.2e}")
    client.remove(model)
    return eP < 5e-3 and eH < 5e-3


def check_BC(client):
    """Invariante Mprod=b*Hinf, balance de fago, y limite H0->0."""
    print("\n" + "=" * 66)
    print("Check B — invariante de acoplamiento y balance de masa")
    print("=" * 66)
    params = dict(DEFAULTS)
    _c, model, _g, _m = build(params, TMP, client=client, verbose=False)
    j = model.java
    j.study("std1").run()
    t, MP, MH = masses(model)
    Mprod = np.asarray(model.evaluate("Mprod"), float).ravel()
    Minact = np.asarray(model.evaluate("Minact"), float).ravel()
    Hinf = np.asarray(model.evaluate("Hinf"), float).ravel()
    b = float(j.param().evaluate("b_burst"))

    # Invariante Mprod = b*Hinf
    denom = max(np.abs(Mprod).max(), 1e-30)
    inv = np.abs(Mprod - b * Hinf).max() / denom
    # Balance de fago: MP(t) = MP(0) + Mprod - Minact
    balP = np.abs(MP - (MP[0] + Mprod - Minact)).max() / max(MP.max(), 1e-30)
    print(f"  invariante Mprod = b*Hinf : error {inv:.2e}")
    print(f"  balance de fago MP(t)=MP0+Mprod-Minact : error {balP:.2e}")
    print(f"  Ralstonia final / inicial : {MH[-1]/MH[0]*100:.1f} %  "
          f"(supervivencia)")
    print(f"  fago: pico/inicial = {MP.max()/MP[0]:.2f}  "
          f"(>1 => hubo amplificacion neta)")
    client.remove(model)

    print("\n" + "=" * 66)
    print("Check C — limite H0->0 (sin Ralstonia: solo difusion+inactivacion)")
    print("=" * 66)
    params = dict(DEFAULTS); params.update({"H0": "0[mol/m^3]"})
    _c, model, _g, _m = build(params, TMP, client=client, verbose=False)
    j = model.java
    j.study("std1").run()
    t, MP, MH = masses(model)
    kin = float(j.param().evaluate("k_inact"))
    decay = MP[0] * np.exp(-kin * t)
    eC = np.abs(MP - decay).max() / MP[0]
    print(f"  M_fago(t) vs M0*exp(-kinact*t) : error {eC:.2e}")
    print(f"  Ralstonia (debe ser 0 siempre) : max {np.abs(MH).max():.2e}")
    client.remove(model)

    return inv < 1e-6, balP < 5e-3, eC < 5e-3


def main():
    client = mph.start(cores=1)
    okA = check_A(client)
    ok_inv, ok_bal, okC = check_BC(client)
    print("\n" + "=" * 66)
    print(f"Check A (vs ODE)        : {'PASA' if okA else 'REVISAR'}")
    print(f"Check B (invariante)    : {'PASA' if ok_inv else 'REVISAR'}")
    print(f"Check B (balance fago)  : {'PASA' if ok_bal else 'REVISAR'}")
    print(f"Check C (limite H0->0)  : {'PASA' if okC else 'REVISAR'}")
    print("=" * 66)
    return 0 if (okA and ok_inv and ok_bal and okC) else 1


if __name__ == "__main__":
    sys.exit(main())
