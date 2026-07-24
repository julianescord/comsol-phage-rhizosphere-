"""
Figura del barrido con replicacion.

El sistema es un ciclo depredador-presa con retardo, asi que la supervivencia
en un instante fijo es fragil. La metrica principal (panel izquierdo) es la
CARGA ACUMULADA de patogeno (integral temporal de Ralstonia), robusta al
instante de observacion. El panel derecho muestra la supervivencia final para
contraste: los dos paneles dan optimos DISTINTOS, y esa es justamente la
leccion.

Rampa secuencial de un solo tono; etiquetas directas; sin doble eje. Se
recuadra el mejor caso (menor) de cada panel.

Uso:
    ./mcp_server/venv/bin/python scripts/plot_replicacion.py
"""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402

NPZ = "/home/julianescord/Documentos/COMSOL/models/replicacion_barrido.npz"
OUT = "/home/julianescord/Documentos/COMSOL/models/replicacion_barrido.png"
INK, INK_SOFT = "#1a1a1a", "#6b6b6b"


def panel(ax, M, rb, db, cmap, title, cblabel):
    im = ax.imshow(M, cmap=cmap, origin="upper", aspect="auto")
    ax.set_xticks(range(len(rb))); ax.set_xticklabels([f"{r:.0f}" for r in rb])
    ax.set_yticks(range(len(db))); ax.set_yticklabels([f"{d:.1e}" for d in db])
    ax.set_xlabel("radio de la bead  r$_{bead}$  [µm]", color=INK)
    ax.set_ylabel("difusividad en el gel  D$_{bead}$  [m²/s]", color=INK)
    ax.set_title(title, color=INK, fontsize=11)
    mark = np.unravel_index(np.argmin(M), M.shape)
    lo, hi = M.min(), M.max()
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            hot = (M[i, j] - lo) / (hi - lo + 1e-30) > 0.55
            edge = dict(boxstyle="round,pad=0.12", fc="none",
                        ec="#b8860b", lw=2) if (i, j) == mark else None
            ax.text(j, i, f"{M[i,j]*100:.0f}%", ha="center", va="center",
                    fontsize=11, fontweight="bold",
                    color="white" if hot else INK, bbox=edge)
    cb = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
    cb.set_label(cblabel, color=INK); cb.outline.set_visible(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(colors=INK_SOFT, length=0)
    return mark


def main():
    if not os.path.exists(NPZ):
        print(f"No existe {NPZ}. Corre antes scripts/sweep_replicacion.py")
        return 1
    z = np.load(NPZ)
    load, surv = z["load"], z["survival"]
    rb, db = z["r_bead_um"], z["d_bead"]

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(13, 5.2))
    fig.patch.set_facecolor("white")
    mL = panel(axA, load, rb, db, "Oranges",
               "Carga acumulada de Ralstonia  (métrica robusta)\n"
               "∫ H(t)/H₀ dt · menos = mejor biocontrol", "carga media [%]")
    mS = panel(axB, surv, rb, db, "Oranges",
               "Supervivencia en t = 21 d  (frágil: fase del ciclo)\n"
               "H(t_end)/H₀ · menos = mejor", "supervivencia [%]")

    rL, rS = rb[mL[1]], rb[mS[1]]
    nota = (f"La métrica robusta (carga) optimiza en r_bead={rL:.0f} µm; "
            f"la frágil (final) en {rS:.0f} µm. La replicación hace que el "
            "tamaño importe y favorece liberación más sostenida que las etapas pasivas.")
    fig.text(0.5, 0.005, nota, ha="center", color=INK_SOFT, fontsize=8.5)

    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT, dpi=160, facecolor="white")
    print("Figura:", OUT, f"| opt carga: {rL:.0f}um | opt final: {rS:.0f}um")
    return 0


if __name__ == "__main__":
    sys.exit(main())
