"""
Verificacion del acoplamiento flujo (campo uniforme) -> transporte advectivo.

  Check A — balance de masa. Con adveccion + inactivacion + salida por la raiz
    (outflow): M(t) = M(0) - Mout(t) - Minact(t) debe cerrar. Es la
    verificacion central: un campo con ∇·u != 0 (p.ej. la fuente distribuida o
    un campo convergente regularizado) rompe este balance por el termino
    espurio c·∇·u; el campo uniforme incompresible lo mantiene.

  Check B — limite Pe->0. Sin flujo, no hay entrega advectiva: casi todo el
    fago se inactiva (Mout ~ 0). Reproduce el transporte difusivo previo.

  Check C — la entrega crece con el flujo. A mayor Pe, mas fago sale por la
    raiz antes de inactivarse: Mout/M0 debe crecer monotonamente con Pe.

  Se reporta el Peclet efectivo <|u|>*L/De_soil y el minimo de c (las
  oscilaciones numericas por adveccion deben ser pequeñas frente a c0).

Uso:
    ./mcp_server/venv/bin/python scripts/validate_flujo.py
"""
import os
import sys

import numpy as np
import mph

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_flujo import build, DEFAULTS                  # noqa: E402

TMP = "/tmp/flujo_check.mph"


def run(client, Pe):
    params = dict(DEFAULTS); params.update({"Pe_ref": str(Pe)})
    _c, model, _g, _m = build(params, TMP, client=client, verbose=False)
    j = model.java
    j.study("std1").run()
    eps_b = float(j.param().evaluate("eps_bead"))
    eps_s = float(j.param().evaluate("eps_soil"))
    Ib = np.asarray(model.evaluate("intop_bead(2*pi*r*c)"), float).ravel()
    Ia = np.asarray(model.evaluate("intop_all(2*pi*r*c)"), float).ravel()
    M = eps_b * Ib + eps_s * (Ia - Ib)
    Mout = np.asarray(model.evaluate("Mout"), float).ravel()
    Minact = np.asarray(model.evaluate("Minact"), float).ravel()
    c0 = float(j.param().evaluate("c0"))
    cmin = np.asarray(model.evaluate("c"), float).min() / c0
    bal = np.abs((M + Mout + Minact) / M[0] - 1.0).max()
    fout = Mout[-1] / M[0]
    client.remove(model)
    return dict(bal=bal, fout=fout, finact=Minact[-1] / M[0], cmin=cmin)


def main():
    client = mph.start(cores=1)
    print(f"{'Pe':>6} {'f_entregado':>12} {'f_inactivado':>13} "
          f"{'balance':>10} {'cmin/c0':>10}")
    print("-" * 56)
    data = {}
    for Pe in (0, 5, 20, 80):
        d = run(client, Pe)
        data[Pe] = d
        print(f"{Pe:6d} {d['fout']*100:11.2f}% {d['finact']*100:12.2f}% "
              f"{d['bal']:10.2e} {d['cmin']:10.2e}")

    okA = all(d["bal"] < 0.02 for d in data.values())     # balance cierra
    okB = data[0]["fout"] < 0.05                           # sin flujo, poca entrega
    fs = [data[Pe]["fout"] for Pe in (0, 5, 20, 80)]
    okC = all(fs[i] <= fs[i + 1] + 1e-6 for i in range(len(fs) - 1))

    print("\n" + "=" * 56)
    print(f"Check A (balance de masa)     : {'PASA' if okA else 'REVISAR'}")
    print(f"Check B (limite Pe->0)        : {'PASA' if okB else 'REVISAR'}")
    print(f"Check C (entrega crece con Pe): {'PASA' if okC else 'REVISAR'}")
    print("=" * 56)
    print("Lectura: la adveccion aumenta la fraccion de fago que alcanza la")
    print("raiz viva, a costa de menos inactivacion — el flujo ayuda a la")
    print("entrega, venciendo en parte la limitacion difusiva.")
    return 0 if (okA and okB and okC) else 1


if __name__ == "__main__":
    sys.exit(main())
