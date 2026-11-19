from socle import *
import time, random, math
from collections import deque

# Voisinage relocate : on retire une mission de sa liste (tournée ou reportées)
# et on la remet ailleurs (autre position, autre technicien ou reportées).
# C'est un générateur (yield) : les voisins sont donnés un par un, sans tout
# garder en mémoire. Seuls les voisins réalisables sont renvoyés.
def generer_voisins(S, N):

    listes = N["techs"] + ["reportees"]

    # on parcourt chaque mission de chaque liste
    for source in listes:
        for position_source, mission in enumerate(S[source]):

            # On retire la mission de sa liste
            route_source = S[source][:position_source] + S[source][position_source + 1:]

            for destination in listes:

                if source == destination == "reportees":
                    continue

                # Vérifier la compétence avant de tester les positions
                if destination != "reportees":
                    competence = N["comp"][mission]

                    if N["habilite"][destination][competence] != 1:
                        continue

                if source == destination:
                    base = route_source
                else:
                    base = S[destination]

                if destination == "reportees":
                    positions = [len(base)]
                else:
                    positions = range(len(base) + 1)

                for position in positions:

                    # Éviter le même planning et les échanges en double
                    if source == destination:
                        if position == position_source or position == position_source + 1:
                            continue

                    nouvelle_route = base[:position] + [mission] + base[position:]

                    voisin = {cle: S[cle] for cle in S}

                    if source == destination:
                        voisin[source] = nouvelle_route
                    else:
                        voisin[source] = route_source
                        voisin[destination] = nouvelle_route

                    # Vérifier seulement les tournées modifiées
                    if source != "reportees":
                        if not verifier_tournee(voisin, N, source):
                            continue

                    if destination != "reportees" and destination != source:
                        if not verifier_tournee(voisin, N, destination):
                            continue

                    mouvement = {
                        "mission": mission,
                        "source": source,
                        "destination": destination,
                        "position_source": position_source,
                        "position_destination": position
                    }

                    # on renvoie le voisin et la description du mouvement
                    yield voisin, mouvement

# même voisinage mais rangé dans deux listes (pratique pour compter ou afficher)
def voisinage(S, N):

    voisins = []
    mouvements = []

    for V, mouvement in generer_voisins(S, N):
        voisins.append(V)
        mouvements.append(mouvement)

    return voisins, mouvements

# Descente « première amélioration » : on parcourt les voisins et on prend
# le premier qui fait baisser le coût. On recommence jusqu'à ce qu'aucun voisin
# ne soit meilleur (optimum local).
def premiere_amelioration(S0, N):

    S = {cle: S0[cle][:] for cle in S0}

    while True:

        amelioration = False
        cout_actuel = f(S, N)

        for V, mouvement in generer_voisins(S, N):

            if f(V, N) < cout_actuel - 1e-9:
                S = V
                amelioration = True
                break

        if amelioration == False:
            break

    return S

# Descente « plus forte pente » : à chaque étape on regarde TOUS les voisins
# et on prend le meilleur. Plus lent par étape, mais chaque pas est le plus grand possible.
def plus_forte_pente(S0, N):

    S = {cle: S0[cle][:] for cle in S0}

    while True:

        meilleur = S
        meilleur_cout = f(S, N)

        # On examine tous les voisins
        for V, mouvement in generer_voisins(S, N):

            cout_voisin = f(V, N)

            if cout_voisin < meilleur_cout - 1e-9:
                meilleur = V
                meilleur_cout = cout_voisin

        # On s'arrête si aucun voisin n'est meilleur
        if meilleur == S:
            break

        S = meilleur

    return S

# Recherche tabou. Pour chaque essai (5 graines), on part de S0 et pendant 180 s :
#  - on parcourt le voisinage relocate et on garde 40 candidats non tabous tirés au hasard
#    (tirage par réservoir, pour ne pas stocker tous les voisins) ;
#  - on prend le meilleur des 40, même s'il est moins bon que la solution actuelle ;
#  - le mouvement inverse (remettre la mission chez son ancien technicien) devient tabou
#    pendant L itérations.
# On relève le meilleur coût à 60, 120 et 180 s.
import time
import random
from collections import deque

