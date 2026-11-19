# Résolution exacte de N0 par énumération complète (possible car N0 n'a que 8 interventions).
# On obtient le vrai front de Pareto (D, R) et l'optimum de f, pour vérifier nos méthodes.
# Principe :
#  1) pour chaque technicien et chaque sous-ensemble d'interventions, on teste tous les
#     ordres de passage et on garde la tournée réalisable la plus courte ;
#  2) on essaie toutes les affectations des 8 interventions (3 techniciens + reportée,
#     donc 4^8 = 65 536 cas) en réutilisant les tournées de l'étape 1.
# À lancer depuis le dossier du notebook : python code/exact_N0.py

import itertools, json
from pathlib import Path
Path("resultats").mkdir(exist_ok=True)
from socle import lire_instance, preparer_instance, verifier_tournee, distance_tournee

N = lire_instance("donnees/N0")
preparer_instance(N)
jobs, techs = N["interventions"]["intervention"].tolist(), N["techs"]

# étape 1 : meilleure tournée de chaque technicien pour chaque sous-ensemble
meilleure = {}
for t in techs:
    for r in range(len(jobs) + 1):
        for sous_ensemble in itertools.combinations(jobs, r):
            best = None
            for ordre in itertools.permutations(sous_ensemble):
                S = {t: list(ordre)}
                if verifier_tournee(S, N, t):
                    d = distance_tournee(N, t, list(ordre))
                    if best is None or d < best:
                        best = d
            # si aucun ordre n'est réalisable, ce sous-ensemble est impossible pour t
            if best is not None:
                meilleure[(t, frozenset(sous_ensemble))] = best

# étape 2 : toutes les affectations. affectation[i] = numéro du technicien de la mission i,
# et la valeur len(techs) veut dire "reportée"
min_D = {}     # pour chaque nombre de reports R, la plus petite distance trouvée
for affectation in itertools.product(range(len(techs) + 1), repeat=len(jobs)):
    D, ok = 0.0, True
    for k, t in enumerate(techs):
        v = meilleure.get((t, frozenset(j for j, a in zip(jobs, affectation) if a == k)))
        if v is None:
            ok = False
            break
        D += v
    if ok:
        R = sum(1 for a in affectation if a == len(techs))
        if R not in min_D or D < min_D[R]:
            min_D[R] = D

# on ne garde que les points non dominés : quand R augmente, D doit baisser strictement
front, D_prec = {}, float("inf")
for R in sorted(min_D):
    if min_D[R] < D_prec - 1e-9:
        front[R] = round(min_D[R], 3)
        D_prec = min_D[R]
print("front exact :", front)
print("optimum f = D + c.R :", round(min(D + N["penalite"] * R for R, D in min_D.items()), 3))
json.dump({"front": front}, open("resultats/N0_exact.json", "w"), indent=1)