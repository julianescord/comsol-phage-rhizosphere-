"""
Soluciones analiticas de referencia para verificar los modelos FEM.

Se mantienen aparte de los scripts de validacion para que Etapa 1 y Etapa 2
usen exactamente la misma referencia, y para que la referencia pueda
autoverificarse en un solo sitio.
"""
import numpy as np
from scipy.special import erf
from scipy.integrate import quad


def crank_sphere(r, t, a, D, c0=1.0):
    """Difusion desde una esfera con concentracion inicial uniforme.

    Esfera de radio `a` con c=c0 dentro y c=0 fuera en t=0, liberando en un
    medio infinito de difusividad `D` uniforme.
    Crank, "The Mathematics of Diffusion", 2a ed., seccion 3.3.

    Devuelve c(r,t). Valido solo mientras el frente no alcance la frontera
    exterior del dominio FEM (medio infinito).
    """
    r = np.atleast_1d(np.asarray(r, float)).copy()
    r[r < 1e-15] = 1e-15                       # evita la singularidad 1/r
    s = 2.0 * np.sqrt(D * t)
    return c0 * (
        0.5 * (erf((a - r) / s) + erf((a + r) / s))
        - np.sqrt(D * t) / (r * np.sqrt(np.pi))
        * (np.exp(-((a - r) ** 2) / (4 * D * t))
           - np.exp(-((a + r) ** 2) / (4 * D * t)))
    )


def crank_sphere_decay(r, t, a, D, k, c0=1.0):
    """Igual que crank_sphere pero con inactivacion de primer orden.

    Si el decaimiento -k*c es uniforme en el espacio, el cambio de variable
    c = u*exp(-k t) elimina exactamente el termino de reaccion: u obedece la
    difusion pura. Por tanto la solucion es el producto, sin aproximacion.
    Esto es lo que permite verificar el termino de inactivacion de forma
    exacta y por separado del transporte.
    """
    return crank_sphere(r, t, a, D, c0) * np.exp(-k * t)


def selfcheck(a, D, verbose=True):
    """La referencia debe conservar la masa inicial c0*(4/3)*pi*a^3.

    Se ejecuta ANTES de usar la referencia como patron: una formula citada
    de memoria no se da por buena sin verificar.
    """
    M0 = 4.0 / 3.0 * np.pi * a ** 3
    ok = True
    if verbose:
        print("--- autoverificacion de la solucion analitica ---")
    for t in (60.0, 3600.0, 86400.0):
        M, _ = quad(lambda r: 4 * np.pi * r ** 2 * crank_sphere(r, t, a, D)[0],
                    1e-12, a + 12 * np.sqrt(D * t), limit=400)
        err = M / M0 - 1
        ok &= abs(err) < 1e-3
        if verbose:
            print(f"  t={t:8.0f} s   masa/masa0 - 1 = {err:+.3e}")
    if verbose:
        print(f"  autoverificacion: {'OK' if ok else 'FALLO'}\n")
    return ok
