"""
Etapa 2: liberacion desde la bead con difusividad propia, suelo poroso real
e inactivacion del fago.

Sobre la Etapa 1 se añaden tres cosas:

1. **D_bead != D_suelo.** Un 2o nodo PorousMedium sobre la bead con su propia
   difusividad. El fago (~200 nm) difunde en la red de alginato reticulado
   mucho mas lento que en agua libre; esta es la variable que realmente
   controla si la liberacion es sostenida o un pulso.
2. **Suelo poroso real:** porosidad eps_soil y difusividad efectiva por el
   modelo de Millington y Quirk (estandar en suelos).
3. **Inactivacion del fago:** sumidero de primer orden -k_inact*c, el termino
   que el paper de referencia (farmaco pasivo) no contempla.

NO se incluye sorcion de equilibrio (isoterma lineal/Freundlich). Razon
fisica, no de conveniencia: un fago de ~200 nm es un coloide, no un soluto.
Su retencion en suelo es adhesion/filtracion coloidal — cinetica y en la
practica poco reversible — no un reparto en equilibrio instantaneo. Se
modela, cuando toque, como sumidero cinetico adicional en el nodo Reactions
(parametro k_att, aqui desactivado por defecto).

Convenciones importantes:
  - `c` es la concentracion en el FLUIDO de los poros. Los moles por volumen
    total son eps*c, y por eso todas las masas se calculan como eps*integral.
  - En la bead se usa TortuosityModel con tau=1, de modo que
    De_bead = eps_bead*D_bead y la difusividad APARENTE (la que gobierna c)
    es De_bead/eps_bead = D_bead exactamente. Asi `D_bead` significa lo que
    uno espera al leerlo.
  - En el suelo se usa Millington-Quirk; la difusividad aparente resultante
    se determina EMPIRICAMENTE en validate_etapa2.py en vez de asumirla.

Uso:
    ./mcp_server/venv/bin/python scripts/build_etapa2.py
    ./mcp_server/venv/bin/python scripts/build_etapa2.py --eps-soil 1 \
        --tortuosity-soil uniforme --k-inact 0 --d-bead 2.2e-12[m^2/s]
"""
import argparse
import os
import sys

import mph

DEFAULTS = {
    "r_bead": "250[um]",
    "n_dom": "20",
    # Difusividad del fago en agua libre (Stokes-Einstein, particula ~200 nm).
    "D_water": "2.2e-12[m^2/s]",
    # Difusividad APARENTE del fago dentro del gel de alginato. Placeholder:
    # dos ordenes por debajo del agua libre. Es el parametro a barrer.
    "D_bead": "2.2e-14[m^2/s]",
    "eps_soil": "0.45",
    "eps_bead": "0.98",       # el gel de alginato es casi todo agua
    "k_inact": "0.5[1/d]",    # inactivacion del fago (vida media ~1.4 d)
    "k_att": "0[1/d]",        # adhesion coloidal al suelo (desactivada)
    "c0": "1[mol/m^3]",
    "t_end": "14[d]",
    "n_steps": "56",
}


