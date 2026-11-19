# Méthode epsilon-contrainte : on résout une suite de problèmes mono-objectif
# (min D sous R <= epsilon) avec le recuit de recuit.py.

import random

from recuit import *

# ---------------------------------------------------------------------------
# Méthode epsilon-contrainte
# ---------------------------------------------------------------------------
#   min D(S)   sous   R(S) <= epsilon
# La contrainte est remplacée par une pénalité : coût = D + M x max(0, R - epsilon)
# avec M = 100 x pénalité. Au début on avait mis un coût infini, mais inf - inf
# donne nan et le recuit n'acceptait plus aucun voisin.
# Les epsilon sont traités dans l'ordre croissant : chaque recuit part de la solution
# du epsilon précédent, qui respecte déjà R <= epsilon.
# Chaque epsilon n'a qu'environ 16 s, d'où le refroidissement calé sur le temps.

def objectifs(S, N):
    # les deux objectifs : distance D (arrondie au mètre) et nombre de reports R
    R = len(S["reportees"])
    D = f(S, N) - N["penalite"] * R
    return round(D, 3), R


def domine(a, b):
    # a domine b : aussi bon sur D et sur R, et strictement meilleur sur au moins un
    return a[0] <= b[0] + 1e-9 and a[1] <= b[1] and (a[0] < b[0] - 1e-9 or a[1] < b[1])


def filtrer_non_domines(points):
    # points = liste de (D, R, solution). On enlève les doublons puis les points dominés.
    uniques = {}
    for p in points:
        cle = (round(p[0], 3), p[1])
        if cle not in uniques:
            uniques[cle] = p
    pts = list(uniques.values())
    nd = [p for p in pts if not any(domine((q[0], q[1]), (p[0], p[1])) for q in pts if q is not p)]
    return sorted(nd, key=lambda p: (p[1], p[0]))


def hypervolume_2d(front, ref):
    # Aire dominée par le front et bornée par le point de référence ref = (D_ref, R_ref).
    # On parcourt les points par R croissant et on additionne des rectangles.
    pts = sorted({(p[0], p[1]) for p in front if p[0] <= ref[0] and p[1] <= ref[1]}, key=lambda p: (p[1], p[0]))
    hv, D_prec = 0.0, ref[0]
    for D, R in pts:
        if D < D_prec:
            hv += (D_prec - D) * (ref[1] - R)
            D_prec = D
    return hv


def grille_epsilon(N, nb=11):
    # Petites instances (n <= 12) : on teste toutes les valeurs 0, 1, ..., n.
    # Sinon 11 valeurs régulières de 0 à n (un point tous les 10 % de reports).
    n = len(N["interventions"])
    if n <= 12:
        return list(range(n + 1))
    return sorted(set(round(n * k / (nb - 1)) for k in range(nb)))


def epsilon_contrainte(S0, N, epsilons=None, temps_par_epsilon=15, graine=None, tau0=0.1):

    if epsilons is None:
        epsilons = grille_epsilon(N)
    M = 100 * N["penalite"]

    # T0 calculé une seule fois sur S0, puis gardé pour tous les epsilon
    random.seed(graine)
    T0 = calculer_T0(S0, N, tau0)

    resultats = []
    depart = S0

    for k, eps in enumerate(sorted(epsilons)):

        # coût pénalisé pour ce epsilon (eps=eps pour figer la valeur dans la fonction)
        def cout(D, R, eps=eps):
            return D + M * max(0, R - eps)

        g = None if graine is None else graine * 1000 + k
        S, valeur, infos = recuit_simule(depart, N, temps_max=temps_par_epsilon, graine=g, T0=T0,
                                         cout=cout, duree_cycle=0.97 * temps_par_epsilon)
        D, R = objectifs(S, N)
        resultats.append({"epsilon": eps, "D": D, "R": R, "respecte": R <= eps,
                          "temps": infos["temps"], "iterations": infos["iterations"], "solution": S})
        # chaînage : le epsilon suivant part de cette solution si elle respecte la contrainte
        if R <= eps:
            depart = S

    # on ne garde que les points qui respectent leur contrainte et qui ne sont pas dominés
    front = filtrer_non_domines([(r["D"], r["R"], r["solution"]) for r in resultats if r["respecte"]])
    return resultats, front