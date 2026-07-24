"""
Figura del barrido combinado flujo + replicacion.

Carga acumulada de Ralstonia en el plano Pe x r_bead. Cada fila es un nivel de
flujo (Pe); se marca el mejor r_bead (min carga) de cada fila para ver si la
tendencia (bead pequeña vs grande) cambia con el flujo.

Uso:
    ./mcp_server/venv/bin/python scripts/plot_flujo_replicacion.py
"""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402

NPZ = "/home/julianescord/Documentos/COMSOL/models/flujo_replic_barrido.npz"
OUT = "/home/julianescord/Documentos/COMSOL/models/flujo_replic_barrido.png"
INK, INK_SOFT = "#1a1a1a", "#6b6b6b"


def main():
    if not os.path.exists(NPZ):
        print(f"No existe {NPZ}. Corre antes scripts/sweep_flujo_replicacion.py")
        return 1
    z = np.load(NPZ)
    load, Pe, rb = z["load"], z["Pe"], z["r_bead_um"]

    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    fig.patch.set_facecolor("white")
    im = ax.imshow(load * 100, cmap="Oranges", origin="upper", aspect="auto")
    ax.set_xticks(range(len(rb))); ax.set_xticklabels([f"{r:.0f}" for r in rb])
    ax.set_yticks(range(len(Pe))); ax.set_yticklabels([f"{pe:.0f}" for pe in Pe])
    ax.set_xlabel("radio de la bead  r$_{bead}$  [µm]", color=INK)
    ax.set_ylabel("flujo de agua  Pe", color=INK)
    ax.set_title("Carga acumulada de Ralstonia  (flujo + replicación)\n"
                 "menos = mejor biocontrol · recuadro = mejor r_bead por fila",
                 color=INK, fontsize=11)
    lo, hi = load.min(), load.max()
    for i in range(load.shape[0]):
        jbest = int(np.argmin(load[i]))
        for j in range(load.shape[1]):
            hot = (load[i, j] - lo) / (hi - lo + 1e-30) > 0.55
            edge = dict(boxstyle="round,pad=0.12", fc="none",
                        ec="#b8860b", lw=2) if j == jbest else None
            ax.text(j, i, f"{load[i,j]*100:.0f}%", ha="center", va="center",
                    fontsize=11, fontweight="bold",
                    color="white" if hot else INK, bbox=edge)
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
    cb.set_label("carga media [%]", color=INK); cb.outline.set_visible(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(colors=INK_SOFT, length=0)

    # lectura automatica: ¿el mejor r_bead cambia con Pe?
    bests = [rb[int(np.argmin(load[i]))] for i in range(len(Pe))]
    if len(set(bests)) == 1:
        nota = f"El mejor r_bead ({bests[0]:.0f} µm) no cambia con el flujo."
    else:
        nota = (f"El mejor r_bead cambia con el flujo: "
                + ", ".join(f"Pe={Pe[i]:.0f}→{bests[i]:.0f}µm" for i in range(len(Pe))))
    fig.text(0.5, 0.005, nota, ha="center", color=INK_SOFT, fontsize=8.5)

    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT, dpi=160, facecolor="white")
    print("Figura:", OUT, "| mejores r_bead por Pe:", bests)
    return 0


if __name__ == "__main__":
    sys.exit(main())
