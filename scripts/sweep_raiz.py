"""
Barrido r_bead x D_bead CON captacion radicular (Etapa raiz).

Pregunta: la Etapa 2 mostro que, con la inactivacion como unico sumidero, la
entrega de fago es monotona (gana el vehiculo mas pequeño y difusivo, sin
optimo interior). ¿La captacion radicular saturable ROMPE esa monotonia y
crea un optimo de diseño?

Regimen elegido (justificado por calibracion, ver validate_raiz.py y la
longitud de penetracion sqrt(D_soil/k) ~ 0.36 mm):
  - L_root = 0.5 mm: la bead a menos de ~1 longitud de penetracion de la raiz,
    de modo que una fraccion apreciable del fago llega vivo (~46 % en el caso
    base). Con L >> penetracion la raiz no recibe nada y el barrido no informa.
  - Km_root pequeño: para que un pulso rapido SATURE la captacion. Si Km >> c
    en la raiz, la captacion es efectivamente lineal y ya sabemos que un
    sumidero lineal no crea optimo. La saturacion es el mecanismo candidato.

Metrica: fraccion de la DOSIS REAL (M_active(0)) captada por la raiz al final,
leida del acumulador ODE global Mcapt (no por trapecio).

Uso:
    ./mcp_server/venv/bin/python scripts/sweep_raiz.py
"""
import os
import sys

import numpy as np
import mph

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_raiz import build, DEFAULTS                   # noqa: E402

OUT_CSV = "/home/julianescord/Documentos/COMSOL/models/raiz_barrido.csv"
OUT_NPZ = "/home/julianescord/Documentos/COMSOL/models/raiz_barrido.npz"
TMP = "/tmp/raiz_sweep.mph"

# Todos los radios < L_root (0.5 mm) para que la bead quepa holgadamente en el
# dominio; con r_bead >= L_root la geometria degenera (ver guard en build_raiz).
R_BEAD_UM = [25.0, 75.0, 150.0, 300.0]
D_BEAD = [2.2e-12, 2.2e-13, 2.2e-14, 2.2e-15]
L_ROOT = "0.5[mm]"
KM_ROOT = "5e-3[mol/m^3]"      # pequeño: fuerza saturacion con pulsos rapidos
VMAX_ROOT = "1e-9[mol/(m^2*s)]"
T_END_D = 21.0


def tlist_log(t_end_s, n=70, t0=60.0):
    ts = np.unique(np.concatenate(([0.0], np.logspace(
        np.log10(t0), np.log10(t_end_s), n))))
    return ",".join(f"{t:.6g}" for t in ts)


def run_case(client, r_bead_um, d_bead):
    p = dict(DEFAULTS)
    p.update({
        "r_bead": f"{r_bead_um}[um]",
        "D_bead": f"{d_bead}[m^2/s]",
        "L_root": L_ROOT,
        "Km_root": KM_ROOT,
        "Vmax_root": VMAX_ROOT,
        "t_end": f"{T_END_D}[d]",
    })
    _c, model, _g, _m = build(p, TMP, client=client, verbose=False)
    java = model.java
    java.study("std1").feature("time").set(
        "tlist", tlist_log(T_END_D * 86400.0))
    java.study("std1").run()

    eps_b = float(java.param().evaluate("eps_bead"))
    eps_s = float(java.param().evaluate("eps_soil"))
    Ib = np.asarray(model.evaluate("intop_bead(2*pi*r*c)"), float).ravel()
    Ia = np.asarray(model.evaluate("intop_all(2*pi*r*c)"), float).ravel()
    M_active = eps_b * Ib + eps_s * (Ia - Ib)
    M_ref = M_active[0]          # dosis realmente cargada
    Mcap = np.asarray(model.evaluate("Mcapt"), float).ravel()
    Minact = np.asarray(model.evaluate("Minact"), float).ravel()
    f_cap = Mcap[-1] / M_ref
    f_inact = Minact[-1] / M_ref
    # Salvaguarda: el balance de 4 terminos debe cerrar. Un caso que no cierre
    # (p.ej. geometria degenerada) no debe entrar en la conclusion en silencio.
    resid = np.abs((M_active + Mcap + Minact) / M_ref - 1.0).max()
    client.remove(model)
    if resid > 0.02:
        raise RuntimeError(
            f"Balance de masa roto (residual {resid:.2e}) para "
            f"r_bead={r_bead_um}um D_bead={d_bead:.1e}: caso descartado.")
    return f_cap, f_inact


def main():
    client = mph.start(cores=1)
    n = len(R_BEAD_UM) * len(D_BEAD)
    fcap = np.zeros((len(D_BEAD), len(R_BEAD_UM)))
    finact = np.zeros_like(fcap)

    print(f"Barrido con raiz: {n} corridas | L={L_ROOT} Km={KM_ROOT}\n")
    print(f"{'r_bead':>8} {'D_bead':>11} {'f_captada':>11} {'f_inact':>10}")
    print("-" * 44)
    k = 0
    for i, d in enumerate(D_BEAD):
        for j, rb in enumerate(R_BEAD_UM):
            k += 1
            fc, fi = run_case(client, rb, d)
            fcap[i, j] = fc
            finact[i, j] = fi
            print(f"{rb:6.0f}um {d:11.1e} {fc*100:10.2f}% {fi*100:9.2f}%  "
                  f"[{k}/{n}]")

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, "w") as fh:
        fh.write("r_bead_um,D_bead_m2s,f_captada,f_inactivada\n")
        for i, d in enumerate(D_BEAD):
            for j, rb in enumerate(R_BEAD_UM):
                fh.write(f"{rb},{d},{fcap[i,j]:.6e},{finact[i,j]:.6e}\n")
    np.savez(OUT_NPZ, fcap=fcap, finact=finact,
             r_bead_um=np.array(R_BEAD_UM), d_bead=np.array(D_BEAD))

    imax = np.unravel_index(np.argmax(fcap), fcap.shape)
    interior = imax[0] not in (0, len(D_BEAD) - 1) and \
        imax[1] not in (0, len(R_BEAD_UM) - 1)
    print(f"\nmaximo f_captada = {fcap[imax]*100:.2f}% en "
          f"r_bead={R_BEAD_UM[imax[1]]:.0f}um, D_bead={D_BEAD[imax[0]]:.1e}")
    print(f"¿optimo INTERIOR? {'SI' if interior else 'NO (en el borde/esquina)'}")
    print(f"\nCSV: {OUT_CSV}\nNPZ: {OUT_NPZ}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
