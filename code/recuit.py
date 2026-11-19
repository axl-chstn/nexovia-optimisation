# Recuit simulé.
# On utilise seulement les fonctions du socle commun (verifier_tournee,
# distance_tournee, f, est_realisable) et le même mouvement que le voisinage
# relocate (on enlève une mission et on la remet ailleurs).

import math
import random
import time

from socle import *


# ---------------------------------------------------------------------------
# 1. Tirer un voisin au hasard
# ---------------------------------------------------------------------------
# generer_voisins construit TOUS les voisins relocate. Le recuit n'en utilise
# qu'un par itération, donc on tire directement les 4 choix du mouvement au
# hasard (liste de départ, mission, destination, position) et on ne construit
# qu'un seul voisin. C'est ce qui nous a fait passer d'environ 2 à 30 000
# itérations par seconde sur N200.

def voisin_aleatoire(S, N):

    listes = N["techs"] + ["reportees"]

    # Choisir une liste non vide, puis une mission dans cette liste
    source = random.choice([l for l in listes if len(S[l]) > 0])
    position_source = random.randrange(len(S[source]))
    mission = S[source][position_source]

    # Choisir une destination : un technicien compétent ou les reportées
    competence = N["comp"][mission]
    destinations = [t for t in N["techs"] if N["habilite"][t][competence] == 1] + ["reportees"]
    destination = random.choice(destinations)

    # reportée -> reportée : ça ne change rien, on rejette le tirage
    if source == "reportees" and destination == "reportees":
        return None, None

    # On retire la mission de sa liste
    route_source = S[source][:position_source] + S[source][position_source + 1:]

    if source == destination:
        base = route_source
    else:
        base = S[destination]

    # Choisir une position (pour les reportées, l'ordre ne compte pas : à la fin)
    if destination == "reportees":
        position = len(base)
    else:
        position = random.randint(0, len(base))

    # Remettre la mission à sa place ne change rien
    if source == destination and position == position_source:
        return None, None

    nouvelle_route = base[:position] + [mission] + base[position:]

    # Construction du voisin (on copie les listes pour ne jamais modifier S)
    voisin = {cle: S[cle][:] for cle in S}
    if source == destination:
        voisin[source] = nouvelle_route
    else:
        voisin[source] = route_source
        voisin[destination] = nouvelle_route

    # Seules les 2 tournées modifiées peuvent être devenues impossibles,
    # donc on ne vérifie qu'elles
    for tech in [source, destination]:
        if tech != "reportees" and not verifier_tournee(voisin, N, tech):
            return None, None

    mouvement = {"mission": mission, "source": source, "destination": destination,
                 "position_source": position_source, "position_destination": position}
    return voisin, mouvement


# ---------------------------------------------------------------------------
# 2. Température initiale T0
# ---------------------------------------------------------------------------
# On tire des voisins de S0 et on garde ceux qui dégradent le coût.
# Avec leur dégradation moyenne d, on choisit T0 pour qu'au début une
# dégradation moyenne soit acceptée avec la probabilité tau0 :
#     exp(-d / T0) = tau0   donc   T0 = -d / ln(tau0)
# Comme ça T0 s'adapte tout seul à l'échelle des coûts de chaque instance.

def calculer_T0(S0, N, tau0, nb=500):

    cout_S0 = f(S0, N)
    degradations = []
    essais = 0

    # au plus 50 x 500 = 25 000 tirages (en pratique moins de 9 000 suffisent)
    while len(degradations) < nb and essais < 50 * nb:
        essais += 1
        V, mouvement = voisin_aleatoire(S0, N)
        if V is not None:
            delta = f(V, N) - cout_S0
            if delta > 0:
                degradations.append(delta)

    # cas limite : aucune dégradation trouvée, on prend une valeur par défaut
    if len(degradations) == 0:
        return 1.0

    moyenne = sum(degradations) / len(degradations)
    return -moyenne / math.log(tau0)


# ---------------------------------------------------------------------------
# 3. Recuit simulé
# ---------------------------------------------------------------------------
# Paramètres :
#   tau0      : taux d'acceptation au départ (sert à calculer T0)
#   alpha     : refroidissement, T = alpha * T à la fin de chaque palier
#   k_palier  : un palier dure k_palier * n itérations (n = nombre d'interventions)
#   temps_max : budget en secondes, c'est le seul critère d'arrêt
# Réchauffage : quand T passe sous T0 / 1000 et qu'il reste du temps, on repart
# de la meilleure solution avec T = T0.
#
# Pour aller vite on ne recalcule que la distance des 2 tournées modifiées :
#   nouvelle distance = distance actuelle + (distance des tournées modifiées après - avant)
#
# Options utilisées par les autres fonctions de ce fichier :
#   cout        : autre fonction à minimiser (pour l'epsilon-contrainte)
#   duree_cycle : refroidissement calé sur le temps, en secondes (epsilon-contrainte et essais P)
#   Q           : variante "P essais" du cours. L'essai s'arrête après Q itérations sans
#                 améliorer la meilleure solution, et il n'y a plus de réchauffage.
#                 Avec Q = None (par défaut), le recuit est celui du rapport.

