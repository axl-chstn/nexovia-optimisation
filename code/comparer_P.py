# Comparaison ajoutée après la soutenance : notre recuit (réchauffage depuis la meilleure
# solution) contre la version du cours (P essais indépendants depuis une solution aléatoire).
# Même budget (180 s), mêmes instances, mêmes graines pour toutes les variantes.
# À lancer depuis le dossier du notebook : python code/comparer_P.py
# Résultats : resultats/variante_P/comparaison_P.json

import json, os, sys, time
from multiprocessing import Pool
ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
sys.path.insert(0, ICI)
from recuit_P import *

BUDGET = 180
INSTANCES = ["N50", "N100", "N200"]
GRAINES = [1, 2, 3, 4, 5]
# "actuel" = notre recuit ; P1, P3, P5 = version du cours avec 1, 3 ou 5 essais
VARIANTES = ["actuel", "P1", "P3", "P5"]
SORTIE = os.path.join(RACINE, "resultats", "variante_P", "comparaison_P.json")


def charger(nom):
    N = lire_instance(os.path.join(RACINE, "donnees", nom))
    preparer_instance(N)
    return N, json.load(open(os.path.join(RACINE, "S0_communs.json")))[nom]


def lancer(tache):
    # un essai = une instance, une variante, une graine
    nom, variante, graine = tache
    N, S0 = charger(nom)
    if variante == "actuel":
        S, c, inf = recuit_simule(S0, N, temps_max=BUDGET, graine=graine)
        detail = {"rechauffages": inf["rechauffages"], "iterations": inf["iterations"]}
    else:
        # "P3" -> P = 3
        S, c, inf = recuit_essais_P(S0, N, temps_max=BUDGET, P=int(variante[1:]), graine=graine)
        detail = {"essais": inf["essais"]}
    # on vérifie quand même que la solution est bonne et que le coût est juste
    assert est_realisable(S, N) and abs(f(S, N) - c) < 1e-6
    return {"instance": nom, "variante": variante, "graine": graine, "S0": round(f(S0, N), 2),
            "cout": round(c, 2), **detail}


if __name__ == "__main__":
    taches = [(nom, v, g) for g in GRAINES for nom in INSTANCES for v in VARIANTES]
    resultats = []
    debut = time.time()
    os.makedirs(os.path.dirname(SORTIE), exist_ok=True)
    with Pool(4) as p:
        for r in p.imap_unordered(lancer, taches):
            resultats.append(r)
            # on réécrit le fichier à chaque essai, comme ça rien n'est perdu si on arrête avant la fin
            json.dump(resultats, open(SORTIE, "w"), indent=1)
            print(f"[{len(resultats)}/{len(taches)}] {time.time()-debut:.0f}s", r["instance"], r["variante"], r["graine"], r["cout"], flush=True)