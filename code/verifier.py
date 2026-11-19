"""Contrôle des sorties livrées, puis essai court des algorithmes finaux."""
# Depuis le dossier du notebook : python code/verifier.py
# 1) relit les 45 résultats du génétique et les 9 archives PLS et recalcule leurs coûts
#    avec verification_csv.py ;
# 2) lance des essais très courts du génétique et de la PLS pour vérifier que tout marche.

import json, math, functools
from pathlib import Path
from collections import Counter
from lancer import ROOT, NOMS, charger
from genetique import algorithme_genetique
from multiobjectif import pls, domine
import verification_csv as controle
# Les CSV restent en mémoire ; la logique du contrôleur indépendant est inchangée.
controle.lignes = functools.lru_cache(maxsize=None)(controle.lignes)


def main():
    ag = points = 0
    for n in NOMS:
        N, S0 = charger(n)
        # résultats du génétique : coût recalculé = coût enregistré, et pas pire que S0
        for p in (ROOT / 'resultats/genetique').glob(f'{n}_graine_*.json'):
            r = json.loads(p.read_text())
            val = controle.verifier(r['solution'], n)
            assert math.isclose(val, r['resultat']['Coût 180'], abs_tol=1e-7), p
            assert val <= r['reference'] + 1e-7, p
            ag += 1
        # archive PLS : aucun point dominé, pas de doublon, coûts justes
        r = json.loads((ROOT / 'resultats/multiobjectif' / f'PLS_{n}.json').read_text())
        front = r['front']
        assert all(not domine((b['D'], b['R']), (a['D'], a['R'])) for a in front for b in front)
        assert len({(a['D'], a['R']) for a in front}) == len(front)
        for a in front:
            val = controle.verifier(a['solution'], n)
            assert math.isclose(val - N['penalite'] * a['R'], a['D'], abs_tol=1e-7), (n, a['D'], a['R'])
            assert len(a['solution']['reportees']) == a['R']
            points += 1
    assert ag == 45
    print(f'{ag} sorties AG et {points} points PLS : coûts, faisabilité et non-dominance vérifiés.', flush=True)

    # essais courts : le génétique ne doit pas modifier S0, et le coût à 0,1 s
    # ne doit pas être pire que celui à 0,05 s
    for n in ['N0', 'N50', 'N200']:
        N, S = charger(n)
        avant = json.dumps(S, sort_keys=True)
        rr, ss = algorithme_genetique(S, N, budgets=(.05, .1), graines=(1,))
        assert json.dumps(S, sort_keys=True) == avant
        assert math.isclose(controle.verifier(ss[0], n), rr[0]['Coût 0.1'], abs_tol=1e-7)
        assert rr[0]['Coût 0.05'] >= rr[0]['Coût 0.1'] - 1e-7
    # la PLS doit retrouver les 8 points du front de N0 en 1 s
    N, S = charger('N0', 'historique-pls')
    r = pls(S, N, budget=1)
    assert len(r['front']) == 8
    print('Essais courts AG (N0, N50, N200) et PLS (N0) : OK.')


if __name__ == '__main__':
    main()