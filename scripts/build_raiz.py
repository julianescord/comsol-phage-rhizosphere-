"""
Etapa 3 (raíz): captación radicular saturable como sumidero.

REORDENAMIENTO respecto al plan original de 5 etapas: la raíz (antes Etapa 4)
se adelanta a la 3ª posición, y el flujo de agua no saturado (antes Etapa 3)
pasa a la 4ª. Motivo: el barrido de la Etapa 2 mostró que, con la inactivación
como único sumidero, la entrega de fago es monótona (no hay óptimo de diseño).
La raíz es el proceso que puede —o no— crear ese óptimo, así que es la
pregunta científica prioritaria.

Qué añade sobre la Etapa 2:
  - Una frontera de CAPTACIÓN RADICULAR en el borde exterior del dominio, a
    distancia L de la bead. Se modela como sumidero de Michaelis-Menten:
        J_root = -Vmax_root * c / (Km_root + c)      [mol/(m^2*s)]
    Saturable a proposito: es lo que puede romper la monotonia de la Etapa 2.
    Un pulso rapido SATURA la captacion (c >> Km) y el exceso se inactiva; un
    flujo sostenido se mantiene cerca de Km y la raiz lo capta con eficiencia.
  - r_dom deja de ser "medio infinito" y pasa a ser L = distancia bead-raiz,
    un parametro fisico independiente de r_bead.

Interpretacion fisica del sumidero: el fago que alcanza la rizosfera densa en
Ralstonia se adsorbe / infecta bacterias alli y sale del pool de fago libre
difusivo; los sitios (bacterias, superficie radicular) son finitos, de ahi la
saturacion. Es el analogo del sumidero de tejido de Dosmar et al. 2021.

Geometria de la frontera exterior: se aisla con una Difference de dos
selecciones Ball (esfericas), r_dom*1.001 menos r_dom*0.999, que deja solo el
arco exterior (R = r_dom) y excluye el eje de simetria.

Uso:
    ./mcp_server/venv/bin/python scripts/build_raiz.py
    ./mcp_server/venv/bin/python scripts/build_raiz.py --vmax-root 0   # limite: = Etapa 2
"""
import argparse
import os
import sys

import mph

DEFAULTS = {
    "r_bead": "250[um]",
    "L_root": "5[mm]",          # distancia bead -> superficie radicular
    "D_water": "2.2e-12[m^2/s]",
    "D_bead": "2.2e-14[m^2/s]",
    "eps_soil": "0.45",
    "eps_bead": "0.98",
    "k_inact": "0.5[1/d]",
    "k_att": "0[1/d]",
    "Vmax_root": "1e-9[mol/(m^2*s)]",   # captacion radicular maxima
    "Km_root": "0.1[mol/m^3]",          # constante de semisaturacion
    "c0": "1[mol/m^3]",
    "t_end": "21[d]",
    "n_steps": "84",
}


