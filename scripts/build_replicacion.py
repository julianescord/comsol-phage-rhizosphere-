"""
Etapa replicacion: infeccion fago-Ralstonia como reaccion-difusion acoplada.

Es el aporte de novedad del proyecto: el fago NO es un agente pasivo que solo
difunde y se inactiva, sino que se AMPLIFICA donde encuentra a su hospedador.
Al lisar una Ralstonia libera un "burst" de b fagos nuevos y consume esa
bacteria. Eso convierte el modelo en un sistema depredador-presa espacial
(reaccion-difusion de 2 especies).

Escenario (elegido con el usuario): PROTECCION DE LA RAIZ. Ralstonia (cH)
coloniza la superficie radicular; se representa concentrada en una banda
rizosferica cerca de L, en su capacidad de carga. El fago (cP) se libera desde
la bead, difunde a traves del suelo inactivandose, y si alcanza la banda con
Ralstonia se amplifica. Pregunta: ¿la amplificacion compensa la inactivacion
en transito y suprime a Ralstonia en la raiz? ¿favorece esto la liberacion
sostenida, que las etapas 2-3 no favorecian?

Cinetica (Lotka-Volterra directo, sin latencia explicita), en pore volume:
    R_cP = +b*kinf*cP*cH - (kinact+katt)*cP
    R_cH = +rH*cH*(1 - cH/Kcap) - kinf*cP*cH

Numero reproductivo basico del fago: R0 ~ b*kinf*H0/kinact. Los parametros por
defecto dan R0 ~ 4 (la epidemia despega pero no explota).

Reemplaza el sumidero de captacion abstracto de la Etapa raiz: aqui la "raiz"
es la banda con Ralstonia y la captacion es la infeccion explicita. La frontera
exterior vuelve a ser no-flujo (sistema cerrado, balance de masa verificable).

Uso:
    ./mcp_server/venv/bin/python scripts/build_replicacion.py
    ./mcp_server/venv/bin/python scripts/build_replicacion.py --H0 0   # limite: sin Ralstonia = Etapa 2
"""
import argparse
import os
import sys

import mph

DEFAULTS = {
    "r_bead": "150[um]",
    "L_root": "0.5[mm]",
    "D_water": "2.2e-12[m^2/s]",
    "D_bead": "2.2e-14[m^2/s]",
    "D_host": "1e-16[m^2/s]",       # Ralstonia sesil (biofilm en la raiz)
    "eps_soil": "0.45",
    "eps_bead": "0.98",
    "k_inact": "0.5[1/d]",
    "k_att": "0[1/d]",
    "b_burst": "50",                # fagos liberados por lisis
    "k_inf": "5e-7[m^3/(mol*s)]",   # tasa de infeccion (da R0 ~ 4)
    "r_host": "0.5[1/d]",           # crecimiento de Ralstonia
    "Kcap": "1[mol/m^3]",           # capacidad de carga de Ralstonia
    "H0": "1[mol/m^3]",             # densidad inicial de Ralstonia en la banda
    "f_rhizo": "0.85",              # banda rizosferica: R > f_rhizo*L_root
    "c0": "1[mol/m^3]",             # fago inicial en la bead
    "t_end": "21[d]",
    "n_steps": "84",
}


