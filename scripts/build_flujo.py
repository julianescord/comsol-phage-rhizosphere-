"""
Etapa 4: flujo de agua y transporte advectivo del fago.

Anade adveccion sobre el modelo de la Etapa raiz (1 especie = fago,
inactivacion, salida por la raiz). La pregunta cientifica es directa: el fago
se inactiva en transito hacia la raiz (longitud de penetracion ~0.36 mm);
¿el flujo de agua por transpiracion, que lo arrastra HACIA la raiz, le ayuda a
llegar antes de inactivarse?

MODELO DE FLUJO — campo de velocidad UNIFORME impuesto, no resuelto con Darcy.
Decisiones y por que (documentadas porque costaron):
  1. Resolver Darcy con recarga distribuida rompia el balance de masa: la
     fuente de fluido introduce el termino espurio c·∇·u en la forma
     conservativa del transporte.
  2. Resolver Darcy por gradiente de presion daba Peclet ~1e4 (geometria fina +
     suelo permeable) con oscilaciones numericas severas.
  3. Un campo CONVERGENTE hacia la raiz esferica envolvente es INCOMPRESIBLE
     solo con una fuente en el centro (el agua que converge debe originarse en
     algun sitio). Cualquier regularizacion de esa singularidad reintroduce
     ∇·u≠0 y vuelve a romper el balance. Es una limitacion geometrica de la
     "raiz envolvente" heredada de las etapas previas, no un bug.

Por eso se usa un flujo de fondo UNIFORME (riego/percolacion que atraviesa la
rizosfera): u = -u_ref * z_hat, con ∇·u = 0 EXACTO. Advecta el fago a traves
del suelo; el que alcanza la frontera radicular sale por OUTFLOW. Es un
escenario distinto del de transpiracion convergente (que exigiria rediseñar la
geometria con entrada/salida en fronteras opuestas — trabajo futuro), pero es
verificable y responde una pregunta valida: ¿el flujo de agua de fondo ayuda al
fago a alcanzar la raiz antes de inactivarse?

u_ref se fija por el numero de Peclet Pe = u_ref*L/De_soil (parametro Pe_ref).
Metrica: fago entregado (salido) por la raiz. Limite Pe_ref->0 = solo
difusion + inactivacion (reproduce el transporte de las etapas previas).

Uso:
    ./mcp_server/venv/bin/python scripts/build_flujo.py
    ./mcp_server/venv/bin/python scripts/build_flujo.py --Pe-ref 0   # limite difusivo
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
    "eps_soil": "0.45",
    "eps_bead": "0.98",
    "k_inact": "0.5[1/d]",
    "k_att": "0[1/d]",
    "c0": "1[mol/m^3]",
    "Pe_ref": "20",             # numero de Peclet en la raiz (fija u_ref)
    "t_end": "21[d]",
    "n_steps": "84",
}


def build(params, out_path, client=None, verbose=True):
    client = client or mph.start(cores=1)
    model = client.create("flujo_adveccion")
    java = model.java
    java.modelNode().create("comp1")

    p = java.param()
    for k, v in params.items():
        p.set(k, v)
    p.set("r_dom", "L_root")
    p.set("De_soil", "eps_soil^(4/3)*D_water", "Difusividad efectiva (MQ)")
    # Velocidad de referencia (en la raiz) que da el Peclet pedido.
    p.set("u_ref", "Pe_ref*De_soil/L_root", "Velocidad de Darcy en la raiz")

    r_bead_si = float(p.evaluate("r_bead"))
    r_dom_si = float(p.evaluate("r_dom"))
    if r_bead_si >= 0.9 * r_dom_si:
        raise ValueError(f"Geometria degenerada: r_bead>={0.9*r_dom_si:.2e}")

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

    # --- Campo de velocidad impuesto: flujo de fondo UNIFORME ----------
    # u = -u_ref * z_hat.  Incompresible exacto (∇·u = 0), sin singularidad,
    # sin fuente espuria de masa. El fago se advecta hacia -z, hacia el
    # hemisferio inferior de la frontera radicular.
    var = java.component("comp1").variable().create("var_flow")
    var.set("u_r", "0[m/s]")
    var.set("u_z", "-u_ref")

    # --- Transporte: TDS con adveccion --------------------------------
    tds = java.component("comp1").physics().create(
        "tds", "DilutedSpeciesInPorousMedia", "geom1")
    f1 = tds.feature("porous1").feature("fluid1")
    f1.set("DF_c_mat", "userdef"); f1.set("DF_c", "D_water")
    f1.set("FluidDiffusivityModelType", "MillingtonAndQuirkModel")
    f1.set("u_src", "userdef"); f1.set("u", ["u_r", "0", "u_z"])
    tds.feature("porous1").feature("pm1").set("poro_mat", "userdef")
    tds.feature("porous1").feature("pm1").set("poro", "eps_soil")
    tds.feature("porous1").label("Suelo")

    p2 = tds.create("porous2", "PorousMedium", 2)
    p2.selection().named("sel_bead")
    f2 = p2.feature("fluid1")
    f2.set("DF_c_mat", "userdef"); f2.set("DF_c", "D_bead")
    f2.set("FluidDiffusivityModelType", "TortuosityModel"); f2.set("tauF", "1")
    f2.set("u_src", "userdef"); f2.set("u", ["u_r", "0", "u_z"])
    p2.feature("pm1").set("poro_mat", "userdef"); p2.feature("pm1").set("poro", "eps_bead")
    p2.label("Bead de alginato")

    init2 = tds.create("init2", "init", 2)
    init2.selection().named("sel_bead"); init2.set("initc", "c0")
    init2.label("Carga inicial de fago")

    reac = tds.create("reac_inact", "Reactions", 2)
    reac.selection().all(); reac.set("ReactingVolumeType", "PoreVolume")
    reac.set("R_c", "-(k_inact+k_att)*c"); reac.label("Inactivacion")

    outf = tds.create("outflow_root", "Outflow", 1)
    outf.selection().named("sel_root"); outf.label("Salida por la raiz")

    for tag, dim, named in (("intop_all", 2, None), ("intop_bead", 2, "sel_bead"),
                            ("intop_root", 1, "sel_root")):
        cpl = java.component("comp1").cpl().create(tag, "Integration")
        cpl.selection().geom("geom1", dim)
        cpl.selection().named(named) if named else cpl.selection().all()

    # Acumuladores de balance: fago salido por la raiz (flujo normal total) e
    # inactivado.  M(t) = M(0) - Mout(t) - Minact(t).
    rate_out = "intop_root(2*pi*r*tds.ntflux_c)"
    rate_inact = ("(k_inact+k_att)*(eps_bead*intop_bead(2*pi*r*c)"
                  "+eps_soil*(intop_all(2*pi*r*c)-intop_bead(2*pi*r*c)))")
    ge = java.physics().create("ge", "GlobalEquations", "geom1")
    g1 = ge.feature("ge1")
    g1.set("name", ["Mout", "Minact"])
    g1.set("equation", [f"Moutt-({rate_out})", f"Minactt-({rate_inact})"])
    g1.set("initialValueU", ["0", "0"])
    g1.set("DependentVariableQuantity", "none")
    g1.set("CustomDependentVariableUnit", "mol")
    g1.set("SourceTermQuantity", "none")
    g1.set("CustomSourceTermUnit", "mol/s")

    java.component("comp1").material().create("mat1", "Common").label("Placeholder")

    mesh = java.component("comp1").mesh().create("mesh1")
    ftri = mesh.create("ftri1", "FreeTri")
    sbz = ftri.create("size_bead", "Size")
    sbz.selection().geom("geom1", 2); sbz.selection().named("sel_bead")
    sbz.set("custom", "on"); sbz.set("hmaxactive", "on"); sbz.set("hmax", "r_bead/15")
    # Malla fina para el Peclet de malla < 2 con adveccion (Pe~20).
    g = mesh.feature("size")
    g.set("hauto", "3"); g.set("custom", "on")
    g.set("hmax", "r_dom/80"); g.set("hmin", "r_bead/40"); g.set("hgrad", "1.13")
    mesh.run()

    std = java.study().create("std1")
    stime = std.create("time", "Transient")
    stime.set("tlist", "range(0,t_end/n_steps,t_end)")
    stime.set("rtol", "1e-4")

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    model.save(out_path)
    if verbose:
        Pe = float(p.evaluate("Pe_ref"))
        print("dominios:", geom.getNDomains(), "| elementos:", mesh.getNumElem(),
              f"| Pe_ref = {Pe:.0f}")
    return client, model, geom, mesh


def main():
    ap = argparse.ArgumentParser()
    for k, v in DEFAULTS.items():
        ap.add_argument(f"--{k.replace('_', '-')}", default=v)
    ap.add_argument("--out",
                    default="/home/julianescord/Documentos/COMSOL/models/flujo.mph")
    args = ap.parse_args()
    params = {k: getattr(args, k) for k in DEFAULTS}
    print("Parametros:", params)
    client, model, geom, mesh = build(params, args.out)
    print("guardado en:", args.out)


if __name__ == "__main__":
    sys.exit(main())