def recherche_tabou(S0, N, L):

    resultats = []
    solutions = []

    for essai in range(1, 6):

        # générateur aléatoire propre à l'essai, pour pouvoir refaire le même calcul
        rng = random.Random(essai)

        S = {cle: S0[cle][:] for cle in S0}
        meilleure = {cle: S[cle][:] for cle in S}
        meilleur_cout = f(S, N)

        # deque(maxlen=L) : quand la liste est pleine, le plus ancien tabou sort tout seul
        liste_tabou = deque(maxlen=L)
        couts = {60: None, 120: None, 180: None}

        debut = time.perf_counter()

        while time.perf_counter() - debut < 180:

            candidats = []
            nb = 0

            # Générer des voisins et tirer 40 candidats au hasard
            for V, mouvement in generer_voisins(S, N):

                temps = time.perf_counter() - debut

                for t in couts:
                    if temps >= t and couts[t] is None:
                        couts[t] = meilleur_cout

                if temps >= 180:
                    break

                # un mouvement est tabou si on remet la mission là où elle était avant
                cle = (mouvement["mission"], mouvement["destination"])

                if cle in liste_tabou:
                    continue

                nb += 1

                # tirage par réservoir : chaque voisin autorisé a la même chance d'être parmi les 40
                if len(candidats) < 40:
                    candidats.append((V, mouvement))
                else:
                    j = rng.randrange(nb)
                    if j < 40:
                        candidats[j] = (V, mouvement)

            if time.perf_counter() - debut >= 180 or not candidats:
                break

            # Choisir le meilleur candidat autorisé
            rng.shuffle(candidats)
            S, mouvement = min(candidats, key=lambda x: f(x[0], N))

            if time.perf_counter() - debut >= 180:
                break

            # Mémoriser le mouvement inverse
            liste_tabou.append((
                mouvement["mission"],
                mouvement["source"]
            ))

            if f(S, N) < meilleur_cout:
                meilleur_cout = f(S, N)
                meilleure = {cle: S[cle][:] for cle in S}

        temps_reel = time.perf_counter() - debut

        # si l'essai s'est arrêté avant un seuil, on prend le meilleur coût final
        for t in couts:
            if couts[t] is None:
                couts[t] = meilleur_cout

        resultats.append({
            "Essai": essai,
            "Coût 60": round(couts[60], 2),
            "Coût 120": round(couts[120], 2),
            "Coût 180": round(couts[180], 2),
            "Reports": len(meilleure["reportees"]),
            "Temps": round(temps_reel, 2)
        })

        solutions.append(meilleure)

    return resultats, solutions

# Méthode hybride ALNS + tabou (amélioration proposée avec l'aide d'une IA, voir la déclaration).
# À chaque itération : on détruit une partie de la solution (on reporte 10 à 25 % des missions),
# on la répare (insertion gloutonne ou par regret), puis on fait quelques pas de tabou.
# Les 4 couples destruction / réparation ont un poids qui augmente quand ils marchent bien.
import time
import random
import math

def copier_solution(S):
    return {cle: valeur[:] for cle, valeur in S.items()}


# Étape 1 : retirer plusieurs interventions
def detruire_hybride(S, N, rng, methode, quantite):

    S = copier_solution(S)

    for _ in range(quantite):

        missions = [
            (t, i, m)
            for t in N["techs"]
            for i, m in enumerate(S[t])
        ]

        if not missions:
            break

        if methode == "aleatoire":
            t, i, m = rng.choice(missions)

        else:
            # Retirer une intervention coûteuse en distance
            def cout_retrait(x):
                t, i, m = x
                sans = S[t][:i] + S[t][i+1:]
                return (distance_tournee(N, t, S[t])
                        - distance_tournee(N, t, sans))

            t, i, m = max(missions, key=cout_retrait)

        S[t].pop(i)
        S["reportees"].append(m)

    return S


# Étape 2 : reconstruire les tournées
def reparer_hybride(S, N, methode, debut, temps_max):

    S = copier_solution(S)

    while time.perf_counter() - debut < temps_max:

        choix = None

        for mission in S["reportees"]:

            options = []

            for t in N["techs"]:

                if time.perf_counter() - debut >= temps_max:
                    return S

                if N["habilite"][t][N["comp"][mission]] != 1:
                    continue

                d0 = distance_tournee(N, t, S[t])

                for pos in range(len(S[t]) + 1):

                    S[t].insert(pos, mission)

                    if verifier_tournee(S, N, t):

                        surplus = distance_tournee(N, t, S[t]) - d0

                        if surplus < N["penalite"] - 1e-9:
                            options.append((surplus, t, pos))

                    S[t].pop(pos)

            if not options:
                continue

            options.sort()
            d, t, pos = options[0]

            if methode == "gloutonne":
                score = N["penalite"] - d

            else:
                # regret = écart entre la 2e meilleure insertion et la meilleure :
                # on insère d'abord les missions qu'on risque de ne plus pouvoir bien placer
                # Réparation par regret
                if len(options) > 1:
                    second = min(N["penalite"], options[1][0])
                else:
                    second = N["penalite"]

                score = second - d

            if choix is None or score > choix[0]:
                choix = (score, mission, t, pos)

        if choix is None:
            break

        _, mission, t, pos = choix

        S["reportees"].remove(mission)
        S[t].insert(pos, mission)

    return S