def build(params, out_path, client=None, verbose=True):
    client = client or mph.start(cores=1)
    model = client.create("replicacion_fago_ralstonia")
    java = model.java
    java.modelNode().create("comp1")

    p = java.param()
    for k, v in params.items():
        p.set(k, v)
    p.set("r_dom", "L_root")
    p.set("R_rhizo", "f_rhizo*L_root", "Radio interno de la banda rizosferica")

    r_bead_si = float(p.evaluate("r_bead"))
    r_dom_si = float(p.evaluate("r_dom"))
    if r_bead_si >= 0.9 * r_dom_si:
        raise ValueError(
            f"Geometria degenerada: r_bead ({r_bead_si:.3e}) >= 0.9*L_root "
            f"({0.9*r_dom_si:.3e}).")

    # --- Geometria ----------------------------------------------------
    geom = java.component("comp1").geom().create("geom1", 2)
    geom.axisymmetric(True)
    for tag, r in (("c_soil", "r_dom"), ("c_bead", "r_bead")):
        c = geom.create(tag, "Circle")
        c.set("r", r)
        c.set("angle", "180")
        c.set("rot", "-90")
    geom.feature("fin").set("action", "union")
    geom.run()

    seldef = java.component("comp1").selection()
    sb = seldef.create("sel_bead", "Box")
    sb.set("entitydim", "2")
    sb.set("xmin", "-r_bead*0.01"); sb.set("xmax", "r_bead*1.01")
    sb.set("ymin", "-r_bead*1.01"); sb.set("ymax", "r_bead*1.01")
    sb.set("condition", "inside")
    sb.label("Bead")

    # --- Fisica: 2 especies (cP = fago, cH = Ralstonia) ---------------
    tds = java.component("comp1").physics().create(
        "tds", "DilutedSpeciesInPorousMedia", "geom1")
    tds.field("concentration").component(["cP", "cH"])

    f1 = tds.feature("porous1").feature("fluid1")
    f1.set("DF_cP_mat", "userdef"); f1.set("DF_cP", "D_water")
    f1.set("DF_cH_mat", "userdef"); f1.set("DF_cH", "D_host")
    f1.set("FluidDiffusivityModelType", "MillingtonAndQuirkModel")
    tds.feature("porous1").feature("pm1").set("poro_mat", "userdef")
    tds.feature("porous1").feature("pm1").set("poro", "eps_soil")
    tds.feature("porous1").label("Suelo")

    p2 = tds.create("porous2", "PorousMedium", 2)
    p2.selection().named("sel_bead")
    f2 = p2.feature("fluid1")
    f2.set("DF_cP_mat", "userdef"); f2.set("DF_cP", "D_bead")
    f2.set("DF_cH_mat", "userdef"); f2.set("DF_cH", "D_host")
    f2.set("FluidDiffusivityModelType", "TortuosityModel")
    f2.set("tauF", ["1", "1"])
    p2.feature("pm1").set("poro_mat", "userdef")
    p2.feature("pm1").set("poro", "eps_bead")
    p2.label("Bead de alginato")

    # Condiciones iniciales:
    #   init1 (todo): cP=0, cH=H0 en la banda rizosferica (R>R_rhizo), 0 dentro
    #   init2 (bead): cP=c0, cH=0
    tds.feature("init1").set("initc",
                             ["0", "H0*(sqrt(r^2+z^2)>=R_rhizo)"])
    init2 = tds.create("init2", "init", 2)
    init2.selection().named("sel_bead")
    init2.set("initc", ["c0", "0"])
    init2.label("Fago cargado en la bead")

    # Reacciones acopladas Lotka-Volterra.
    reac = tds.create("reac", "Reactions", 2)
    reac.selection().all()
    reac.set("ReactingVolumeType", "PoreVolume")
    reac.set("R_cP", "b_burst*k_inf*cP*cH - (k_inact+k_att)*cP")
    reac.set("R_cH", "r_host*cH*(1-cH/Kcap) - k_inf*cP*cH")
    reac.label("Infeccion fago-Ralstonia (Lotka-Volterra)")

    # --- Operadores de integracion ------------------------------------
    for tag, named in (("intop_all", None), ("intop_bead", "sel_bead")):
        cpl = java.component("comp1").cpl().create(tag, "Integration")
        cpl.selection().geom("geom1", 2)
        if named:
            cpl.selection().named(named)
        else:
            cpl.selection().all()

    # --- Acumuladores de masa (ODEs globales) para el balance ---------
    # Mprod: fagos producidos por lisis (acumulado).
    # Minact: fagos inactivados (acumulado).
    # Hinf: Ralstonia consumida por infeccion (acumulado).
    # Invariante exacto de acoplamiento: Mprod = b_burst * Hinf.
    epsw = "eps_bead*intop_bead(2*pi*r*{0})+eps_soil*(intop_all(2*pi*r*{0})-intop_bead(2*pi*r*{0}))"
    rate_prod = "b_burst*k_inf*(" + epsw.format("cP*cH") + ")"
    rate_inact = "(k_inact+k_att)*(" + epsw.format("cP") + ")"
    rate_hinf = "k_inf*(" + epsw.format("cP*cH") + ")"
    ge = java.physics().create("ge", "GlobalEquations", "geom1")
    g1 = ge.feature("ge1")
    g1.set("name", ["Mprod", "Minact", "Hinf"])
    g1.set("equation", [f"Mprodt-({rate_prod})",
                        f"Minactt-({rate_inact})",
                        f"Hinft-({rate_hinf})"])
    g1.set("initialValueU", ["0", "0", "0"])
    g1.set("DependentVariableQuantity", "none")
    g1.set("CustomDependentVariableUnit", "mol")
    g1.set("SourceTermQuantity", "none")
    g1.set("CustomSourceTermUnit", "mol/s")
    ge.label("Acumuladores (fago producido / inactivado / Ralstonia consumida)")

    java.component("comp1").material().create("mat1", "Common").label("Placeholder")

    # --- Malla ---------------------------------------------------------
    mesh = java.component("comp1").mesh().create("mesh1")
    ftri = mesh.create("ftri1", "FreeTri")
    sbz = ftri.create("size_bead", "Size")
    sbz.selection().geom("geom1", 2)
    sbz.selection().named("sel_bead")
    sbz.set("custom", "on"); sbz.set("hmaxactive", "on"); sbz.set("hmax", "r_bead/15")
    g = mesh.feature("size")
    g.set("hauto", "3"); g.set("custom", "on")
    g.set("hmax", "r_dom/50"); g.set("hmin", "r_bead/40"); g.set("hgrad", "1.15")
    mesh.run()

    std = java.study().create("std1")
    stime = std.create("time", "Transient")
    stime.set("tlist", "range(0,t_end/n_steps,t_end)")
    # El sistema es stiff y amplifica exponencialmente: con la tolerancia por
    # defecto (~1e-3) el pico de fago tiene ~1% de error (ver
    # validate_replicacion.py, Check A). Se aprieta para fiabilidad.
    stime.set("rtol", "1e-4")

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    model.save(out_path)
    if verbose:
        R0 = (float(p.evaluate("b_burst")) * float(p.evaluate("k_inf"))
              * float(p.evaluate("H0")) / float(p.evaluate("k_inact")))
        print("dominios:", geom.getNDomains(), "| elementos:", mesh.getNumElem())
        print(f"R0 (b*kinf*H0/kinact) = {R0:.2f}")
    return client, model, geom, mesh


def main():
    ap = argparse.ArgumentParser()
    for k, v in DEFAULTS.items():
        ap.add_argument(f"--{k.replace('_', '-')}", default=v)
    ap.add_argument("--out",
                    default="/home/julianescord/Documentos/COMSOL/models/replicacion.mph")
    args = ap.parse_args()
    params = {k: getattr(args, k) for k in DEFAULTS}
    print("Parametros:", params)
    client, model, geom, mesh = build(params, args.out)
    print("guardado en:", args.out)


if __name__ == "__main__":
    sys.exit(main())
