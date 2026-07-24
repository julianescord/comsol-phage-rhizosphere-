"""
Modelo combinado: flujo de agua (adveccion) + replicacion del fago.

Cruza los dos hallazgos principales del proyecto:
  - Replicacion (build_replicacion): la carga acumulada de patogeno favorece la
    LIBERACION SOSTENIDA (beads grandes), porque mantiene presion sobre el
    rebrote de Ralstonia.
  - Flujo (build_flujo): el flujo de agua RESCATA al fago de la inactivacion en
    transito (Pe=5 -> 80% llega vivo vs 1% sin flujo).
Pregunta: ¿el flujo de agua cambia el desenlace de biocontrol y la conclusion
sobre la liberacion sostenida?

DOS INTERFACES TDS (imprescindible): el fago (cP) es movil y se advecta con el
agua; Ralstonia (cH) es sesil (biofilm en la raiz) y NO debe advectarse — con
Pe~20 el flujo la barreria decenas de mm en 21 d, absurdo. Como en TDS la
velocidad es por interfaz (comun a todas sus especies), se separan:
  - tds  (cP, fago):      adveccion uniforme + difusion + inactivacion + replic.
  - tds2 (cH, Ralstonia): SIN adveccion, casi inmovil, crecimiento - infeccion.
Las reacciones cruzadas (cada interfaz usa la variable de la otra) acoplan el
sistema Lotka-Volterra.

Flujo: uniforme (u=-u_ref*z_hat), incompresible exacto (ver build_flujo y su
salvedad geometrica). Pe_ref fija la intensidad. La raiz es Outflow para el
fago. Ralstonia en banda rizosferica cerca de L.

Uso:
    ./mcp_server/venv/bin/python scripts/build_flujo_replicacion.py
    ./mcp_server/venv/bin/python scripts/build_flujo_replicacion.py --Pe-ref 0  # = replicacion
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
    "D_host": "1e-16[m^2/s]",
    "eps_soil": "0.45",
    "eps_bead": "0.98",
    "k_inact": "0.5[1/d]",
    "k_att": "0[1/d]",
    "b_burst": "50",
    "k_inf": "5e-7[m^3/(mol*s)]",
    "r_host": "0.5[1/d]",
    "Kcap": "1[mol/m^3]",
    "H0": "1[mol/m^3]",
    "f_rhizo": "0.85",
    "c0": "1[mol/m^3]",
    "Pe_ref": "20",             # intensidad del flujo (Pe=u*L/De_soil)
    "t_end": "21[d]",
    "n_steps": "84",
}


def build(params, out_path, client=None, verbose=True):
    client = client or mph.start(cores=1)
    model = client.create("flujo_replicacion")
    java = model.java
    java.modelNode().create("comp1")

    p = java.param()
    for k, v in params.items():
        p.set(k, v)
    p.set("r_dom", "L_root")
    p.set("R_rhizo", "f_rhizo*L_root")
    p.set("De_soil", "eps_soil^(4/3)*D_water")
    p.set("u_ref", "Pe_ref*De_soil/L_root")

    if float(p.evaluate("r_bead")) >= 0.9 * float(p.evaluate("r_dom")):
        raise ValueError("Geometria degenerada: r_bead >= 0.9*L_root")

    # --- Geometria ----------------------------------------------------
    geom = java.component("comp1").geom().create("geom1", 2)
    geom.axisymmetric(True)
    for tag, r in (("c_soil", "r_dom"), ("c_bead", "r_bead")):
        c = geom.create(tag, "Circle")
        c.set("r", r); c.set("angle", "180"); c.set("rot", "-90")
    geom.feature("fin").set("action", "union")
    geom.run()

    seldef = java.component("comp1").selection()
    sb = seldef.create("sel_bead", "Box")
    sb.set("entitydim", "2")
    sb.set("xmin", "-r_bead*0.01"); sb.set("xmax", "r_bead*1.01")
    sb.set("ymin", "-r_bead*1.01"); sb.set("ymax", "r_bead*1.01")
    sb.set("condition", "inside"); sb.label("Bead")
    b_out = seldef.create("ball_out", "Ball")
    b_out.set("entitydim", "1"); b_out.set("posx", "0"); b_out.set("posy", "0")
    b_out.set("r", "r_dom*1.001"); b_out.set("condition", "intersects")
    b_in = seldef.create("ball_in", "Ball")
    b_in.set("entitydim", "1"); b_in.set("posx", "0"); b_in.set("posy", "0")
    b_in.set("r", "r_dom*0.999"); b_in.set("condition", "intersects")
    sr = seldef.create("sel_root", "Difference")
    sr.set("entitydim", "1"); sr.set("add", ["ball_out"]); sr.set("subtract", ["ball_in"])
    sr.label("Frontera radicular")

    # campo de velocidad uniforme (solo para el fago)
    var = java.component("comp1").variable().create("var_flow")
    var.set("u_r", "0[m/s]")
    var.set("u_z", "-u_ref")

    # ================= Interfaz 1: FAGO (cP), advectado ================
    tds = java.component("comp1").physics().create(
        "tds", "DilutedSpeciesInPorousMedia", "geom1")
    tds.field("concentration").component(["cP"])
    f1 = tds.feature("porous1").feature("fluid1")
    f1.set("DF_cP_mat", "userdef"); f1.set("DF_cP", "D_water")
    f1.set("FluidDiffusivityModelType", "MillingtonAndQuirkModel")
    f1.set("u_src", "userdef"); f1.set("u", ["u_r", "0", "u_z"])
    tds.feature("porous1").feature("pm1").set("poro_mat", "userdef")
    tds.feature("porous1").feature("pm1").set("poro", "eps_soil")
    tds.feature("porous1").label("Suelo (fago)")
    p2 = tds.create("porous2", "PorousMedium", 2)
    p2.selection().named("sel_bead")
    f2 = p2.feature("fluid1")
    f2.set("DF_cP_mat", "userdef"); f2.set("DF_cP", "D_bead")
    f2.set("FluidDiffusivityModelType", "TortuosityModel"); f2.set("tauF", "1")
    f2.set("u_src", "userdef"); f2.set("u", ["u_r", "0", "u_z"])
    p2.feature("pm1").set("poro_mat", "userdef"); p2.feature("pm1").set("poro", "eps_bead")
    p2.label("Bead (fago)")
    i2 = tds.create("init2", "init", 2)
    i2.selection().named("sel_bead"); i2.set("initc", "c0")
    rP = tds.create("reacP", "Reactions", 2)
    rP.selection().all(); rP.set("ReactingVolumeType", "PoreVolume")
    rP.set("R_cP", "b_burst*k_inf*cP*cH - (k_inact+k_att)*cP")
    outf = tds.create("outflow_root", "Outflow", 1)
    outf.selection().named("sel_root")

    # ================= Interfaz 2: RALSTONIA (cH), sesil ===============
    tds2 = java.component("comp1").physics().create(
        "tds2", "DilutedSpeciesInPorousMedia", "geom1")
    tds2.field("concentration").component(["cH"])
    g1 = tds2.feature("porous1").feature("fluid1")
    g1.set("DF_cH_mat", "userdef"); g1.set("DF_cH", "D_host")
    g1.set("FluidDiffusivityModelType", "TortuosityModel"); g1.set("tauF", "1")
    tds2.feature("porous1").feature("pm1").set("poro_mat", "userdef")
    tds2.feature("porous1").feature("pm1").set("poro", "eps_soil")
    tds2.feature("porous1").label("Suelo (Ralstonia)")
    tds2.feature("init1").set("initc", "H0*(sqrt(r^2+z^2)>=R_rhizo)")
    rH = tds2.create("reacH", "Reactions", 2)
    rH.selection().all(); rH.set("ReactingVolumeType", "PoreVolume")
    rH.set("R_cH", "r_host*cH*(1-cH/Kcap) - k_inf*cP*cH")

    # --- Integracion y acumuladores -----------------------------------
    for tag, dim, named in (("intop_all", 2, None), ("intop_bead", 2, "sel_bead"),
                            ("intop_root", 1, "sel_root")):
        cpl = java.component("comp1").cpl().create(tag, "Integration")
        cpl.selection().geom("geom1", dim)
        cpl.selection().named(named) if named else cpl.selection().all()

    epsw = ("eps_bead*intop_bead(2*pi*r*{0})"
            "+eps_soil*(intop_all(2*pi*r*{0})-intop_bead(2*pi*r*{0}))")
    rate_prod = "b_burst*k_inf*(" + epsw.format("cP*cH") + ")"
    rate_inact = "(k_inact+k_att)*(" + epsw.format("cP") + ")"
    rate_hinf = "k_inf*(" + epsw.format("cP*cH") + ")"
    rate_out = "intop_root(2*pi*r*tds.ntflux_cP)"
    ge = java.physics().create("ge", "GlobalEquations", "geom1")
    gg = ge.feature("ge1")
    gg.set("name", ["Mprod", "Minact", "Hinf", "Mout"])
    gg.set("equation", [f"Mprodt-({rate_prod})", f"Minactt-({rate_inact})",
                       f"Hinft-({rate_hinf})", f"Moutt-({rate_out})"])
    gg.set("initialValueU", ["0", "0", "0", "0"])
    gg.set("DependentVariableQuantity", "none")
    gg.set("CustomDependentVariableUnit", "mol")
    gg.set("SourceTermQuantity", "none")
    gg.set("CustomSourceTermUnit", "mol/s")

    java.component("comp1").material().create("mat1", "Common")

    mesh = java.component("comp1").mesh().create("mesh1")
    ftri = mesh.create("ftri1", "FreeTri")
    sbz = ftri.create("size_bead", "Size")
    sbz.selection().geom("geom1", 2); sbz.selection().named("sel_bead")
    sbz.set("custom", "on"); sbz.set("hmaxactive", "on"); sbz.set("hmax", "r_bead/15")
    gm = mesh.feature("size")
    gm.set("hauto", "3"); gm.set("custom", "on")
    gm.set("hmax", "r_dom/80"); gm.set("hmin", "r_bead/40"); gm.set("hgrad", "1.13")
    mesh.run()

    std = java.study().create("std1")
    stime = std.create("time", "Transient")
    stime.set("tlist", "range(0,t_end/n_steps,t_end)")
    stime.set("rtol", "1e-4")

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    model.save(out_path)
    if verbose:
        R0 = (float(p.evaluate("b_burst")) * float(p.evaluate("k_inf"))
              * float(p.evaluate("H0")) / float(p.evaluate("k_inact")))
        print("dominios:", geom.getNDomains(), "| elementos:", mesh.getNumElem(),
              f"| R0={R0:.1f} | Pe={float(p.evaluate('Pe_ref')):.0f}")
    return client, model, geom, mesh


def main():
    ap = argparse.ArgumentParser()
    for k, v in DEFAULTS.items():
        ap.add_argument(f"--{k.replace('_', '-')}", default=v)
    ap.add_argument("--out",
                    default="/home/julianescord/Documentos/COMSOL/models/flujo_replicacion.mph")
    args = ap.parse_args()
    params = {k: getattr(args, k) for k in DEFAULTS}
    print("Parametros:", params)
    client, model, geom, mesh = build(params, args.out)
    print("guardado en:", args.out)


if __name__ == "__main__":
    sys.exit(main())
