"""
Barrido del flujo (Peclet) en el modelo combinado flujo + replicacion.

Pregunta: ¿el flujo de agua cambia el desenlace de biocontrol y la conclusion
sobre la liberacion sostenida? Sin flujo (etapa replicacion) la carga acumulada
de patogeno favorecia beads grandes/lentas. El flujo rescata al fago de la
inactivacion en transito — ¿eso refuerza, anula o invierte esa conclusion?

Se barre Pe (intensidad del flujo) x r_bead (tamaño del vehiculo), midiendo la
carga acumulada de Ralstonia = (1/t_end)*∫ H(t)/H0 dt (menos = mejor).

Uso:
    ./mcp_server/venv/bin/python scripts/sweep_flujo_replicacion.py
"""
import os
import sys

import numpy as np
from scipy.integrate import trapezoid
import mph

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_flujo_replicacion import build, DEFAULTS      # noqa: E402

OUT_CSV = "/home/julianescord/Documentos/COMSOL/models/flujo_replic_barrido.csv"
OUT_NPZ = "/home/julianescord/Documentos/COMSOL/models/flujo_replic_barrido.npz"
TMP = "/tmp/fr_sweep.mph"

PE = [0.0, 5.0, 20.0]
R_BEAD_UM = [25.0, 75.0, 150.0, 300.0]
T_END_D = 21.0


def tlist_log(t_end_s, n=80, t0=60.0):
    ts = np.unique(np.concatenate(([0.0], np.logspace(
        np.log10(t0), np.log10(t_end_s), n))))
    return ",".join(f"{t:.6g}" for t in ts)


def run_case(client, Pe, rb):
    p = dict(DEFAULTS)
    p.update({"Pe_ref": str(Pe), "r_bead": f"{rb}[um]", "t_end": f"{T_END_D}[d]"})
    _c, model, _g, _m = build(p, TMP, client=client, verbose=False)
    j = model.java
    j.study("std1").feature("time").set("tlist", tlist_log(T_END_D * 86400.0))
    j.study("std1").run()
    eps_b = float(j.param().evaluate("eps_bead")); eps_s = float(j.param().evaluate("eps_soil"))
    t = np.array(j.sol("sol1").getPVals(), float)
    Ib = np.asarray(model.evaluate("intop_bead(2*pi*r*cH)"), float).ravel()
    Ia = np.asarray(model.evaluate("intop_all(2*pi*r*cH)"), float).ravel()
    MH = eps_b * Ib + eps_s * (Ia - Ib)
    load = trapezoid(MH / MH[0], t) / (t[-1] - t[0])
    client.remove(model)
    return load


def main():
    client = mph.start(cores=1)
    load = np.zeros((len(PE), len(R_BEAD_UM)))
    n = load.size
    print(f"Barrido flujo+replicacion: {n} corridas\n")
    print(f"{'Pe':>5} {'r_bead':>8} {'carga Ralstonia':>16}")
    print("-" * 34)
    k = 0
    for i, Pe in enumerate(PE):
        for jx, rb in enumerate(R_BEAD_UM):
            k += 1
            load[i, jx] = run_case(client, Pe, rb)
            print(f"{Pe:5.0f} {rb:6.0f}um {load[i,jx]*100:14.1f}%  [{k}/{n}]")

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, "w") as fh:
        fh.write("Pe,r_bead_um,load_avg\n")
        for i, Pe in enumerate(PE):
            for jx, rb in enumerate(R_BEAD_UM):
                fh.write(f"{Pe},{rb},{load[i,jx]:.6e}\n")
    np.savez(OUT_NPZ, load=load, Pe=np.array(PE), r_bead_um=np.array(R_BEAD_UM))

    print("\n--- mejor r_bead por nivel de flujo (min carga) ---")
    for i, Pe in enumerate(PE):
        jbest = int(np.argmin(load[i]))
        print(f"  Pe={Pe:3.0f}: mejor r_bead = {R_BEAD_UM[jbest]:4.0f}um "
              f"(carga {load[i,jbest]*100:.1f}%)  "
              f"| tendencia r_bead: {'grande' if jbest>=2 else 'pequeña'}")
    print(f"\nCSV: {OUT_CSV}\nNPZ: {OUT_NPZ}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