def recuit_simule(S0, N, temps_max=60, graine=None, tau0=0.1, alpha=0.99, k_palier=20,
                  T0=None, cout=None, duree_cycle=None, garder_trace=False, Q=None):

    random.seed(graine)
    debut = time.perf_counter()

    # par défaut on minimise f = D + pénalité x R
    if cout is None:
        def cout(D, R):
            return D + N["penalite"] * R

    if T0 is None:
        T0 = calculer_T0(S0, N, tau0)
    T_min = T0 / 1000

    # longueur d'un palier (au moins 10 itérations pour les toutes petites instances)
    n = len(N["interventions"])
    if duree_cycle is None:
        palier = max(10, k_palier * n)
    else:
        palier = max(10, n)

    # Solution courante : on garde la distance de chaque tournée pour le calcul rapide
    S = {cle: S0[cle][:] for cle in S0}
    distance = {tech: distance_tournee(N, tech, S[tech]) for tech in N["techs"]}
    D = sum(distance.values())
    R = len(S["reportees"])
    cout_actuel = cout(D, R)

    meilleure = {cle: S[cle][:] for cle in S}
    meilleur_cout = cout_actuel
    temps_meilleur = 0.0
    historique = [(0.0, meilleur_cout)]          # (temps, meilleur coût) à chaque amélioration
    trace = []                                   # (temps, coût courant, température)

    T = T0
    debut_cycle = time.perf_counter()
    iterations = acceptes = rechauffages = 0
    dans_palier = 0
    sans_amelioration = 0                        # c'est le compteur J du cours

    while time.perf_counter() - debut < temps_max:

        iterations += 1
        sans_amelioration += 1
        if Q is not None and sans_amelioration > Q:
            break                                # fin de l'essai (critère Q du cours)
        V, mouvement = voisin_aleatoire(S, N)

        # V = None : voisin impossible, l'itération est perdue et on retire au hasard
        if V is not None:

            # Variation de distance : seulement les tournées modifiées
            nouvelles = {}
            for tech in [mouvement["source"], mouvement["destination"]]:
                if tech != "reportees":
                    nouvelles[tech] = distance_tournee(N, tech, V[tech])
            D_voisin = D + sum(nouvelles[t] - distance[t] for t in nouvelles)
            R_voisin = len(V["reportees"])
            cout_voisin = cout(D_voisin, R_voisin)

            difference = cout_voisin - cout_actuel

            # Règle de Metropolis : on accepte toujours si c'est mieux,
            # sinon avec la probabilité exp(-difference / T)
            if difference <= 0 or random.random() < math.exp(-difference / T):
                S = V
                distance.update(nouvelles)
                D, R, cout_actuel = D_voisin, R_voisin, cout_voisin
                acceptes += 1

                # nouvelle meilleure solution (1e-9 pour ignorer les égalités à l'arrondi près)
                if cout_actuel < meilleur_cout - 1e-9:
                    meilleure = {cle: S[cle][:] for cle in S}
                    meilleur_cout = cout_actuel
                    temps_meilleur = time.perf_counter() - debut
                    historique.append((temps_meilleur, meilleur_cout))
                    sans_amelioration = 0

        # Fin de palier : on refroidit
        dans_palier += 1
        if dans_palier >= palier:
            dans_palier = 0

            if garder_trace:
                trace.append((time.perf_counter() - debut, cout_actuel, T))

            if duree_cycle is None:
                # refroidissement classique
                T = alpha * T
            else:
                # refroidissement calé sur le temps : T va de T0 à T0/1000
                # exactement pendant duree_cycle secondes
                t_cycle = time.perf_counter() - debut_cycle
                T = T0 * (1 / 1000) ** min(1.0, t_cycle / duree_cycle)
                if t_cycle >= duree_cycle:
                    T = T_min / 2

            # Réchauffage depuis la meilleure solution (sauf en mode "essais du cours")
            if T < T_min and Q is None:
                T = T0
                rechauffages += 1
                debut_cycle = time.perf_counter()
                S = {cle: meilleure[cle][:] for cle in meilleure}
                distance = {tech: distance_tournee(N, tech, S[tech]) for tech in N["techs"]}
                D = sum(distance.values())
                R = len(S["reportees"])
                cout_actuel = meilleur_cout

    duree = time.perf_counter() - debut
    historique.append((duree, meilleur_cout))
    infos = {"iterations": iterations, "acceptes": acceptes, "rechauffages": rechauffages,
             "T0": T0, "palier": palier, "temps": duree, "temps_meilleur": temps_meilleur,
             "historique": historique, "trace": trace}
    return meilleure, meilleur_cout, infos