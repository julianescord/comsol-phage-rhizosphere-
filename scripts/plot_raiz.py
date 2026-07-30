"""
Figura del barrido con captacion radicular.

Misma codificacion que plot_etapa2: D_bead es magnitud ordenada -> rampa
SECUENCIAL de un solo tono; sin doble eje; etiquetas directas en cada celda.
El panel compara la fraccion CAPTADA por la raiz (lo util) frente a la
INACTIVADA (lo perdido), para leer de un vistazo la eficiencia del diseño.

Uso:
    ./mcp_server/venv/bin/python scripts/plot_raiz.py
"""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402

NPZ = "/home/julianescord/Documentos/COMSOL/models/raiz_barrido.npz"
OUT = "/home/julianescord/Documentos/COMSOL/models/raiz_barrido.png"
INK, INK_SOFT, GRID = "#1a1a1a", "#6b6b6b", "#e4e4e2"


def main():
    if not os.path.exists(NPZ):
        print(f"No existe {NPZ}. Corre antes scripts/sweep_raiz.py")
        return 1
    z = np.load(NPZ)
    fcap, finact = z["fcap"], z["finact"]
    rb, db = z["r_bead_um"], z["d_bead"]

    fig, ax = plt.subplots(figsize=(7.4, 5.4))
    fig.patch.set_facecolor("white")
    im = ax.imshow(fcap * 100, cmap="Greens", origin="upper", aspect="auto",
                   vmin=0, vmax=max(1e-9, fcap.max() * 100))
    ax.set_xticks(range(len(rb)))
    ax.set_xticklabels([f"{r:.0f}" for r in rb])
    ax.set_yticks(range(len(db)))
    ax.set_yticklabels([f"{d:.1e}" for d in db])
    ax.set_xlabel("radio de la bead  r$_{bead}$  [µm]", color=INK)
    ax.set_ylabel("difusividad en el gel  D$_{bead}$  [m²/s]", color=INK)
    ax.set_title("Fracción de la dosis CAPTADA por la raíz\n"
                 "(captación saturable, L = 0.5 mm)", color=INK, fontsize=12)

    imax = np.unravel_index(np.argmax(fcap), fcap.shape)
    thr = fcap.max() * 0.55
    for i in range(len(db)):
        for j in range(len(rb)):
            edge = dict(boxstyle="round,pad=0.12", fc="none",
                        ec="#b8860b", lw=2) if (i, j) == imax else None
            ax.text(j, i, f"{fcap[i,j]*100:.1f}%", ha="center", va="center",
                    fontsize=12, fontweight="bold",
                    color="white" if fcap[i, j] > thr else INK, bbox=edge)
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
    cb.set_label("f$_{captada}$  [%]", color=INK)
    cb.outline.set_visible(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(colors=INK_SOFT, length=0)

    interior = imax[0] not in (0, len(db) - 1) and imax[1] not in (0, len(rb) - 1)
    nota = ("óptimo INTERIOR (recuadro): la raíz rompe la monotonía"
            if interior else
            "máximo en la esquina: la raíz NO crea óptimo interior")
    fig.text(0.5, 0.01, nota, ha="center", color=INK_SOFT, fontsize=9)

    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT, dpi=160, facecolor="white")
    print("Figura:", OUT, "| optimo interior:", interior)
    return 0


if __name__ == "__main__":
    sys.exit(main())
