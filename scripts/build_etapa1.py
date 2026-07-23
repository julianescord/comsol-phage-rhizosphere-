"""
Etapa 1 del modelo de liberacion de fagos en la rizosfera:
difusion pura desde una bead esferica de alginato hacia suelo homogeneo.

Objetivo de esta etapa: NO es todavia el modelo realista, sino el caso
verificable. Se configura la interfaz "Transport of Diluted Species in
Porous Media" de forma que se reduzca EXACTAMENTE a la 2a ley de Fick:

    porosidad theta = 1, modelo de tortuosidad con tau_F = 1
    =>  De = (theta/tau_F)*D = D    y    d(theta*c)/dt = dc/dt
    =>  dc/dt = div(D grad c)

Eso permite comparar contra la solucion analitica de Crank para una esfera
con concentracion inicial uniforme c0 liberando en un medio infinito
(ver validate_etapa1.py). Una vez validado, las Etapas 2+ activan la
porosidad real, la sorcion, la inactivacion y la replicacion del fago.

Geometria: axisimetrica 2D (plano rz). La esfera se representa como un
semicirculo con el lado plano sobre el eje r=0.

Uso:
    ./mcp_server/venv/bin/python scripts/build_etapa1.py [--r-bead 250[um]]
"""
import argparse
import os
import sys

import mph

# --- Valores por defecto -----------------------------------------------
# D_phage: Stokes-Einstein para una particula de ~200 nm de diametro en agua
# a 298 K (eta = 1e-3 Pa.s):  D = kT/(6*pi*eta*a) ~ 2.2e-12 m^2/s.
# En la Etapa 1 se usa el valor en agua libre (sin correccion por suelo)
# porque el objetivo es la verificacion numerica, no el realismo.
DEFAULTS = {
    "r_bead": "250[um]",       # radio de la bead de alginato (a barrer)
    "n_dom": "20",             # r_dom = n_dom * r_bead (medio ~infinito)
    "D_phage": "2.2e-12[m^2/s]",
    "c0": "1[mol/m^3]",        # concentracion inicial en la bead (normalizable)
    "eps_soil": "1",           # Etapa 1: 1 para reducir a Fick puro
    "tau_F": "1",              # Etapa 1: 1 para reducir a Fick puro
    "t_end": "24[h]",
    "n_steps": "48",
}