def build(params, out_path, client=None, verbose=True):
    client = client or mph.start(cores=1)
    model = client.create("raiz_captacion")
    java = model.java
    java.modelNode().create("comp1")

    p = java.param()
    p.set("r_bead", params["r_bead"], "Radio de la bead de alginato")
    p.set("L_root", params["L_root"], "Distancia bead -> superficie radicular")
    p.set("r_dom", "L_root", "Radio del dominio = distancia a la raiz")
    p.set("D_water", params["D_water"], "Difusividad del fago en agua libre")
    p.set("D_bead", params["D_bead"], "Difusividad aparente del fago en la bead")
    p.set("eps_soil", params["eps_soil"], "Porosidad del suelo")
    p.set("eps_bead", params["eps_bead"], "Fraccion de agua del gel")
    p.set("k_inact", params["k_inact"], "Constante de inactivacion del fago")
    p.set("k_att", params["k_att"], "Constante de adhesion coloidal al suelo")
    p.set("Vmax_root", params["Vmax_root"], "Captacion radicular maxima")
    p.set("Km_root", params["Km_root"], "Constante de semisaturacion radicular")
    p.set("c0", params["c0"], "Concentracion inicial de fago en la bead")
    p.set("t_end", params["t_end"], "Horizonte de simulacion")
    p.set("n_steps", params["n_steps"], "Numero de pasos guardados")

    # Guard: la bead debe caber holgadamente dentro del dominio. Si
    # r_bead >= L_root la geometria degenera (la bead llena o rebasa el
    # dominio) y COMSOL devuelve un balance de masa sin sentido en vez de
    # fallar. Se comprueba explicitamente.
    r_bead_si = float(p.evaluate("r_bead"))
    r_dom_si = float(p.evaluate("r_dom"))
    if r_bead_si >= 0.9 * r_dom_si:
        raise ValueError(
            f"Geometria degenerada: r_bead ({r_bead_si:.3e} m) casi alcanza "
            f"o supera r_dom=L_root ({r_dom_si:.3e} m). La bead debe ser "
            f"bastante menor que la distancia a la raiz.")

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

    # Dominio de la bead (por caja).
    sb = seldef.create("sel_bead", "Box")
    sb.set("entitydim", "2")
    sb.set("xmin", "-r_bead*0.01")
    sb.set("xmax", "r_bead*1.01")
    sb.set("ymin", "-r_bead*1.01")
    sb.set("ymax", "r_bead*1.01")
    sb.set("condition", "inside")
    sb.label("Bead")

    # Frontera radicular = arco exterior (R = r_dom), aislado con Difference
    # de dos bolas: intersecta la de radio 1.001 pero no la de 0.999.
    b_out = seldef.create("ball_out", "Ball")
    b_out.set("entitydim", "1")
    b_out.set("posx", "0")
    b_out.set("posy", "0")
    b_out.set("r", "r_dom*1.001")
    b_out.set("condition", "intersects")
    b_in = seldef.create("ball_in", "Ball")
    b_in.set("entitydim", "1")
    b_in.set("posx", "0")
    b_in.set("posy", "0")
    b_in.set("r", "r_dom*0.999")
    b_in.set("condition", "intersects")
    sr = seldef.create("sel_root", "Difference")
    sr.set("entitydim", "1")
    sr.set("add", ["ball_out"])
    sr.set("subtract", ["ball_in"])
    sr.label("Frontera radicular")

    # --- Fisica --------------------------------------------------------
    tds = java.component("comp1").physics().create(
        "tds", "DilutedSpeciesInPorousMedia", "geom1")

    f1 = tds.feature("porous1").feature("fluid1")
    f1.set("DF_c_mat", "userdef")
    f1.set("DF_c", "D_water")
    f1.set("FluidDiffusivityModelType", "MillingtonAndQuirkModel")
    tds.feature("porous1").feature("pm1").set("poro_mat", "userdef")
    tds.feature("porous1").feature("pm1").set("poro", "eps_soil")
    tds.feature("porous1").label("Suelo")

    p2 = tds.create("porous2", "PorousMedium", 2)
    p2.selection().named("sel_bead")
    f2 = p2.feature("fluid1")
    f2.set("DF_c_mat", "userdef")
    f2.set("DF_c", "D_bead")
    f2.set("FluidDiffusivityModelType", "TortuosityModel")
    f2.set("tauF", "1")
    p2.feature("pm1").set("poro_mat", "userdef")
    p2.feature("pm1").set("poro", "eps_bead")
    p2.label("Bead de alginato")

    init2 = tds.create("init2", "init", 2)
    init2.selection().named("sel_bead")
    init2.set("initc", "c0")
    init2.label("Carga inicial de fago en la bead")

    reac = tds.create("reac_inact", "Reactions", 2)
    reac.selection().all()
    reac.set("R_c", "-(k_inact + k_att)*c")
    reac.set("ReactingVolumeType", "PoreVolume")   # ver Check A, Etapa 2
    reac.label("Inactivacion del fago")

    # Sumidero radicular saturable (Michaelis-Menten) en la frontera exterior.
    flux = tds.create("flux_root", "FluxBoundary", 1)
    flux.selection().named("sel_root")
    flux.set("FluxType", "GeneralInwardFlux")
    flux.set("J0", "-Vmax_root*c/(Km_root+c)")     # J0<0 => sale hacia la raiz
    # CRITICO: 'species' viene desactivado (=0) por defecto y sin esto la BC
    # de flujo NO se aplica a c (el sumidero no remueve masa). Se detecto por
    # el balance de masa: Minact alcanzaba toda la dosis Y ademas habia Mcapt,
    # lo que es imposible. Ver validate_raiz.py.
    flux.set("species", "1")
    flux.label("Captacion radicular (Michaelis-Menten)")

    # --- Operadores de integracion para el balance de masa de 4 terminos --
    for tag, dim, named in (("intop_all", 2, None),
                            ("intop_bead", 2, "sel_bead"),
                            ("intop_root", 1, "sel_root")):
        cpl = java.component("comp1").cpl().create(tag, "Integration")
        cpl.selection().geom("geom1", dim)
        if named:
            cpl.selection().named(named)
        else:
            cpl.selection().all()

    # --- Acumuladores de masa (ODEs globales) --------------------------
    # COMSOL integra estas dos variables con su propio solver, con la misma
    # precision que el transporte, en vez de una integracion trapezoidal
    # post-hoc sobre pasos guardados. Cierran el balance de masa de 4 terminos
    # de forma exacta:  M_captada acumulada  y  M_inactivada acumulada.
    rate_cap = "intop_root(2*pi*r*Vmax_root*c/(Km_root+c))"
    rate_inact = ("k_inact*(eps_bead*intop_bead(2*pi*r*c)"
                  "+eps_soil*(intop_all(2*pi*r*c)-intop_bead(2*pi*r*c)))")
    ge = java.physics().create("ge", "GlobalEquations", "geom1")
    g1 = ge.feature("ge1")
    g1.set("name", ["Mcapt", "Minact"])
    g1.set("equation", [f"Mcaptt-({rate_cap})", f"Minactt-({rate_inact})"])
    g1.set("initialValueU", ["0", "0"])
    g1.set("DependentVariableQuantity", "none")
    g1.set("CustomDependentVariableUnit", "mol")
    g1.set("SourceTermQuantity", "none")
    g1.set("CustomSourceTermUnit", "mol/s")
    ge.label("Acumuladores de masa (captada / inactivada)")

    java.component("comp1").material().create("mat1", "Common").label("Placeholder")

    # --- Malla ---------------------------------------------------------
    mesh = java.component("comp1").mesh().create("mesh1")
    ftri = mesh.create("ftri1", "FreeTri")
    sbz = ftri.create("size_bead", "Size")
    sbz.selection().geom("geom1", 2)
    sbz.selection().named("sel_bead")
    sbz.set("custom", "on")
    sbz.set("hmaxactive", "on")
    sbz.set("hmax", "r_bead/15")
    # Refinar tambien en la frontera radicular: alli vive el gradiente del flujo.
    srz = ftri.create("size_root", "Size")
    srz.selection().geom("geom1", 1)
    srz.selection().named("sel_root")
    srz.set("custom", "on")
    srz.set("hmaxactive", "on")
    srz.set("hmax", "r_dom/60")
    g = mesh.feature("size")
    g.set("hauto", "3")
    g.set("custom", "on")
    g.set("hmax", "r_dom/40")
    g.set("hmin", "r_bead/40")
    g.set("hgrad", "1.15")
    mesh.run()

    std = java.study().create("std1")
    std.create("time", "Transient").set("tlist", "range(0,t_end/n_steps,t_end)")

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    model.save(out_path)
    if verbose:
        print("dominios:", geom.getNDomains(), "| fronteras:", geom.getNBoundaries(),
              "| elementos:", mesh.getNumElem())
        print("frontera radicular (sel_root) ->",
              list(java.component("comp1").selection("sel_root").entities(1)))
    return client, model, geom, mesh


def main():
    ap = argparse.ArgumentParser()
    for k, v in DEFAULTS.items():
        ap.add_argument(f"--{k.replace('_', '-')}", default=v)
    ap.add_argument("--out",
                    default="/home/julianescord/Documentos/COMSOL/models/raiz_captacion.mph")
    args = ap.parse_args()
    params = {k: getattr(args, k) for k in DEFAULTS}
    print("Parametros:", params)
    client, model, geom, mesh = build(params, args.out)
    print("guardado en:", args.out)


if __name__ == "__main__":
    sys.exit(main())
