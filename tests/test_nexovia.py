"""Contrats de faisabilité et cohérence des résultats, sans campagne longue."""
import copy
import functools
import json
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
from lancer import charger, NOMS
from socle import f, est_realisable
from genetique_renouvellement import algorithme_genetique
from multiobjectif import domine
from recuit import recuit_simule
from recuit_P import recuit_essais_P
import verification_csv as controle
controle.lignes = functools.lru_cache(maxsize=None)(controle.lignes)

class NexoviaTests(unittest.TestCase):
    def test_departs_communs(self):
        for nom in NOMS:
            with self.subTest(instance=nom):
                N, S = charger(nom)
                self.assertTrue(est_realisable(S, N))
                self.assertAlmostEqual(f(S, N), controle.verifier(S, nom), places=7)

    def test_departs_exploratoire_et_commun_distincts(self):
        N, S = charger("N50", "exploratoire")
        self.assertAlmostEqual(f(S, N), 614.036, places=3)
        N, S = charger("N50")
        self.assertAlmostEqual(f(S, N), 687.919, places=3)

    def test_renouvellement_preserve_depart_et_faisabilite(self):
        N, S = charger("N50", "exploratoire")
        avant = copy.deepcopy(S)
        for base, renfort in [(0, 0), (.1, .2), (.2, .4)]:
            with self.subTest(base=base):
                rr, ss = algorithme_genetique(S, N, budgets=(.1,), graines=(1,),
                    taux_immigration=base, taux_stagnation=renfort)
                self.assertEqual(S, avant)
                val = controle.verifier(ss[0], "N50")
                self.assertLessEqual(val, f(S, N) + 1e-7)
                self.assertAlmostEqual(val, rr[0]["Coût 0.1"], places=7)

    def test_recuit_et_variante_P(self):
        N, S = charger("N0")
        avant = copy.deepcopy(S)
        for solveur, options in [(recuit_simule, {}),
                                 (recuit_essais_P, {"P": 2, "Q": 100, "nb_pas": 8})]:
            avec, cout, infos = solveur(S, N, temps_max=.2, graine=1, **options)
            self.assertIsNotNone(avec)
            self.assertAlmostEqual(controle.verifier(avec, "N0"), cout, places=7)
            self.assertEqual(S, avant)

    def test_dominance(self):
        self.assertTrue(domine((100, 2), (130, 2)))
        self.assertFalse(domine((100, 5), (130, 2)))
        self.assertFalse(domine((130, 2), (100, 5)))
        self.assertFalse(domine((100, 2), (100, 2)))

    def test_25_sorties_apports(self):
        dossiers = {"long_terme_N200": 5, "recuit_N200": 5, "renouvellement_N50": 15}
        for dossier, nombre in dossiers.items():
            fichiers = sorted((ROOT / "resultats_apports" / dossier).glob("*.json"))
            self.assertEqual(len(fichiers), nombre)
            for p in fichiers:
                with self.subTest(fichier=p.name):
                    r = json.loads(p.read_text())
                    cout = controle.verifier(r["solution_finale"], r["instance"])
                    self.assertAlmostEqual(cout, r["cout_final"], places=7)
                    valeurs = [v for t, v in sorted(r["couts_seuils"].items(), key=lambda x: int(x[0]))]
                    self.assertTrue(all(b <= a + 1e-7 for a, b in zip(valeurs, valeurs[1:])))
                    self.assertAlmostEqual(cout, valeurs[-1], places=7)
                    ref = controle.verifier(r["solution_initiale"], r["instance"])
                    self.assertAlmostEqual(ref, r["reference"], places=7)

if __name__ == "__main__":
    unittest.main()
