"""Deux apports séparés : AG original N200 à 400 s ; immigration sur N50 à 20 s.
Aucun calcul au chargement. Les sorties existantes ne sont jamais écrasées.
"""
# Expériences ajoutées après la soutenance pour le génétique :
#  - apport 1 : le génétique final sur N200 prolongé jusqu'à 400 s (+ 5 recuits de 180 s
#    sur la même machine, comme témoin) ;
#  - apport 2 : trois politiques d'immigration sur N50 (0/0, 10/20 et 20/40 %), 20 s.
# Lancement complet (depuis le dossier du notebook) : python code/experiences.py --sortie nouveaux_resultats/complements
# Pour une seule étude, utiliser --etude temps-long, renouvellement ou temoin.

import os
# un seul fil de calcul pour les bibliothèques numériques
for name in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS']:
    os.environ[name] = '1'
import argparse, json, time, datetime, sys, platform, hashlib, multiprocessing, zipfile, traceback, bisect
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from socle import lire_instance, preparer_instance, est_realisable, f, heuristique_gloutonne
ROOT = Path(__file__).resolve().parents[1]
# politiques testées : (nom, immigration habituelle, immigration après stagnation)
POLITIQUES = [('0_0', 0., 0.), ('10_20', .1, .2), ('20_40', .2, .4)]
BARRIER = None


def initialiser(barrier):
    # la barrière sert à démarrer les 3 essais N50 d'une même graine en même temps
    global BARRIER
    BARRIER = barrier