# Étape 3 : méthode hybride ALNS + Tabou
def hybride_alns_tabou(S0, N, L, temps_max=180, graine=1):

    rng = random.Random(graine)
    debut = time.perf_counter()

    S = copier_solution(S0)
    meilleure = copier_solution(S0)
    meilleur_cout = f(S0, N)

    evolution = [(0.0, meilleur_cout)]

    # Quatre combinaisons destruction / réparation
    operateurs = [
        (a, b)
        for a in ("aleatoire", "couteux")
        for b in ("gloutonne", "regret")
    ]

    # au départ tous les opérateurs ont le même poids
    poids = {op: 1.0 for op in operateurs}
    iterations = 0

    while time.perf_counter() - debut < temps_max:

        # Choisir un opérateur selon ses performances
        op = rng.choices(
            operateurs,
            weights=[poids[o] for o in operateurs]
        )[0]

        planifiees = sum(len(S[t]) for t in N["techs"])

        # nombre de missions retirées : entre 10 et 25 % des missions planifiées
        q = max(1, round(
            planifiees * rng.uniform(0.10, 0.25)
        ))

        candidat = detruire_hybride(S, N, rng, op[0], q)

        candidat = reparer_hybride(
            candidat, N, op[1], debut, temps_max
        )

        # Amélioration locale par recherche tabou
        liste_tabou = []
        amelioration = False

        for _ in range(L + 5):

            if time.perf_counter() - debut >= temps_max:
                break

            candidats = []
            nb = 0

            for V, m in generer_voisins(candidat, N):

                if time.perf_counter() - debut >= temps_max:
                    break

                if (m["mission"], m["destination"]) in liste_tabou:
                    continue

                nb += 1

                if len(candidats) < 40:
                    candidats.append((V, m))
                else:
                    j = rng.randrange(nb)
                    if j < 40:
                        candidats[j] = (V, m)

            if not candidats:
                break

            rng.shuffle(candidats)

            candidat, mouvement = min(
                candidats,
                key=lambda x: f(x[0], N)
            )

            liste_tabou.append((
                mouvement["mission"],
                mouvement["source"]
            ))

            if len(liste_tabou) > L:
                liste_tabou.pop(0)

            cout = f(candidat, N)

            if cout < meilleur_cout - 1e-9:
                meilleure = copier_solution(candidat)
                meilleur_cout = cout
                amelioration = True

                evolution.append((
                    time.perf_counter() - debut,
                    meilleur_cout
                ))

        # Accepter parfois une solution moins bonne
        # pour explorer une autre région
        cout_candidat = f(candidat, N)
        cout_actuel = f(S, N)

        # température qui baisse avec le temps (comme dans un recuit)
        temperature = max(
            0.1,
            0.1 * f(S0, N) *
            (1 - (time.perf_counter() - debut) / temps_max)
        )

        accepte = (
            cout_candidat <= cout_actuel
            or rng.random() < math.exp(
                min(0, (cout_actuel - cout_candidat) / temperature)
            )
        )

        if accepte:
            S = candidat

        # Adapter le poids des opérateurs
        # récompense : 6 si nouveau record, 2 si accepté, 1 sinon
        recompense = 6 if amelioration else 2 if accepte else 1

        poids[op] = 0.9 * poids[op] + 0.1 * recompense

        iterations += 1

    # Coûts aux paliers de temps, si atteints
    couts = {
        t: min(c for moment, c in evolution if moment <= t)
        for t in (60, 120, 180)
        if t <= temps_max
    }

    infos = {
        "cout": round(meilleur_cout, 2),
        "temps": round(time.perf_counter() - debut, 2),
        "iterations": iterations,
        "couts": couts
    }

    return meilleure, infos