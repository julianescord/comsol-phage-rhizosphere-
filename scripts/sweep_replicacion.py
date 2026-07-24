"""
Barrido r_bead x D_bead CON replicacion del fago.

La pregunta que cierra el arco del proyecto: las Etapas 2 y 3 mostraron que,
con el fago como agente pasivo (difunde, se inactiva, es captado), la entrega
es MONOTONA -> gana el vehiculo mas pequeño y difusivo, sin optimo interior, y
sin argumento para la liberacion sostenida. ¿La AMPLIFICACION del fago cambia
esto? Si el fago se auto-amplifica al alcanzar a Ralstonia, la dosis y la
velocidad de liberacion podrian importar de otra forma.

METRICA — importante. El sistema es un ciclo depredador-presa con retardo de
transporte: Ralstonia crece, el fago la aplasta, Ralstonia REBROTA. Por eso la
supervivencia en un instante fijo (p.ej. t_end) es FRAGIL: captura solo una
fase del ciclo y da conclusiones que cambian con el instante elegido. La
metrica robusta y biologicamente relevante es la CARGA ACUMULADA de patogeno:

    carga = (1/t_end) * integral_0^t_end [ H(t)/H(0) ] dt

= cuanto patogeno soporta la raiz a lo largo del tiempo. Menos es mejor. Se
reportan tambien la supervivencia final y el minimo para contraste, y la
amplificacion neta del fago.

Uso:
    ./mcp_server/venv/bin/python scripts/sweep_replicacion.py
"""
import os
import sys

import numpy as np
from scipy.integrate import trapezoid
import mph

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_replicacion import build, DEFAULTS            # noqa: E402

OUT_CSV = "/home/julianescord/Documentos/COMSOL/models/replicacion_barrido.csv"
OUT_NPZ = "/home/julianescord/Documentos/COMSOL/models/replicacion_barrido.npz"
TMP = "/tmp/replic_sweep.mph"

R_BEAD_UM = [25.0, 75.0, 150.0, 300.0]     # todos < L_root=0.5mm
D_BEAD = [2.2e-12, 2.2e-13, 2.2e-14, 2.2e-15]
T_END_D = 21.0


def tlist_log(t_end_s, n=90, t0=60.0):
    ts = np.unique(np.concatenate(([0.0], np.logspace(
        np.log10(t0), np.log10(t_end_s), n))))
    return ",".join(f"{t:.6g}" for t in ts)


def run_case(client, r_bead_um, d_bead):
    p = dict(DEFAULTS)
    p.update({"r_bead": f"{r_bead_um}[um]", "D_bead": f"{d_bead}[m^2/s]",
              "t_end": f"{T_END_D}[d]"})
    _c, model, _g, _m = build(p, TMP, client=client, verbose=False)
    j = model.java
    j.study("std1").feature("time").set("tlist", tlist_log(T_END_D * 86400.0))
    j.study("std1").run()

    eps_b = float(j.param().evaluate("eps_bead"))
    eps_s = float(j.param().evaluate("eps_soil"))

    t = np.array(j.sol("sol1").getPVals(), float)

    def Mof(sp):
        Ib = np.asarray(model.evaluate(f"intop_bead(2*pi*r*{sp})"), float).ravel()
        Ia = np.asarray(model.evaluate(f"intop_all(2*pi*r*{sp})"), float).ravel()
        return eps_b * Ib + eps_s * (Ia - Ib)
    MP, MH = Mof("cP"), Mof("cH")
    h = MH / MH[0]
    load = trapezoid(h, t) / (t[-1] - t[0])   # carga acumulada (metrica robusta)
    surv = h[-1]                              # supervivencia en t_end (fragil)
    hmin = h.min()                            # minimo alcanzado
    ampl = MP.max() / MP[0]                   # amplificacion neta del fago
    client.remove(model)
    return load, surv, hmin, ampl


def opt_axis(M, rb, db):
    """Reporta donde esta el minimo de M por eje y si es interior en r_bead."""
    imin = np.unravel_index(np.argmin(M), M.shape)
    # ¿el minimo por columna (r_bead) cae en el interior en la mayoria de filas?
    cols = [int(np.argmin(M[i])) for i in range(M.shape[0])]
    interior_rb = all(c not in (0, len(rb) - 1) for c in cols)
    return imin, interior_rb


def main():
    client = mph.start(cores=1)
    n = len(R_BEAD_UM) * len(D_BEAD)
    load = np.zeros((len(D_BEAD), len(R_BEAD_UM)))
    surv = np.zeros_like(load)
    hmin = np.zeros_like(load)
    ampl = np.zeros_like(load)
    print(f"Barrido con replicacion: {n} corridas\n")
    print(f"{'r_bead':>8} {'D_bead':>11} {'carga':>8} {'superv.fin':>11} "
          f"{'min':>7} {'ampl':>10}")
    print("-" * 60)
    k = 0
    for i, d in enumerate(D_BEAD):
        for j_, rb in enumerate(R_BEAD_UM):
            k += 1
            ld, s, hm, a = run_case(client, rb, d)
            load[i, j_], surv[i, j_], hmin[i, j_], ampl[i, j_] = ld, s, hm, a
            print(f"{rb:6.0f}um {d:11.1e} {ld*100:7.1f}% {s*100:10.1f}% "
                  f"{hm*100:6.1f}% {a:9.0f}x  [{k}/{n}]")

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, "w") as fh:
        fh.write("r_bead_um,D_bead_m2s,load_avg,survival_final,min_survival,"
                 "phage_amplification\n")
        for i, d in enumerate(D_BEAD):
            for j_, rb in enumerate(R_BEAD_UM):
                fh.write(f"{rb},{d},{load[i,j_]:.6e},{surv[i,j_]:.6e},"
                         f"{hmin[i,j_]:.6e},{ampl[i,j_]:.6e}\n")
    np.savez(OUT_NPZ, load=load, survival=surv, min_survival=hmin,
             amplification=ampl, r_bead_um=np.array(R_BEAD_UM),
             d_bead=np.array(D_BEAD))

    print("\n--- optimos por metrica (menos = mejor biocontrol) ---")
    for name, M in (("carga acumulada (ROBUSTA)", load),
                    ("supervivencia final (fragil)", surv),
                    ("minimo alcanzado", hmin)):
        imin, interior_rb = opt_axis(M, R_BEAD_UM, D_BEAD)
        print(f"  {name:32s}: mejor {M[imin]*100:5.1f}% en "
              f"r_bead={R_BEAD_UM[imin[1]]:4.0f}um D_bead={D_BEAD[imin[0]]:.1e}"
              f" | optimo interior en r_bead: {'SI' if interior_rb else 'NO'}")
    print(f"\nCSV: {OUT_CSV}\nNPZ: {OUT_NPZ}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