def build(params, out_path):
    client = mph.start(cores=1)
    model = client.create("etapa1_difusion_pura")
    java = model.java

    java.modelNode().create("comp1")

    # --- 1. Parametros globales ---------------------------------------
    p = java.param()
    p.set("r_bead", params["r_bead"], "Radio de la bead de alginato")
    p.set("n_dom", params["n_dom"], "Factor de tamano del dominio de suelo")
    p.set("r_dom", "n_dom*r_bead", "Radio externo del dominio de suelo")
    p.set("D_phage", params["D_phage"], "Coef. de difusion del fago")
    p.set("c0", params["c0"], "Concentracion inicial de fago en la bead")
    p.set("eps_soil", params["eps_soil"], "Porosidad (Etapa 1: 1 = Fick puro)")
    p.set("tau_F", params["tau_F"], "Factor de tortuosidad (Etapa 1: 1)")
    p.set("t_end", params["t_end"], "Horizonte de simulacion")
    p.set("n_steps", params["n_steps"], "Numero de pasos guardados")

    # --- 2. Geometria axisimetrica ------------------------------------
    geom = java.component("comp1").geom().create("geom1", 2)
    geom.axisymmetric(True)

    # El orden importa: el suelo primero, la bead encima, para que
    # Form Union deje la bead como dominio propio embebido.
    soil = geom.create("c_soil", "Circle")
    soil.set("r", "r_dom")
    soil.set("angle", "180")
    soil.set("rot", "-90")

    bead = geom.create("c_bead", "Circle")
    bead.set("r", "r_bead")
    bead.set("angle", "180")
    bead.set("rot", "-90")

    geom.feature("fin").set("action", "union")   # Form Union
    geom.run()

    # Seleccion robusta del dominio de la bead por caja delimitadora,
    # en vez de confiar en la numeracion de dominios de COMSOL.
    sel = java.component("comp1").selection().create("sel_bead", "Box")
    sel.set("entitydim", "2")
    sel.set("xmin", "-r_bead*0.01")
    sel.set("xmax", "r_bead*1.01")
    sel.set("ymin", "-r_bead*1.01")
    sel.set("ymax", "r_bead*1.01")
    sel.set("condition", "inside")
    sel.label("Bead")

    # --- 3. Fisica: Transport of Diluted Species in Porous Media ------
    tds = java.component("comp1").physics().create(
        "tds", "DilutedSpeciesInPorousMedia", "geom1")

    fluid = tds.feature("porous1").feature("fluid1")
    fluid.set("DiffusionCoefficientSource", "mat")
    fluid.set("DF_c_mat", "userdef")
    fluid.set("DF_c", "D_phage")
    # Etapa 1: tortuosidad explicita tau_F=1 => De = (theta/tau_F)*D = D.
    fluid.set("FluidDiffusivityModelType", "TortuosityModel")
    fluid.set("tauF", "tau_F")

    pm = tds.feature("porous1").feature("pm1")
    pm.set("poro_mat", "userdef")
    pm.set("poro", "eps_soil")

    # Condicion inicial: c=0 en todo (init1 por defecto), c=c0 en la bead.
    init2 = tds.create("init2", "init", 2)
    init2.selection().named("sel_bead")
    init2.set("initc", "c0")
    init2.label("Carga inicial de fago en la bead")

    # Operador de integracion sobre todo el dominio, para el balance de masa.
    # La convencion axisimetrica (si COMSOL ya incluye el factor 2*pi*r) se
    # determina empiricamente en validate_etapa1.py comparando contra la masa
    # exacta en t=0, en vez de asumirla.
    cpl = java.component("comp1").cpl().create("intop_all", "Integration")
    cpl.selection().geom("geom1", 2)
    cpl.selection().all()
    print("  props de Integration:", sorted(str(x) for x in cpl.properties()))

    # --- 4. Material (requerido aunque todo sea userdef) --------------
    mat = java.component("comp1").material().create("mat1", "Common")
    mat.label("Suelo (placeholder Etapa 1)")

    # --- 5. Mallado ----------------------------------------------------
    # Refinado dentro de la bead y en su frontera, donde vive el gradiente.
    mesh = java.component("comp1").mesh().create("mesh1")
    ftri = mesh.create("ftri1", "FreeTri")
    size_bead = ftri.create("size_bead", "Size")
    size_bead.selection().geom("geom1", 2)
    size_bead.selection().named("sel_bead")
    size_bead.set("custom", "on")
    size_bead.set("hmaxactive", "on")
    size_bead.set("hmax", "r_bead/15")
    # El nodo 'size' global no tiene las banderas *active del Size local.
    gsize = mesh.feature("size")
    gsize.set("hauto", "3")        # 'Finer'
    gsize.set("custom", "on")
    gsize.set("hmax", "r_dom/40")
    gsize.set("hmin", "r_bead/40")
    gsize.set("hgrad", "1.15")
    mesh.run()

    # --- 6. Estudio time-dependent -------------------------------------
    std = java.study().create("std1")
    step = std.create("time", "Transient")
    step.set("tlist", "range(0,t_end/n_steps,t_end)")

    model.save(out_path)
    return client, model, geom, mesh


def main():
    ap = argparse.ArgumentParser()
    for k, v in DEFAULTS.items():
        ap.add_argument(f"--{k.replace('_', '-')}", default=v)
    ap.add_argument("--out", default="/home/julianescord/Documentos/COMSOL/models/etapa1_difusion_pura.mph")
    args = ap.parse_args()

    params = {k: getattr(args, k) for k in DEFAULTS}
    print("Parametros:", params)

    # models/ no se versiona (ver .gitignore): el script crea su salida.
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)

    client, model, geom, mesh = build(params, args.out)

    print("dominios:", geom.getNDomains(), "| fronteras:", geom.getNBoundaries())
    print("elementos de malla:", mesh.getNumElem())
    print("parametros en el modelo:")
    for k, v in model.parameters().items():
        print(f"   {k} = {v}")
    print("guardado en:", args.out)


if __name__ == "__main__":
    sys.exit(main())
