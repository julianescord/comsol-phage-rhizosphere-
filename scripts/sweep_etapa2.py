"""
Barrido r_bead x D_bead de la Etapa 2.

Pregunta que responde: para un fago que se inactiva a ritmo k_inact, ¿que
combinacion de tamaño de bead y difusividad del gel maximiza la cantidad de
fago ACTIVO presente en el suelo?

HALLAZGO (ver models/etapa2_barrido.png): con inactivacion como UNICO sumidero,
la entrega de fago activo es MONOTONA — bead mas pequeña y gel mas abierto
siempre entregan mas. NO hay optimo interior. La razon es asimetrica:
  - la liberacion lenta SI se penaliza: el fago se inactiva dentro de la bead
    antes de poder salir (en el caso 1000um/2.2e-15, tau_dif ~ 5000 d >> los
    14 d de simulacion, y solo el 5% llega activo);
  - la liberacion rapida NO se penaliza en esta metrica: una vez en el suelo el
    fago se inactiva al mismo ritmo k que dentro, asi que adelantar la salida
    solo puede ayudar.
El "compromiso" liberacion-vs-inactivacion que uno esperaria requiere un
proceso que PREMIE la sostenibilidad — captacion radicular (Etapa 4) o
replicacion con umbral (Etapa 5). Sin el, el diseño optimo es el vehiculo mas
pequeño y difusivo posible.

Metrica: f_soil(t) = fraccion de la dosis inicial que en el instante t esta
ACTIVA y FUERA de la bead. Se reporta su maximo y el instante en que ocurre.

Notas de balance de masa: `c` es la concentracion en el fluido de poro, asi
que los moles por volumen total son eps*c. La bead y el suelo tienen
porosidades distintas, por eso las masas se calculan por dominio y no con una
sola integral.

Uso:
    ./mcp_server/venv/bin/python scripts/sweep_etapa2.py
"""
import os
import sys

import numpy as np
import mph

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_etapa2 import build, DEFAULTS                 # noqa: E402

OUT_CSV = "/home/julianescord/Documentos/COMSOL/models/etapa2_barrido.csv"
OUT_NPZ = "/home/julianescord/Documentos/COMSOL/models/etapa2_barrido.npz"
TMP = "/tmp/etapa2_sweep.mph"

R_BEAD_UM = [25.0, 100.0, 250.0, 1000.0]
D_BEAD = [2.2e-12, 2.2e-13, 2.2e-14, 2.2e-15]
T_END_D = 14.0


def tlist_log(t_end_s, n=60, t0=60.0):
    """Muestreo logaritmico: los casos rapidos liberan en minutos y los
    lentos en semanas; un muestreo lineal perderia por completo los rapidos."""
    ts = np.unique(np.concatenate(([0.0], np.logspace(
        np.log10(t0), np.log10(t_end_s), n))))
    return ",".join(f"{t:.6g}" for t in ts)


def run_case(client, r_bead_um, d_bead):
    params = dict(DEFAULTS)
    params.update({
        "r_bead": f"{r_bead_um}[um]",
        "D_bead": f"{d_bead}[m^2/s]",
        "t_end": f"{T_END_D}[d]",
    })
    _c, model, _g, _m = build(params, TMP, "mq", False, client=client,
                              verbose=False)
    java = model.java
    t_end_s = T_END_D * 86400.0
    java.study("std1").feature("time").set("tlist", tlist_log(t_end_s))

    java.study("std1").run()
    times = np.array(java.sol("sol1").getPVals(), float)

    eps_b = float(java.param().evaluate("eps_bead"))
    eps_s = float(java.param().evaluate("eps_soil"))
    a = float(java.param().evaluate("r_bead"))
    c0 = float(java.param().evaluate("c0"))

    Ib = np.asarray(model.evaluate("intop_bead(2*pi*r*c)"), float).ravel()
    Ia = np.asarray(model.evaluate("intop_all(2*pi*r*c)"), float).ravel()

    M0 = eps_b * c0 * 4.0 / 3.0 * np.pi * a ** 3
    M_bead = eps_b * Ib
    M_soil = eps_s * (Ia - Ib)

    client.remove(model)
    return times, M_bead / M0, M_soil / M0


def main():
    client = mph.start(cores=1)
    n = len(R_BEAD_UM) * len(D_BEAD)
    peak = np.zeros((len(D_BEAD), len(R_BEAD_UM)))
    tpeak = np.zeros_like(peak)
    curves = {}

    print(f"Barrido: {len(R_BEAD_UM)} radios x {len(D_BEAD)} difusividades "
          f"= {n} corridas\n")
    print(f"{'r_bead':>9} {'D_bead':>11} {'max f_soil':>11} {'t(max)':>12} "
          f"{'f_bead(fin)':>12}")
    print("-" * 60)

    k = 0
    for i, d in enumerate(D_BEAD):
        for j, rb in enumerate(R_BEAD_UM):
            k += 1
            times, f_bead, f_soil = run_case(client, rb, d)
            idx = int(np.argmax(f_soil))
            peak[i, j] = f_soil[idx]
            tpeak[i, j] = times[idx]
            curves[(rb, d)] = (times, f_bead, f_soil)
            tp = times[idx]
            tp_s = f"{tp/3600:.1f} h" if tp < 86400 else f"{tp/86400:.1f} d"
            print(f"{rb:7.0f}um {d:11.1e} {peak[i,j]*100:10.2f}% {tp_s:>12} "
                  f"{f_bead[-1]*100:11.2f}%   [{k}/{n}]")

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, "w") as fh:
        fh.write("r_bead_um,D_bead_m2s,max_f_soil,t_max_s,f_bead_final\n")
        for i, d in enumerate(D_BEAD):
            for j, rb in enumerate(R_BEAD_UM):
                fh.write(f"{rb},{d},{peak[i,j]:.6e},{tpeak[i,j]:.6e},"
                         f"{curves[(rb,d)][1][-1]:.6e}\n")
    np.savez(OUT_NPZ, peak=peak, tpeak=tpeak,
             r_bead_um=np.array(R_BEAD_UM), d_bead=np.array(D_BEAD),
             **{f"curve_{rb}_{d}": np.vstack(curves[(rb, d)])
                for (rb, d) in curves})
    print(f"\nCSV: {OUT_CSV}\nNPZ: {OUT_NPZ}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
