# Lance toutes les expériences du recuit et de l'epsilon-contrainte présentées dans le rapport.
# À lancer depuis le dossier du notebook :
#   python code/campagne_recuit.py sensi1                 -> analyse de sensibilité, étape 1 (30 s)
#   python code/campagne_recuit.py sensi2 '<combinaisons>'  -> étape 2 (60 s), combinaisons en json
#   python code/campagne_recuit.py mono '{"tau0": 0.1, "alpha": 0.99, "k_palier": 20}'
#   python code/campagne_recuit.py eps 0.1                 -> epsilon-contrainte (180 s par essai)
# Les résultats sont écrits dans resultats/ au format json (lus ensuite par analyse_recuit.py).

import sys, json, os, time
from multiprocessing import Pool
from epsilon_contrainte import *

INSTANCES = ["N0", "N10", "N20", "N30", "N50", "N80", "N100", "N150", "N200"]
GRAINES = [1, 2, 3, 4, 5]
BUDGETS = [60, 120, 180]
# réglage de départ, avant l'analyse de sensibilité
REGLAGE_INITIAL = {"tau0": 0.5, "alpha": 0.95, "k_palier": 5}
os.makedirs("resultats", exist_ok=True)

# on garde les instances déjà lues pour ne pas relire les csv à chaque essai
_cache = {}


def instance(nom):
    if nom not in _cache:
        N = lire_instance(os.path.join("donnees", nom))
        preparer_instance(N)
        _cache[nom] = (N, json.load(open("S0_communs.json"))[nom])
    return _cache[nom]


def tache_mono(a):
    # Un essai de 180 s du recuit sur une instance et une graine
    nom, g, reglage = a
    N, S0 = instance(nom)
    S, c, info = recuit_simule(S0, N, temps_max=max(BUDGETS), graine=g, garder_trace=True, **reglage)
    assert est_realisable(S, N)
    h = info["historique"]
    lignes = []
    # une seule exécution de 180 s donne aussi les résultats à 60 et 120 s :
    # on regarde la meilleure valeur connue à chaque instant dans l'historique
    for B in BUDGETS:
        pts = [x for x in h if x[0] <= B]
        lignes.append({"budget": B, "f": pts[-1][1], "temps_meilleur": pts[-1][0]})
    D, R = objectifs(S, N)
    tr = info["trace"]
    return {"instance": nom, "graine": g, "reglage": reglage, "lignes": lignes, "f": c, "D": D, "R": R,
            "iterations": info["iterations"], "acceptes": info["acceptes"], "T0": info["T0"],
            "palier": info["palier"], "rechauffages": info["rechauffages"], "temps_meilleur": info["temps_meilleur"],
            # on n'enregistre qu'environ 400 points de la trace pour limiter la taille du fichier
            "historique": h, "trace": tr[::max(1, len(tr) // 400)], "solution": S}


# Étape 1 de la sensibilité : on change un seul paramètre à la fois
SENSI_INST = ["N20", "N50", "N100", "N200"]
SENSI1 = [("base", {})] + [("tau0", {"tau0": v}) for v in (0.1, 0.9)] + \
         [("alpha", {"alpha": v}) for v in (0.80, 0.90, 0.99)] + [("k_palier", {"k_palier": v}) for v in (1, 20)]


def tache_sensi(a):
    # Un essai de sensibilité : réglage de base modifié par cfg
    nom, nomcfg, cfg, g, budget, base = a
    N, S0 = instance(nom)
    p = dict(base)
    p.update(cfg)
    S, c, info = recuit_simule(S0, N, temps_max=budget, graine=g, **p)
    return {"instance": nom, "parametre": nomcfg, **p, "graine": g, "budget": budget, "f": c, "T0": info["T0"],
            "iterations": info["iterations"], "rechauffages": info["rechauffages"],
            "temps_meilleur": info["temps_meilleur"], "historique": info["historique"]}


def tache_eps(a):
    # Un essai complet de l'epsilon-contrainte : 180 s partagées entre les valeurs de epsilon
    nom, g, tau0 = a
    N, S0 = instance(nom)
    grille = grille_epsilon(N)
    t = time.perf_counter()
    res, front = epsilon_contrainte(S0, N, epsilons=grille, temps_par_epsilon=180 / len(grille), graine=g, tau0=tau0)
    return {"instance": nom, "graine": g, "temps_total": time.perf_counter() - t, "bruts": res,
            "front": [{"D": p[0], "R": p[1], "solution": p[2]} for p in front]}


def lancer(fonction, taches, fichier):
    # On lance tous les essais et on sauvegarde les résultats à la fin
    out = []
    with Pool(4) as pool:
        for r in pool.imap_unordered(fonction, taches):
            out.append(r)
            print(fichier, len(out), "/", len(taches), r["instance"], flush=True)
    json.dump(out, open(os.path.join("resultats", fichier), "w"))


if __name__ == "__main__":
    quoi = sys.argv[1]
    # on commence par les grosses instances
    ordre = lambda nom: -INSTANCES.index(nom)
    if quoi == "sensi1":
        lancer(tache_sensi, [(i, n, c, g, 30, REGLAGE_INITIAL) for i in SENSI_INST for n, c in SENSI1 for g in GRAINES], "sensi_etape1.json")
    elif quoi == "sensi2":
        combos = json.loads(sys.argv[2])     # {"nom de la combinaison": {"tau0": ..., ...}, ...}
        lancer(tache_sensi, [(i, n, c, g, 60, REGLAGE_INITIAL) for i in ["N50", "N100", "N200"] for n, c in combos.items() for g in GRAINES], "sensi_etape2.json")
    elif quoi == "mono":
        reglage = json.loads(sys.argv[2])
        lancer(tache_mono, sorted([(i, g, reglage) for i in INSTANCES for g in GRAINES], key=lambda x: ordre(x[0])), "mono.json")
    elif quoi == "eps":
        tau0 = float(sys.argv[2])
        lancer(tache_eps, sorted([(i, g, tau0) for i in INSTANCES for g in GRAINES], key=lambda x: ordre(x[0])), "eps.json")