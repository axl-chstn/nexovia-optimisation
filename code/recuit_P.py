# Complément : variante du recuit en P essais indépendants, comme dans le schéma du cours.
# On réutilise le recuit de recuit.py, avec ses options duree_cycle et Q.

import random
import time

from recuit import *

# Schéma du cours : pour k de 1 à P, x0 = solution aléatoire, T = T0, on refroidit
# jusqu'à Q itérations sans amélioration, et on garde la meilleure solution.
# Différence avec notre réchauffage : on ne repart pas de la meilleure solution
# mais d'une nouvelle solution aléatoire (on diversifie au lieu d'intensifier).

def solution_aleatoire(S0, N, nb_pas=None):
    # Solution "aléatoire" mais toujours admissible : on part de S0 et on fait
    # nb_pas mouvements relocate tirés au hasard, en les acceptant tous même
    # s'ils dégradent. Par défaut nb_pas = n, donc chaque mission bouge à peu près une fois.
    if nb_pas is None:
        nb_pas = len(N["interventions"])
    S = {cle: S0[cle][:] for cle in S0}
    pas = essais = 0
    while pas < nb_pas and essais < 100 * nb_pas:
        essais += 1
        V, mouvement = voisin_aleatoire(S, N)
        if V is not None:                     # voisin admissible : on le prend sans condition
            S = V
            pas += 1
    return S


def recuit_essais_P(S0, N, temps_max=180, P=3, Q=None, graine=None, tau0=0.1, nb_pas=None):
    # Recuit comme dans le cours : P essais indépendants, chacun depuis une solution aléatoire.
    # - le budget total est partagé : chaque essai reçoit (temps restant / essais restants),
    #   donc si un essai s'arrête tôt, le temps qu'il laisse revient aux suivants ;
    # - chaque essai refroidit selon le temps (comme pour l'epsilon-contrainte) pour faire
    #   un cycle complet de T0 à T0/1000 dans sa part de temps ;
    # - un essai s'arrête après Q itérations sans amélioration. Par défaut Q = 10 000 x n,
    #   environ 2 fois le plus long écart entre deux améliorations qu'on a mesuré
    #   (à peu près 5 000 x n sur N50), pour ne couper un essai que quand il est vraiment figé.
    random.seed(graine)
    debut = time.perf_counter()
    n = len(N["interventions"])
    if Q is None:
        Q = 10000 * n
    T0 = calculer_T0(S0, N, tau0)              # même T0 pour tous les essais

    meilleure, meilleur_cout, essais = None, float("inf"), []
    for k in range(P):
        reste = temps_max - (time.perf_counter() - debut)
        if reste <= 0:
            break
        part = reste / (P - k)
        x0 = solution_aleatoire(S0, N, nb_pas)
        g = None if graine is None else graine * 1000 + k
        S, c, infos = recuit_simule(x0, N, temps_max=part, graine=g, T0=T0,
                                    duree_cycle=0.97 * part, Q=Q)
        # on garde le détail de chaque essai pour l'analyse
        essais.append({"essai": k + 1, "cout_depart": round(f(x0, N), 2), "cout": round(c, 2),
                       "temps": round(infos["temps"], 2), "iterations": infos["iterations"]})
        if c < meilleur_cout:
            meilleure, meilleur_cout = S, c

    infos = {"essais": essais, "T0": T0, "Q": Q, "temps": time.perf_counter() - debut}
    return meilleure, meilleur_cout, infos