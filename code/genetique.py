# Partie Axel : algorithme génétique.
# Une solution (un individu) est le planning lui-même : une liste ordonnée de missions
# par technicien, plus la liste des reportées. On réutilise f, est_realisable,
# verifier_tournee et distance_tournee du socle commun.
# Les fonctions finissent par _ag pour ne pas se mélanger avec celles des autres parties.

from socle import *
import random
import time
import pandas as pd


def copie_ag(S):
    # copie d'un planning (on copie chaque liste pour ne pas modifier l'original)
    return {cle: missions[:] for cle, missions in S.items()}


def cle_ag(S, N):
    # "Empreinte" d'un planning, pour repérer les doublons dans la population.
    # L'ordre des reports n'a aucune importance, donc on les trie.
    return (tuple(tuple(S[t]) for t in N["techs"]),
            tuple(sorted(S["reportees"])))


def completer_ag(S, ordre, N, rng, limite, diversifier=False):
    # Essaie d'insérer les missions reportées (dans l'ordre donné) sans rendre le
    # planning impossible. Une mission reste reportée si aucune insertion n'est retenue.
    # limite = heure (perf_counter) à laquelle il faut s'arrêter.
    for mission in ordre:
        if time.perf_counter() >= limite:
            break
        if mission not in S["reportees"]:
            continue

        # on teste toutes les positions chez tous les techniciens
        choix = []
        for tech in N["techs"]:
            ancienne_distance = distance_tournee(N, tech, S[tech])
            for position in range(len(S[tech]) + 1):
                if time.perf_counter() >= limite:
                    return S
                S[tech].insert(position, mission)
                if verifier_tournee(S, N, tech):
                    ajout = distance_tournee(N, tech, S[tech]) - ancienne_distance
                    choix.append((ajout, tech, position))
                S[tech].pop(position)

        if choix:
            choix.sort()
            # Diversification : on choisit au hasard parmi les 3 meilleures insertions.
            # Sinon on prend la meilleure.
            ajout, tech, position = rng.choice(choix[:3]) if diversifier else choix[0]
            # sans diversification, on n'insère que si ça coûte moins cher que le report
            if diversifier or ajout <= N["penalite"]:
                S[tech].insert(position, mission)
                S["reportees"].remove(mission)
    return S


def individu_aleatoire_ag(N, rng, limite):
    # Nouvel individu : même principe que le glouton, mais avec un ordre des missions
    # mélangé et des insertions un peu au hasard, pour avoir des individus différents.
    ordre = list(N["duree"])
    rng.shuffle(ordre)
    S = {tech: [] for tech in N["techs"]}
    S["reportees"] = ordre[:]
    return completer_ag(S, ordre, N, rng, limite, diversifier=True)


def croisement_ag(parent1, parent2, N, rng, limite):
    # L'enfant part de "tout reporté" puis récupère des tournées des parents.
    enfant = {tech: [] for tech in N["techs"]}
    enfant["reportees"] = list(N["duree"])

    # Pour chaque technicien, hériter de la tournée d'un des deux parents.
    # Une mission déjà prise ailleurs n'est pas copiée une seconde fois.
    techniciens = N["techs"][:]
    rng.shuffle(techniciens)
    for tech in techniciens:
        parent = rng.choice([parent1, parent2])
        for mission in parent[tech]:
            if time.perf_counter() >= limite:
                return enfant
            if mission in enfant["reportees"]:
                enfant[tech].append(mission)
                # si la tournée devient impossible, on enlève la mission
                if verifier_tournee(enfant, N, tech):
                    enfant["reportees"].remove(mission)
                else:
                    enfant[tech].pop()

    # Réparation : on essaie de réinsérer les missions encore reportées.
    ordre = enfant["reportees"][:]
    rng.shuffle(ordre)
    return completer_ag(enfant, ordre, N, rng, limite)


