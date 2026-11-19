"""Recrée les statistiques et figures des deux apports, sans nouveaux calculs."""
# (Ce fichier s'appelait analyser.py dans le dossier des apports d'Axel. On l'a renommé
# pour ne pas le confondre avec code/analyser.py, qui analyse la campagne principale.)
# Depuis le dossier du notebook : python code/analyser_apports.py --resultats resultats/complements
# Sorties dans analyses/ : tableaux csv, synthese.json, N200_convergence et N50_renouvellement (png et svg).

import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.matplotlib'))
import argparse, json, csv, statistics, bisect


def stats(v):
    # petit résumé statistique d'une liste de coûts
    return dict(n=len(v), meilleur=min(v), moyenne=statistics.mean(v), ecart_type=statistics.stdev(v) if len(v) > 1 else 0, pire=max(v), mediane=statistics.median(v))


def lire(d):
    # tous les json d'un dossier, triés par graine
    return sorted([json.loads(p.read_text()) for p in d.glob('*.json')], key=lambda r: r['graine'])


def ecrire(p, rows):
    if not rows:
        return
    with p.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter=';')
        w.writeheader()
        w.writerows(rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--partiel', action='store_true')
    p.add_argument('--resultats', default='resultats/complements')
    p.add_argument('--sortie', default='analyses')
    p.add_argument('--sans-graphiques', action='store_true')
    a = p.parse_args()
    src = ROOT / a.resultats
    out = ROOT / a.sortie
    out.mkdir(parents=True, exist_ok=True)
    long = lire(src / 'long_terme_N200')
    rs = lire(src / 'recuit_N200')
    n50 = lire(src / 'renouvellement_N50')
    # --partiel permet d'analyser avant la fin de la campagne
    if not a.partiel:
        assert len(long) == 5 and len(rs) == 5 and len(n50) == 15, 'Attendre les 25 sorties'

    # Apport 2 (N50) : statistiques par politique d'immigration
    groupes = {n: [r for r in n50 if r['configuration'] == n] for n in ['0_0', '10_20', '20_40']}
    n50stats = []
    longstats = []
    ind = []
    compar = []
    for n, rr in groupes.items():
        if rr:
            v = [r['cout_final'] for r in rr]
            n50stats.append(dict(politique=n, **stats(v), generations_moyennes=statistics.mean(r['resultat']['Générations'] for r in rr), population_finale_moyenne=statistics.mean(r['resultat']['Population finale'] for r in rr)))
            for r in rr:
                ind.append(dict(experience='renouvellement_N50', configuration=n, graine=r['graine'], budget_s=20, cout=r['cout_final'], generations=r['resultat']['Générations'], temps_cpu_s=r['temps_cpu_s']))

    # comparaison graine par graine avec la politique d'origine 20/40
    base = {r['graine']: r for r in groupes['20_40']}
    for n in ['0_0', '10_20']:
        rr = [r for r in groupes[n] if r['graine'] in base]
        if rr:
            diffs = [r['cout_final'] - base[r['graine']]['cout_final'] for r in rr]
            compar.append(dict(politique=n, reference='20_40', n=len(diffs), ecart_moyen_cout=statistics.mean(diffs), meilleur_sur=sum(x < -1e-7 for x in diffs), egalite_sur=sum(abs(x) <= 1e-7 for x in diffs), moins_bon_sur=sum(x > 1e-7 for x in diffs)))

    # Apport 1 (N200) : coûts du génétique à chaque seuil de temps, et du recuit témoin
    for t in [60, 120, 180, 300, 400]:
        if long:
            longstats.append(dict(methode='AG_original', budget_s=t, **stats([r['couts_seuils'][str(t)] for r in long])))
    for t in [60, 120, 180]:
        if rs:
            longstats.append(dict(methode='Recuit', budget_s=t, **stats([r['couts_seuils'][str(t)] for r in rs])))
    for nom, rr in [('long_terme_N200', long), ('recuit_N200', rs)]:
        for r in rr:
            for t, c in r['couts_seuils'].items():
                ind.append(dict(experience=nom, configuration=r['configuration'], graine=r['graine'], budget_s=int(t), cout=c, generations=r['resultat'].get('Générations', ''), temps_cpu_s=r['temps_cpu_s']))
    for name, rows in [('N50_renouvellement', n50stats), ('N200_long_terme', longstats), ('essais_individuels', ind), ('N50_comparaison_graines', compar)]:
        ecrire(out / f'{name}.csv', rows)
    obj = dict(effectifs={'AG_N200': len(long), 'Recuit_N200': len(rs), 'renouvellement_N50': len(n50)}, N50=n50stats, N200=longstats, comparaisons_N50=compar)
    (out / 'synthese.json').write_text(json.dumps(obj, ensure_ascii=False, indent=2))
    for r in n50stats:
        print('N50', r['politique'], f"{r['moyenne']:.2f} ± {r['ecart_type']:.2f}", flush=True)

    # Graphiques
    if not a.sans_graphiques:
        import numpy as np
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        plt.rcParams.update({'font.family': 'Arial', 'font.size': 11, 'axes.titlesize': 13, 'axes.titleweight': 'bold', 'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True, 'grid.alpha': .2, 'svg.fonttype': 'none'})

        def save(fig, n):
            for ext in ['png', 'svg']:
                fig.savefig(out / f'{n}.{ext}', dpi=220, facecolor='white')
            plt.close(fig)

        if long:
            # coût moyen du génétique seconde par seconde (+- un écart-type) jusqu'à 400 s
            grid = np.arange(0, 401)
            Y = []
            for r in long:
                tr = r['resultat']['Historique']
                ts = [x[0] for x in tr]
                Y.append([tr[max(0, bisect.bisect_right(ts, float(t)) - 1)][1] for t in grid])
            Y = np.array(Y)
            m = Y.mean(axis=0)
            sd = Y.std(axis=0, ddof=1) if len(Y) > 1 else np.zeros_like(m)
            fig, ax = plt.subplots(figsize=(9, 3.6), layout='constrained')
            ax.step(grid, m, where='post', color='#28647D', lw=2, label='Génétique original : moyenne')
            ax.fill_between(grid, m - sd, m + sd, step='post', color='#28647D', alpha=.15, label='± un écart-type')
            ax.axvline(180, ls=':', color='#777777', lw=1)
            if rs:
                # ligne horizontale : coût moyen du recuit à 180 s
                ref = statistics.mean(r['couts_seuils']['180'] for r in rs)
                ax.plot([180, 400], [ref, ref], ls='--', color='#C57230', lw=1.5, label='Recuit : moyenne à 180 s')
            ax.set(xlim=(0, 400), xlabel='Temps de calcul (s)', ylabel='Meilleur coût pénalisé connu', title='N200 — prolongement du génétique jusqu’à 400 secondes')
            ax.set_xticks([0, 60, 120, 180, 300, 400])
            ax.legend(frameon=False, fontsize=9)
            save(fig, 'N200_convergence')

        if n50:
            # les 5 essais de chaque politique (points) avec moyenne et écart-type
            fig, ax = plt.subplots(figsize=(8.5, 3.5), layout='constrained')
            colors = ['#73828B', '#2E8594', '#C57230']
            for i, (n, col) in enumerate(zip(['0_0', '10_20', '20_40'], colors)):
                rr = groupes[n]
                if not rr:
                    continue
                v = [r['cout_final'] for r in rr]
                # petit décalage horizontal pour que les points ne se cachent pas
                xs = [i + (k - (len(v) - 1) / 2) * .045 for k in range(len(v))]
                ax.scatter(xs, v, color=col, s=38, alpha=.75, zorder=3)
                ax.errorbar(i, statistics.mean(v), yerr=statistics.stdev(v) if len(v) > 1 else 0, fmt='D', ms=7, lw=2, capsize=6, color=col, mec='white', zorder=4)
            ax.set_xticks([0, 1, 2], ['0 % / 0 %', '10 % / 20 %', '20 % / 40 %'])
            ax.set(xlabel='Immigration habituelle / après stagnation', ylabel='Coût final à 20 s', title='N50 — comparaison des trois politiques de renouvellement')
            fig.supxlabel('Points : cinq essais ; losange : moyenne ; barres : ± un écart-type', fontsize=9)
            save(fig, 'N50_renouvellement')
    print('Analyses enregistrées dans', out)


if __name__ == '__main__':
    main()