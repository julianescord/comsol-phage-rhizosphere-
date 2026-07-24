"""
Barrido del numero de Peclet: efecto del flujo de agua en la entrega del fago.

Mide como la fraccion de fago que alcanza la raiz VIVA depende de la intensidad
del flujo de agua de fondo (Pe = u*L/De_soil). El limite Pe=0 es difusion pura
(el fago se inactiva en transito); a Pe creciente la adveccion lo arrastra a la
raiz antes de inactivarse.

Uso:
    ./mcp_server/venv/bin/python scripts/sweep_flujo.py
"""
import os
import sys

import numpy as np
import mph

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_flujo import build, DEFAULTS                  # noqa: E402

OUT_CSV = "/home/julianescord/Documentos/COMSOL/models/flujo_barrido.csv"
OUT_NPZ = "/home/julianescord/Documentos/COMSOL/models/flujo_barrido.npz"
TMP = "/tmp/flujo_sweep.mph"

PE = [0.0, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0]


def run_case(client, Pe):
    params = dict(DEFAULTS); params.update({"Pe_ref": str(Pe)})
    _c, model, _g, _m = build(params, TMP, client=client, verbose=False)
    j = model.java
    j.study("std1").run()
    eps_b = float(j.param().evaluate("eps_bead"))
    eps_s = float(j.param().evaluate("eps_soil"))
    Ib = np.asarray(model.evaluate("intop_bead(2*pi*r*c)"), float).ravel()
    Ia = np.asarray(model.evaluate("intop_all(2*pi*r*c)"), float).ravel()
    M = eps_b * Ib + eps_s * (Ia - Ib)
    Mout = np.asarray(model.evaluate("Mout"), float).ravel()
    Minact = np.asarray(model.evaluate("Minact"), float).ravel()
    bal = np.abs((M + Mout + Minact) / M[0] - 1.0).max()
    client.remove(model)
    return Mout[-1] / M[0], Minact[-1] / M[0], bal


def main():
    client = mph.start(cores=1)
    fout = np.zeros(len(PE)); finact = np.zeros(len(PE)); bals = np.zeros(len(PE))
    print(f"{'Pe':>7} {'entregado':>11} {'inactivado':>12} {'balance':>10}")
    print("-" * 44)
    for i, Pe in enumerate(PE):
        fo, fi, b = run_case(client, Pe)
        fout[i], finact[i], bals[i] = fo, fi, b
        print(f"{Pe:7.0f} {fo*100:10.2f}% {fi*100:11.2f}% {b:10.2e}")

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, "w") as fh:
        fh.write("Pe,f_entregado,f_inactivado,balance\n")
        for i, Pe in enumerate(PE):
            fh.write(f"{Pe},{fout[i]:.6e},{finact[i]:.6e},{bals[i]:.6e}\n")
    np.savez(OUT_NPZ, Pe=np.array(PE), fout=fout, finact=finact)
    print(f"\nbalance |max| en todo el barrido: {bals.max():.2e}")
    print(f"CSV: {OUT_CSV}\nNPZ: {OUT_NPZ}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
