"""
Figura: efecto del flujo de agua (Peclet) en el destino del fago.

Dos curvas — fago entregado a la raiz vs. inactivado — en funcion del numero de
Peclet. Muestra la transicion del regimen difusivo (Pe<1: casi todo se
inactiva) al advectivo (Pe>10: casi todo llega vivo). Eje Pe en escala log
(con Pe=0 mostrado como punto aparte a la izquierda).

Uso:
    ./mcp_server/venv/bin/python scripts/plot_flujo.py
"""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402

NPZ = "/home/julianescord/Documentos/COMSOL/models/flujo_barrido.npz"
OUT = "/home/julianescord/Documentos/COMSOL/models/flujo_barrido.png"
INK, INK_SOFT, GRID = "#1a1a1a", "#6b6b6b", "#e4e4e2"
C_OUT, C_IN = "#0072B2", "#D55E00"       # azul entregado, naranja inactivado


def main():
    if not os.path.exists(NPZ):
        print(f"No existe {NPZ}. Corre antes scripts/sweep_flujo.py")
        return 1
    z = np.load(NPZ)
    Pe, fout, finact = z["Pe"], z["fout"], z["finact"]

    # Pe=0 se dibuja a la izquierda en un eje log; se le asigna una posicion.
    nz = Pe > 0
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    fig.patch.set_facecolor("white")

    ax.plot(Pe[nz], fout[nz] * 100, "-o", color=C_OUT, lw=2, ms=6,
            label="entregado vivo a la raíz", solid_capstyle="round")
    ax.plot(Pe[nz], finact[nz] * 100, "-s", color=C_IN, lw=2, ms=6,
            label="inactivado en tránsito", solid_capstyle="round")
    # punto Pe=0 (difusion pura)
    x0 = Pe[nz].min() * 0.35
    ax.plot([x0], [fout[~nz][0] * 100], "o", color=C_OUT, ms=7)
    ax.plot([x0], [finact[~nz][0] * 100], "s", color=C_IN, ms=7)
    ax.axvline(Pe[nz].min() * 0.6, ls=":", c=GRID, lw=1)
    ax.text(x0, 50, "Pe = 0\n(difusión\npura)", ha="center", va="center",
            fontsize=8, color=INK_SOFT)

    ax.set_xscale("log")
    ax.set_xlabel("número de Péclet  Pe = u·L / D$_{e,suelo}$", color=INK)
    ax.set_ylabel("fracción de la dosis  [%]", color=INK)
    ax.set_title("El flujo de agua rescata al fago de la inactivación\n"
                 "en tránsito hacia la raíz", color=INK, fontsize=12)
    ax.set_ylim(-3, 103)
    ax.legend(frameon=False, fontsize=10, labelcolor=INK, loc="center right")
    ax.grid(True, which="both", color=GRID, lw=0.7)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("bottom", "left"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK_SOFT)

    fig.text(0.5, 0.005,
             "Sin flujo (Pe=0) casi todo el fago muere en tránsito; con flujo "
             "modesto (Pe≳5) la mayoría llega viva.",
             ha="center", color=INK_SOFT, fontsize=8.5)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT, dpi=160, facecolor="white")
    print("Figura:", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
