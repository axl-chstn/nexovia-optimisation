"""Lanceur de compilation. Les algorithmes finaux importés restent inchangés."""
# Lance le génétique ou la PLS sur une ou plusieurs instances et enregistre le résultat en json.
# Exemples (depuis le dossier du notebook) :
#   python code/lancer.py genetique --instances N0 --secondes 1 --graines 1
#   python code/lancer.py pls --instances N50 --secondes 180
# Les nouveaux résultats vont dans nouveaux_resultats/ (les anciens ne sont jamais écrasés).

import argparse, json, time
from pathlib import Path
from socle import lire_instance, preparer_instance, est_realisable, f, heuristique_gloutonne
from genetique import algorithme_genetique
from multiobjectif import pls

# ROOT = dossier du notebook (le dossier au-dessus de code/)
ROOT = Path(__file__).resolve().parent.parent
NOMS = ['N0', 'N10', 'N20', 'N30', 'N50', 'N80', 'N100', 'N150', 'N200']


def charger(nom, depart='commun'):
    # Lit l'instance et choisit la solution de départ :
    #  - 'commun' : le S0 commun du groupe (S0_communs.json)
    #  - 'historique-pls' : le départ utilisé pour les archives PLS du rapport
    #  - 'exploratoire' : départ historique N50 sauvegardé ; glouton recalculé ailleurs
    N = lire_instance(str(ROOT / 'donnees' / nom))
    preparer_instance(N)
    if depart == 'historique-pls':
        S0 = json.loads((ROOT / 'resultats/multiobjectif' / f'PLS_{nom}.json').read_text())['solution_initiale']
    elif depart == 'exploratoire':
        historiques = json.loads((ROOT / 'donnees' / 'S0_exploratoires.json').read_text())
        S0 = historiques[nom] if nom in historiques else heuristique_gloutonne(N)
    else:
        S0 = json.loads((ROOT / 'donnees' / 'S0_communs.json').read_text())[nom]
    if not est_realisable(S0, N):
        raise ValueError('S0 non réalisable')
    return N, S0


def main():
    # lecture des options de la ligne de commande
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('methode', choices=['verifier', 'genetique', 'pls'])
    p.add_argument('--instances', nargs='+', choices=NOMS, default=['N0'])
    p.add_argument('--secondes', type=float, default=180)
    p.add_argument('--graines', nargs='+', type=int, default=[1, 2, 3, 4, 5])
    p.add_argument('--sortie', default='nouveaux_resultats')
    p.add_argument('--depart', choices=['commun', 'historique-pls'], default='commun')
    a = p.parse_args()
    if a.secondes <= 0:
        p.error('--secondes doit être positif')
    out = ROOT / a.sortie

    for nom in a.instances:
        N, S0 = charger(nom, a.depart)
        print(nom, 'S0 =', round(f(S0, N), 3), flush=True)
        # "verifier" : on contrôle seulement que S0 se charge et est réalisable
        if a.methode == 'verifier':
            continue
        if a.methode == 'genetique':
            # on relève aussi les coûts à 60 et 120 s s'ils sont avant la fin du budget
            budgets = tuple(b for b in (60, 120) if b < a.secondes) + (a.secondes,)
            rr, ss = algorithme_genetique(S0, N, budgets=budgets, graines=tuple(a.graines))
            res = {'instance': nom, 'methode': 'AG', 'solution_initiale': S0, 'reference': f(S0, N), 'resultats': rr, 'solutions': ss}
        else:
            res = {'instance': nom, 'solution_initiale': S0, 'reference': f(S0, N), **pls(S0, N, budget=a.secondes)}
        out.mkdir(parents=True, exist_ok=True)
        # nom de fichier horodaté pour ne rien écraser
        path = out / f'{a.methode}_{nom}_{time.time_ns()}.json'
        path.write_text(json.dumps(res, ensure_ascii=False, indent=2))
        print('Sauvegardé :', path, flush=True)


if __name__ == '__main__':
    main()