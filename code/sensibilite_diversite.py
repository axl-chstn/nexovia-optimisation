"""Plans de sensibilité et de diversité du génétique.
Le départ historique de N50 est conservé dans donnees/S0_exploratoires.json. Ces essais ne doivent pas être mélangés à la campagne principale.
"""
# Trois plans d'expériences pour le génétique (depuis le dossier du notebook) :
#   python code/sensibilite_diversite.py sensibilite    -> un paramètre à la fois (30 s)
#   python code/sensibilite_diversite.py combinaisons   -> quelques combinaisons (30 s)
#   python code/sensibilite_diversite.py diversite      -> test d'ablation avec/sans diversité (20 s)
# Pour un essai rapide : ajouter --instances N50 --graines 1 --secondes 1

import argparse, json, time
from pathlib import Path
from lancer import charger, ROOT
from genetique import algorithme_genetique
from socle import f

# réglage final de référence
BASE = dict(taille_population=20, proba_croisement=.8, proba_mutation=.25)


def plans(phase):
    # Renvoie la liste des réglages à tester : (nom, paramètres, diversité activée ou non)
    if phase == 'diversite':
        return [('sans', BASE.copy(), False), ('avec', BASE.copy(), True)]
    if phase == 'combinaisons':
        return [('reference', BASE.copy(), True)] + [(f'P{n}_pc1_pm01', dict(taille_population=n, proba_croisement=1., proba_mutation=.1), True) for n in [15, 20, 30]]
    # phase 'sensibilite' : on change une seule valeur à la fois par rapport à BASE
    result = [('reference', BASE.copy(), True)]
    valeurs = {'taille_population': [5, 10, 40, 80], 'proba_croisement': [0., .5, 1.], 'proba_mutation': [0., .1, .5, 1.]}
    for param, vals in valeurs.items():
        for v in vals:
            config = BASE.copy()
            config[param] = v
            result.append((f'{param}_{v}', config, True))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase', choices=['sensibilite', 'combinaisons', 'diversite'])
    p.add_argument('--instances', nargs='+', choices=['N20', 'N50', 'N100', 'N200'])
    p.add_argument('--graines', nargs='+', type=int, default=[1, 2, 3, 4, 5])
    p.add_argument('--secondes', type=float)
    p.add_argument('--sortie', default='nouveaux_essais_exploratoires')
    a = p.parse_args()
    # budgets d'origine : 20 s pour la diversité, 30 s pour le reste
    budget = a.secondes if a.secondes is not None else (20 if a.phase == 'diversite' else 30)
    if budget <= 0:
        p.error('Le budget doit être positif')
    noms = a.instances or (['N50'] if a.phase == 'diversite' else ['N50', 'N200'])
    out = ROOT / a.sortie
    out.mkdir(parents=True, exist_ok=True)

    for nom in noms:
        N, S0 = charger(nom, 'exploratoire')
        for label, config, active in plans(a.phase):
            for seed in a.graines:
                print(a.phase, nom, label, 'graine', seed, flush=True)
                rr, ss = algorithme_genetique(S0, N, **config, budgets=(budget,), graines=(seed,), diversite=active)
                obj = {'phase': a.phase, 'nom': nom, 'reglage': label, 'graine': seed, 'budget': budget, 'parametres': config, 'diversite': active, 'reference': f(S0, N), 'solution_initiale': S0, 'resultat': rr[0], 'solution': ss[0]}
                # un fichier par essai
                dest = out / f'{a.phase}_{nom}_{label}_{seed}_{time.time_ns()}.json'
                dest.write_text(json.dumps(obj, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()