def mutation_ag(S, N, rng, limite):
    # Petit changement aléatoire. On fait jusqu'à 20 tentatives et on garde la première
    # qui donne un planning différent et réalisable. Sinon on renvoie une copie de S.
    listes = N["techs"] + ["reportees"]
    for _ in range(20):
        if time.perf_counter() >= limite:
            break
        voisin = copie_ag(S)
        non_vides = [cle for cle in listes if voisin[cle]]
        if not non_vides:
            break
        source = rng.choice(non_vides)
        i = rng.randrange(len(voisin[source]))

        if rng.random() < 0.7:
            # 70 % du temps : déplacer une mission (la réordonner, la reporter ou la réinsérer)
            destination = rng.choice(listes)
            if source == destination == "reportees":
                continue
            mission = voisin[source].pop(i)
            position = rng.randrange(len(voisin[destination]) + 1)
            voisin[destination].insert(position, mission)
        else:
            # 30 % du temps : échanger deux missions ; avec les reports, ça fait un remplacement
            destination = rng.choice(non_vides)
            j = rng.randrange(len(voisin[destination]))
            voisin[source][i], voisin[destination][j] = (
                voisin[destination][j], voisin[source][i])

        if cle_ag(voisin, N) != cle_ag(S, N) and est_realisable(voisin, N):
            return voisin
    return copie_ag(S)