def sauvegarder(p, obj):
    # écrit d'abord dans un fichier .tmp puis le renomme : pas de fichier à moitié écrit
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix('.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2))
    tmp.replace(p)


def modele(nom):
    # données de l'instance + solution de départ propre à chaque apport
    N = lire_instance(str(ROOT / 'donnees' / nom))
    preparer_instance(N)
    if nom == 'N200':
        # N200 : le S0 commun du groupe, le même que dans la campagne principale
        S = json.loads((ROOT / 'donnees' / 'S0_communs.json').read_text())['N200']
    else:
        # N50 : départ historique figé, indépendant des départages de pandas.
        S = json.loads((ROOT / 'donnees' / 'S0_exploratoires.json').read_text())[nom]
    assert est_realisable(S, N)
    return N, S


def essai(tache):
    # Un essai : selon la phase, génétique long sur N200, recuit témoin sur N200,
    # ou génétique avec une politique d'immigration sur N50.
    phase, configuration, seed, budget, base, renfort, sortie = tache
    nom = 'N50' if phase == 'renouvellement' else 'N200'
    N, S0 = modele(nom)
    avant = json.dumps(S0, sort_keys=True)
    if BARRIER is not None:
        BARRIER.wait(timeout=120)
    date = datetime.datetime.now(datetime.timezone.utc).isoformat()
    debut = time.perf_counter()
    cpu = time.process_time()

    if phase == 'long_terme':
        # Import du fichier final inchangé. Aucun paramètre de renouvellement ajouté.
        from genetique import algorithme_genetique
        seuils = [60, 120, 180, 300, 400]
        rr, ss = algorithme_genetique(S0, N, budgets=tuple(seuils), graines=(seed,))
        r = rr[0]
        S = ss[0]
        couts = {str(t): r[f'Coût {t}'] for t in seuils}
    elif phase == 'recuit':
        # le recuit de la partie 2 (code/recuit.py) avec le réglage du rapport,
        # pour situer le génétique sur la même machine
        from recuit import recuit_simule
        S, c, info = recuit_simule(S0, N, temps_max=180, graine=seed, tau0=.1, alpha=.99, k_palier=20)
        r = {'cout': c, 'infos': info}
        seuils = [60, 120, 180]
        trace = info['historique']
        ts = [x[0] for x in trace]
        # meilleur coût connu à 60, 120 et 180 s, lu dans l'historique
        couts = {str(t): trace[max(0, bisect.bisect_right(ts, t) - 1)][1] for t in seuils}
    else:
        from genetique_renouvellement import algorithme_genetique
        seuils = [20]
        rr, ss = algorithme_genetique(S0, N, budgets=(20,), graines=(seed,), taux_immigration=base, taux_stagnation=renfort)
        r = rr[0]
        S = ss[0]
        couts = {'20': r['Coût 20']}

    cpu = time.process_time() - cpu
    duree = time.perf_counter() - debut
    # S0 ne doit pas avoir été modifié, et la solution finale doit être réalisable
    assert json.dumps(S0, sort_keys=True) == avant and est_realisable(S, N)
    obj = dict(phase=phase, configuration=configuration, instance=nom, graine=seed, budget_s=budget,
               solution_initiale=S0, reference=f(S0, N), resultat=r, solution_finale=S, couts_seuils=couts,
               cout_final=f(S, N), reports_finaux=len(S['reportees']), distance_finale=f(S, N) - N['penalite'] * len(S['reportees']),
               temps_mural_s=duree, temps_cpu_s=cpu, date_debut_utc=date,
               parametres={'population': 20, 'croisement': .8, 'mutation_base': .25, 'elites': 2, 'seuil_stagnation_generations': 10, 'mutation_stagnation_min': .7, 'immigration_habituelle': .2 if phase == 'long_terme' else base, 'immigration_stagnation': .4 if phase == 'long_terme' else renfort} if phase != 'recuit' else {'tau0': .1, 'alpha': .99, 'k_palier': 20},
               code='genetique.py final inchangé' if phase == 'long_terme' else 'recuit.py final inchangé' if phase == 'recuit' else 'genetique_renouvellement.py ; seuls les taux deviennent paramétrables')
    destination = Path(sortie) / f'{configuration}_graine_{seed}.json'
    sauvegarder(destination, obj)
    return phase, configuration, seed, couts, duree, cpu


def collecter(futures, out, compte, total, debut):
    # affiche l'avancement à chaque essai terminé (et l'écrit dans AVANCEMENT.txt)
    for fut in as_completed(futures):
        phase, c, g, cc, t, cpu = fut.result()
        compte += 1
        msg = f'{compte}/{total} : {phase}, {c}, graine {g}, coûts {cc}, CPU/mural {cpu/t:.3f}. Durée totale {(time.perf_counter()-debut)/60:.1f} min.'
        print(msg, flush=True)
        (ROOT / 'AVANCEMENT.txt').write_text(msg + '\n')
    return compte


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sortie', default='nouveaux_resultats/complements')
    p.add_argument('--etude', choices=['toutes', 'temps-long', 'renouvellement', 'temoin'], default='toutes')
    p.add_argument('--graines', type=int, nargs='+', default=[1, 2, 3, 4, 5])
    p.add_argument('--processus', type=int, default=4, help='Nombre de processus pour N200 ; N50 utilise trois processus synchronisés.')
    p.add_argument('--plan', action='store_true', help='Afficher les essais prévus sans lancer de calcul.')
    a = p.parse_args()
    if a.processus < 1 or len(set(a.graines)) != len(a.graines):
        p.error('Utiliser un nombre positif de processus et des graines distinctes.')
    n50 = a.etude in ['toutes', 'renouvellement']
    long = a.etude in ['toutes', 'temps-long']
    temoin = a.etude in ['toutes', 'temoin']
    total = len(a.graines) * (3 * n50 + long + temoin)
    if a.plan:
        print(json.dumps({'etude': a.etude, 'graines': a.graines,
            'renouvellement_N50': 3 * len(a.graines) if n50 else 0,
            'AG_N200_400s': len(a.graines) if long else 0,
            'recuit_N200_180s': len(a.graines) if temoin else 0, 'total': total}, ensure_ascii=False, indent=2))
        return
    out = ROOT / a.sortie
    # on refuse d'écrire dans un dossier qui contient déjà des résultats
    if list(out.glob('*/*_graine_*.json')):
        raise RuntimeError('Des sorties existent. Choisir un nouveau dossier --sortie.')
    out.mkdir(parents=True, exist_ok=True)

    # on note le protocole (machine, versions, empreintes des fichiers) pour pouvoir le retrouver
    empreintes = {str(q.relative_to(ROOT)): hashlib.sha256(q.read_bytes()).hexdigest() for q in list((ROOT / 'code').glob('*.py')) + list((ROOT / 'donnees').rglob('*.csv')) + list((ROOT / 'donnees').glob('S0_*.json'))}
    protocole = dict(debut_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), python=sys.version, plateforme=platform.platform(), cpu_logiques=os.cpu_count(), empreintes=empreintes,
                     apport_1={'instance': 'N200', 'budget_s': 400, 'seuils_s': [60, 120, 180, 300, 400], 'graines': a.graines, 'algorithme': 'Code final original inchangé ; immigration 20/40.'},
                     temoin={'instance': 'N200', 'methode': 'Recuit original', 'budget_s': 180, 'graines': a.graines, 'note': 'Témoin actuel sur la même machine. AG 400 s / recuit 180 s est une comparaison à budgets différents.'},
                     apport_2={'instance': 'N50', 'budget_s': 20, 'graines': a.graines, 'politiques': [[0, 0], [10, 20], [20, 40]], 'depart': 'Glouton historique sauvegardé, comme l’étude exploratoire de diversification. Différent du S0 harmonisé de la campagne principale.'},
                     execution='N50 : trois processus synchronisés par graine, cinq cohortes de 20 s. Ensuite N200 : au plus quatre processus, cinq AG 400 s puis cinq recuits 180 s dans la file. Aucun calcul N50 en concurrence avec N200.',
                     limites='Une seule instance par apport, cinq graines ; temps muraux et CPU enregistrés. Les deux expériences ne sont pas fusionnées et leurs coûts ne se comparent pas entre instances.')
    protocole.update(etude=a.etude, processus_N200=a.processus, graines=a.graines)
    for cle, active in [('apport_1', long), ('temoin', temoin), ('apport_2', n50)]:
        if not active:
            protocole.pop(cle)
    protocole['execution'] = f'N50 : trois politiques synchronisées par graine. N200 : au plus {a.processus} processus. Phases exécutées séparément.'
    sauvegarder(out / 'protocole.json', protocole)
    debut = time.perf_counter()
    compte = 0

    # Apport 2 (N50) : pour chaque graine, les 3 politiques tournent en même temps
    ctx = multiprocessing.get_context('spawn')
    if n50:
        barrier = ctx.Barrier(3)
        with ProcessPoolExecutor(max_workers=3, mp_context=ctx, initializer=initialiser, initargs=(barrier,)) as pool:
            for g in a.graines:
                print(f'N50 : début cohorte graine {g}, trois politiques de 20 s.', flush=True)
                futures = [pool.submit(essai, ('renouvellement', c, g, 20, b, r, str(out / 'renouvellement_N50'))) for c, b, r in POLITIQUES]
                compte = collecter(futures, out, compte, total, debut)

    # Apport 1 (N200) : 5 génétiques de 400 s puis 5 recuits de 180 s
    if long or temoin:
        with ProcessPoolExecutor(max_workers=a.processus, mp_context=ctx) as pool:
            taches = [('long_terme', 'AG_original', g, 400, None, None, str(out / 'long_terme_N200')) for g in a.graines] if long else []
            if temoin:
                taches += [('recuit', 'RS_180', g, 180, None, None, str(out / 'recuit_N200')) for g in a.graines]
            print('N200 : début des essais longs avec le génétique original et du témoin recuit.', flush=True)
            compte = collecter([pool.submit(essai, t) for t in taches], out, compte, total, debut)

    protocole['fin_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    protocole['duree_campagne_s'] = time.perf_counter() - debut
    sauvegarder(out / 'protocole.json', protocole)
    print('CAMPAGNE TERMINÉE', flush=True)
    (ROOT / 'AVANCEMENT.txt').write_text(f'Terminé : {compte}/{total}, durée {(time.perf_counter()-debut)/60:.1f} min.\n')


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        # en cas d'erreur, on garde le message dans ERREUR.txt
        (ROOT / 'ERREUR.txt').write_text(traceback.format_exc())
        raise