def build(params, out_path, tortuosity_soil="mq", uniform_medium=False,
          client=None, verbose=True):
    """Construye el modelo de la Etapa 2.

    uniform_medium=True omite el nodo porous2, dejando TODO el dominio con
    las mismas propiedades. Es el modo degenerado que usa validate_etapa2.py:
    con un medio uniforme el problema vuelve a tener solucion analitica y se
    pueden verificar por separado la inactivacion y la tortuosidad.
    """
    client = client or mph.start(cores=1)
    model = client.create("etapa2_liberacion_inactivacion")
    java = model.java
    java.modelNode().create("comp1")

    # --- 1. Parametros -------------------------------------------------
    p = java.param()
    p.set("r_bead", params["r_bead"], "Radio de la bead de alginato")
    p.set("n_dom", params["n_dom"], "r_dom = n_dom*r_bead")
    p.set("r_dom", "n_dom*r_bead", "Radio externo del dominio de suelo")
    p.set("D_water", params["D_water"], "Difusividad del fago en agua libre")
    p.set("D_bead", params["D_bead"], "Difusividad aparente del fago en la bead")
    p.set("eps_soil", params["eps_soil"], "Porosidad del suelo")
    p.set("eps_bead", params["eps_bead"], "Fraccion de agua del gel de alginato")
    p.set("k_inact", params["k_inact"], "Constante de inactivacion del fago")
    p.set("k_att", params["k_att"], "Constante de adhesion coloidal al suelo")
    p.set("c0", params["c0"], "Concentracion inicial de fago en la bead")
    p.set("t_end", params["t_end"], "Horizonte de simulacion")
    p.set("n_steps", params["n_steps"], "Numero de pasos guardados")

    # --- 2. Geometria --------------------------------------------------
    geom = java.component("comp1").geom().create("geom1", 2)
    geom.axisymmetric(True)
    for tag, r in (("c_soil", "r_dom"), ("c_bead", "r_bead")):
        c = geom.create(tag, "Circle")
        c.set("r", r)
        c.set("angle", "180")
        c.set("rot", "-90")
    geom.feature("fin").set("action", "union")
    geom.run()

    sel = java.component("comp1").selection().create("sel_bead", "Box")
    sel.set("entitydim", "2")
    sel.set("xmin", "-r_bead*0.01")
    sel.set("xmax", "r_bead*1.01")
    sel.set("ymin", "-r_bead*1.01")
    sel.set("ymax", "r_bead*1.01")
    sel.set("condition", "inside")
    sel.label("Bead")

    # --- 3. Fisica -----------------------------------------------------
    tds = java.component("comp1").physics().create(
        "tds", "DilutedSpeciesInPorousMedia", "geom1")

    # porous1 cubre TODO (suelo). porous2 se define despues sobre la bead y
    # la sobrescribe: en COMSOL el nodo de dominio posterior tiene prioridad,
    # asi no hace falta construir el complemento del suelo.
    f1 = tds.feature("porous1").feature("fluid1")
    f1.set("DF_c_mat", "userdef")
    f1.set("DF_c", "D_water")
    if tortuosity_soil == "mq":
        f1.set("FluidDiffusivityModelType", "MillingtonAndQuirkModel")
    else:
        f1.set("FluidDiffusivityModelType", "TortuosityModel")
        f1.set("tauF", "1")
    tds.feature("porous1").feature("pm1").set("poro_mat", "userdef")
    tds.feature("porous1").feature("pm1").set("poro", "eps_soil")
    tds.feature("porous1").label("Suelo")

    if not uniform_medium:
        p2 = tds.create("porous2", "PorousMedium", 2)
        p2.selection().named("sel_bead")
        f2 = p2.feature("fluid1")
        f2.set("DF_c_mat", "userdef")
        f2.set("DF_c", "D_bead")
        # tau=1 => difusividad aparente en la bead == D_bead exactamente.
        f2.set("FluidDiffusivityModelType", "TortuosityModel")
        f2.set("tauF", "1")
        p2.feature("pm1").set("poro_mat", "userdef")
        p2.feature("pm1").set("poro", "eps_bead")
        p2.label("Bead de alginato")

    # Condicion inicial: carga solo dentro de la bead.
    init2 = tds.create("init2", "init", 2)
    init2.selection().named("sel_bead")
    init2.set("initc", "c0")
    init2.label("Carga inicial de fago en la bead")

    # Inactivacion (+ adhesion coloidal si k_att>0). Sumidero de primer orden.
    reac = tds.create("reac_inact", "Reactions", 2)
    reac.selection().all()
    reac.set("R_c", "-(k_inact + k_att)*c")
    reac.label("Inactivacion del fago")
    # CRITICO: el valor por defecto es 'TotalVolume', que interpreta R_c como
    # por volumen TOTAL. Como la ecuacion es eps*dc/dt = div(De grad c) + R_c,
    # eso haria que la tasa efectiva de inactivacion fuese k/eps y no k.
    # Con 'PoreVolume' el termino se multiplica por eps y k_inact recupera su
    # significado fisico: la tasa de inactivacion del fago en el agua de poro.
    # validate_etapa2.py (Check A) verifica empiricamente que asi ocurre.
    reac.set("ReactingVolumeType", "PoreVolume")

    # --- 4. Operadores de integracion para el balance de masa ----------
    # Se integra sobre la bead y sobre todo; el suelo sale por diferencia.
    for tag, named in (("intop_all", None), ("intop_bead", "sel_bead")):
        cpl = java.component("comp1").cpl().create(tag, "Integration")
        cpl.selection().geom("geom1", 2)
        if named:
            cpl.selection().named(named)
        else:
            cpl.selection().all()

    java.component("comp1").material().create("mat1", "Common").label("Placeholder")

    # --- 5. Malla ------------------------------------------------------
    mesh = java.component("comp1").mesh().create("mesh1")
    ftri = mesh.create("ftri1", "FreeTri")
    sb = ftri.create("size_bead", "Size")
    sb.selection().geom("geom1", 2)
    sb.selection().named("sel_bead")
    sb.set("custom", "on")
    sb.set("hmaxactive", "on")
    sb.set("hmax", "r_bead/15")
    g = mesh.feature("size")
    g.set("hauto", "3")
    g.set("custom", "on")
    g.set("hmax", "r_dom/40")
    g.set("hmin", "r_bead/40")
    g.set("hgrad", "1.15")
    mesh.run()

    # --- 6. Estudio ----------------------------------------------------
    std = java.study().create("std1")
    std.create("time", "Transient").set(
        "tlist", "range(0,t_end/n_steps,t_end)")

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    model.save(out_path)
    return client, model, geom, mesh


def main():
    ap = argparse.ArgumentParser()
    for k, v in DEFAULTS.items():
        ap.add_argument(f"--{k.replace('_', '-')}", default=v)
    ap.add_argument("--tortuosity-soil", default="mq", choices=["mq", "uniforme"],
                    help="mq = Millington-Quirk; uniforme = tau=1 (para verificacion)")
    ap.add_argument("--uniform-medium", action="store_true",
                    help="omite el nodo de la bead: medio uniforme (verificacion)")
    ap.add_argument("--out",
                    default="/home/julianescord/Documentos/COMSOL/models/etapa2_liberacion.mph")
    args = ap.parse_args()

    params = {k: getattr(args, k) for k in DEFAULTS}
    print("Parametros:", params)
    print("Tortuosidad del suelo:", args.tortuosity_soil,
          "| medio uniforme:", args.uniform_medium)

    client, model, geom, mesh = build(params, args.out, args.tortuosity_soil,
                                      args.uniform_medium)
    print("dominios:", geom.getNDomains(), "| elementos:", mesh.getNumElem())
    print("guardado en:", args.out)


if __name__ == "__main__":
    sys.exit(main())
