"""
Figura del barrido de la Etapa 2.

Decisiones de codificacion (deliberadas, no por defecto de matplotlib):

- D_bead es una MAGNITUD ORDENADA, no una identidad. Por eso las cuatro
  curvas del panel B no llevan colores categoricos sino una rampa
  SECUENCIAL de un solo tono, claro -> oscuro. Ademas el panel A usa la
  MISMA rampa, de modo que "mas oscuro = gel mas cerrado" significa lo mismo
  en los dos paneles.
- Sin doble eje y. Sin arcoiris. Rejilla y ejes recesivos.
- Etiquetas directas sobre las curvas ademas de la leyenda, para que la
  identidad no dependa solo del color.

Uso:
    ./mcp_server/venv/bin/python scripts/plot_etapa2.py
"""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402

NPZ = "/home/julianescord/Documentos/COMSOL/models/etapa2_barrido.npz"
OUT = "/home/julianescord/Documentos/COMSOL/models/etapa2_barrido.png"

INK = "#1a1a1a"
INK_SOFT = "#6b6b6b"
GRID = "#e4e4e2"


def main():
    if not os.path.exists(NPZ):
        print(f"No existe {NPZ}. Corre antes scripts/sweep_etapa2.py")
        return 1
    z = np.load(NPZ)
    peak, tpeak = z["peak"], z["tpeak"]
    rb, db = z["r_bead_um"], z["d_bead"]

    # Rampa secuencial de un solo tono, claro -> oscuro.
    ramp = plt.cm.Blues(np.linspace(0.32, 0.95, len(db)))

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(12.4, 5.0))
    fig.patch.set_facecolor("white")

    # ---------------- Panel A: mapa de la entrega maxima ----------------
    im = axA.imshow(peak * 100, cmap="Blues", origin="upper", aspect="auto",
                    vmin=0, vmax=max(1e-9, peak.max() * 100))
    axA.set_xticks(range(len(rb)))
    axA.set_xticklabels([f"{r:.0f}" for r in rb])
    axA.set_yticks(range(len(db)))
    axA.set_yticklabels([f"{d:.1e}" for d in db])
    axA.set_xlabel("radio de la bead  r$_{bead}$  [µm]", color=INK)
    axA.set_ylabel("difusividad en el gel  D$_{bead}$  [m²/s]", color=INK)
    axA.set_title("Máximo de fago activo entregado al suelo\n"
                  "(% de la dosis inicial)", color=INK, fontsize=11)

    # Etiqueta directa en cada celda: el valor no depende solo del color.
    thr = peak.max() * 0.55
    for i in range(len(db)):
        for j in range(len(rb)):
            t = tpeak[i, j]
            tl = f"{t/3600:.0f} h" if t < 86400 else f"{t/86400:.1f} d"
            axA.text(j, i - 0.10, f"{peak[i,j]*100:.1f}%", ha="center",
                     va="center", fontsize=11, fontweight="bold",
                     color="white" if peak[i, j] > thr else INK)
            axA.text(j, i + 0.22, tl, ha="center", va="center", fontsize=8,
                     color="#dbe7f3" if peak[i, j] > thr else INK_SOFT)
    cb = fig.colorbar(im, ax=axA, fraction=0.046, pad=0.03)
    cb.set_label("máx. f$_{suelo}$  [%]", color=INK)
    cb.outline.set_visible(False)

    # ---------------- Panel B: cinetica ----------------
    j_ref = int(np.argmin(np.abs(rb - 250.0)))
    r_ref = rb[j_ref]
    for i, d in enumerate(db):
        key = f"curve_{r_ref}_{d}"
        if key not in z:
            continue
        times, _f_bead, f_soil = z[key]
        m = times > 0
        axB.plot(times[m] / 86400, f_soil[m] * 100, lw=2, color=ramp[i],
                 label=f"D$_{{bead}}$ = {d:.1e}", solid_capstyle="round")
        k = int(np.argmax(f_soil))
        if f_soil[k] * 100 > 0.4:      # etiqueta directa solo si es legible
            axB.annotate(f"{d:.0e}", (times[k] / 86400, f_soil[k] * 100),
                         textcoords="offset points", xytext=(6, 4),
                         fontsize=8, color=ramp[i], fontweight="bold")

    axB.set_xlabel("tiempo [d]", color=INK)
    axB.set_ylabel("fago activo en el suelo  [% de la dosis]", color=INK)
    axB.set_title(f"Cinética de entrega  (r$_{{bead}}$ = {r_ref:.0f} µm)\n"
                  "gel más abierto → pico más alto y temprano (monótono)",
                  color=INK, fontsize=11)
    axB.legend(frameon=False, fontsize=8.5, labelcolor=INK)
    axB.grid(True, color=GRID, lw=0.8)
    axB.set_axisbelow(True)

    for ax in (axA, axB):
        for s in ax.spines.values():
            s.set_visible(False)
        ax.tick_params(colors=INK_SOFT, length=0)
    axB.spines["bottom"].set_visible(True)
    axB.spines["bottom"].set_color(GRID)
    axB.spines["left"].set_visible(True)
    axB.spines["left"].set_color(GRID)

    fig.tight_layout()
    fig.savefig(OUT, dpi=160, facecolor="white")
    print("Figura:", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