def algorithme_genetique(S0, N, taille_population=20, proba_croisement=0.8,
                        proba_mutation=0.25, budgets=(60, 120, 180),
                        graines=(1, 2, 3, 4, 5), diversite=True):
    # Lance une exécution par graine. On relève le meilleur coût à chaque budget
    # (60, 120, 180 s) dans la même exécution.
    # diversite=False ne sert qu'au test d'ablation (population sans immigrants ni refus des doublons).

    # quelques contrôles sur les paramètres
    if taille_population < 4:
        raise ValueError("La population doit contenir au moins 4 individus.")
    if not 0 <= proba_croisement <= 1 or not 0 <= proba_mutation <= 1:
        raise ValueError("Les probabilités doivent être entre 0 et 1.")
    budgets = sorted(set(budgets))
    if not budgets or budgets[0] <= 0:
        raise ValueError("Les budgets doivent être strictement positifs.")
    if not est_realisable(S0, N):
        raise ValueError("La solution initiale n'est pas réalisable.")

    resultats, solutions = [], []
    for graine in graines:
        rng = random.Random(graine)      # générateur propre à cette graine
        meilleure = copie_ag(S0)
        meilleur_cout = f(S0, N)
        couts = {budget: None for budget in budgets}
        historique = [(0.0, meilleur_cout)]
        generations = stagnation = 0
        suivi_population = []
        dernier_suivi = -1.0
        debut = time.perf_counter()
        limite = debut + budgets[-1]

        def observer(S):
            # Calcule le coût d'un nouvel individu et met à jour le meilleur connu.
            nonlocal meilleure, meilleur_cout
            cout = f(S, N)
            temps = time.perf_counter() - debut
            # Un résultat trouvé après un seuil ne compte pas avant ce seuil :
            # on fige la valeur d'un budget dès qu'on le dépasse.
            for budget in budgets:
                if temps >= budget and couts[budget] is None:
                    couts[budget] = meilleur_cout
            if temps <= budgets[-1] and cout < meilleur_cout - 1e-9:
                meilleure, meilleur_cout = copie_ag(S), cout
                historique.append((temps, cout))
            return cout

        # Population initiale : S0 + des individus aléatoires.
        # Chaque individu est stocké avec son coût.
        population = [(copie_ag(S0), meilleur_cout)]
        vus = {cle_ag(S0, N)}
        for _ in range(10 * taille_population):
            if len(population) >= taille_population or time.perf_counter() >= limite:
                break
            if diversite:
                S = individu_aleatoire_ag(N, rng, limite)
            else:
                # témoin sans diversité : simples mutations de S0
                S = copie_ag(S0)
                for _ in range(rng.randint(1, 3)):
                    S = mutation_ag(S, N, rng, limite)
            cout = observer(S)
            cle = cle_ag(S, N)
            if not diversite or cle not in vus:
                population.append((S, cout))
                vus.add(cle)

        def selection():
            # Tournoi de 2 : on tire deux individus et on garde le meilleur.
            # Ça garde une pression de sélection modérée.
            candidats = rng.sample(population, min(2, len(population)))
            return min(candidats, key=lambda individu: individu[1])[0]

        # Boucle des générations, jusqu'à la fin du budget
        while time.perf_counter() < limite:
            ancien_record = meilleur_cout
            population.sort(key=lambda individu: individu[1])
            nouvelle = population[:2]  # Élitisme : on garde les deux meilleurs.
            vus = {cle_ag(S, N) for S, cout in nouvelle}

            # Après 10 générations sans progrès, on renforce la diversification :
            # mutation à 0,7 au moins et 40 % d'immigrants au lieu de 20 %.
            mutation = max(proba_mutation, 0.7) if diversite and stagnation >= 10 else proba_mutation
            proportion = 0.4 if stagnation >= 10 else 0.2
            nb_immigrants = max(1, int(taille_population * proportion)) if diversite else 0

            for _ in range(10 * taille_population):
                if len(nouvelle) >= taille_population or time.perf_counter() >= limite:
                    break
                if len(nouvelle) < 2 + nb_immigrants:
                    # immigrant : individu tout neuf
                    enfant = individu_aleatoire_ag(N, rng, limite)
                else:
                    parent1, parent2 = selection(), selection()
                    if rng.random() < proba_croisement:
                        enfant = croisement_ag(parent1, parent2, N, rng, limite)
                    else:
                        enfant = copie_ag(parent1)
                    if rng.random() < mutation:
                        for _ in range(rng.randint(1, 3)):
                            enfant = mutation_ag(enfant, N, rng, limite)

                cout = observer(enfant)
                cle = cle_ag(enfant, N)
                if not diversite or cle not in vus:  # Refuser les doublons dans la population.
                    nouvelle.append((enfant, cout))
                    vus.add(cle)

            population = nouvelle
            generations += 1

            # Suivi de la population environ toutes les 0,25 s (pour les graphiques de diversité)
            temps_suivi = time.perf_counter() - debut
            if temps_suivi - dernier_suivi >= 0.25 and temps_suivi <= budgets[-1]:
                cout_population = sum(c for _, c in population) / len(population)
                uniques = len({cle_ag(s, N) for s, _ in population}) / len(population)

                # Diversité des affectations et des arcs des tournées, par rapport au meilleur membre.
                def arcs(solution):
                    # ensemble des trajets (technicien, de, vers) + des reports
                    ensemble = set()
                    for t in N["techs"]:
                        route = [N["domicile"][t]] + solution[t] + [N["domicile"][t]]
                        ensemble.update((t, a, b) for a, b in zip(route, route[1:]))
                    ensemble.update(("report", m) for m in solution["reportees"])
                    return ensemble
                reference = arcs(min(population, key=lambda x: x[1])[0])
                ecarts = []
                for solution, _ in population:
                    a = arcs(solution)
                    # distance de Jaccard : 1 - (arcs communs / arcs au total)
                    ecarts.append(1 - len(a & reference) / max(1, len(a | reference)))
                suivi_population.append({"temps": temps_suivi, "generation": generations,
                    "cout_moyen": cout_population, "cout_min": min(c for _, c in population),
                    "meilleur": meilleur_cout, "fraction_unique": uniques,
                    "diversite_arcs": sum(ecarts) / len(ecarts), "taille": len(population)})
                dernier_suivi = temps_suivi

            # compteur de stagnation : remis à 0 dès que le meilleur s'améliore
            stagnation = 0 if meilleur_cout < ancien_record - 1e-9 else stagnation + 1

        # fin de l'exécution : on complète les budgets pas encore atteints
        temps_reel = time.perf_counter() - debut
        for budget in budgets:
            if couts[budget] is None:
                couts[budget] = meilleur_cout
        assert est_realisable(meilleure, N)
        resultats.append({
            "Essai": graine,
            **{f"Coût {b}": couts[b] for b in budgets},
            "Reports": len(meilleure["reportees"]),
            "Temps": temps_reel,
            "Générations": generations,
            "Population finale": len(population),
            "Historique": historique,
            "Suivi population": suivi_population
        })
        solutions.append(meilleure)
    return resultats, solutions