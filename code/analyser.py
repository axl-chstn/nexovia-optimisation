"""Analyse des résultats sauvegardés, sans relancer les algorithmes.
Lanceur regroupé pour la compilation : statistiques AG, convergence, comparaison
PLS/epsilon et sensibilité. Les résultats livrés sont toujours lus sans mutation.
"""
# Refait les tableaux et figures du génétique et de la comparaison PLS / epsilon
# à partir des fichiers de resultats/. Depuis le dossier du notebook :
#   python code/analyser.py
# Sorties dans analyses_regenerees/ (convergence_AG.png, synthese_AG.csv, ...).

import argparse, json, csv, statistics
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
NOMS = ['N0', 'N10', 'N20', 'N30', 'N50', 'N80', 'N100', 'N150', 'N200']


def ecrire(path, rows):
    # écrit une liste de dictionnaires dans un csv (séparateur ; pour Excel en français)
    if not rows:
        return
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter=';')
        w.writeheader()
        w.writerows(rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sortie', default='analyses_regenerees')
    a = p.parse_args()
    out = ROOT / a.sortie
    out.mkdir(parents=True, exist_ok=True)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from multiobjectif import hypervolume, couverture
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True, 'grid.alpha': .2})

    # 1) Génétique : statistiques à 180 s et courbes de convergence (une case par instance)
    resume = []
    fig, axes = plt.subplots(3, 3, figsize=(12, 9), layout='constrained')
    for ax, n in zip(axes.flat, NOMS):
        runs = [json.loads(p.read_text()) for p in sorted((ROOT / 'resultats/genetique').glob(f'{n}_graine_*.json'))]
        vals = [r['resultat']['Coût 180'] for r in runs]
        ref = runs[0]['reference']
        resume.append(dict(Instance=n, Meilleur=min(vals), Moyenne=statistics.mean(vals), SD=statistics.stdev(vals), Gain_moyen_pct=100 * (ref - statistics.mean(vals)) / ref, Generations=statistics.mean(r['resultat']['Générations'] for r in runs)))
        for r in runs:
            # on prolonge l'historique jusqu'à 180 s pour que la courbe aille au bout
            h = r['resultat']['Historique'] + [[180, r['resultat']['Coût 180']]]
            ax.step([t for t, c in h], [c for t, c in h], where='post', alpha=.65, lw=1)
        ax.set_title(n)
        ax.set_xlabel('Temps (s)')
        ax.set_ylabel('Meilleur coût pénalisé')
    fig.savefig(out / 'convergence_AG.png', dpi=200)
    plt.close(fig)
    ecrire(out / 'synthese_AG.csv', resume)

    # 2) Comparaison des fronts PLS et epsilon-contrainte (hypervolume et couverture)
    eps = json.loads((ROOT / 'resultats/epsilon_fourni.json').read_text())
    comp = []
    fig, axes = plt.subplots(3, 3, figsize=(12, 9), layout='constrained')
    for ax, n in zip(axes.flat, NOMS):
        archive = json.loads((ROOT / 'resultats/multiobjectif' / f'PLS_{n}.json').read_text())
        # Même précision que les points epsilon publiés et le comparateur original.
        P = [(round(x['D'], 1), x['R']) for x in archive['front']]
        E = [tuple(x) for x in eps['fronts_union'][n]]
        ref = eps['references_HV_affichees'][n]
        for pts, color, marker, label in [(P, '#266480', 'o', 'PLS : 1 exécution'), (E, '#c57230', 's', 'ε : union de 5 exécutions')]:
            pts = sorted(pts)
            ax.plot([x for x, y in pts], [y for x, y in pts], color=color, marker=marker, ms=3, lw=.8, label=label)
        ax.set_title(n)
        ax.set_xlabel('Distance D (km)')
        ax.set_ylabel('Reports R')
        comp.append(dict(Instance=n, Points_PLS=len(P), Points_epsilon=len(E), HV_PLS=hypervolume(P, ref), HV_epsilon=hypervolume(E, ref), Couverture_PLS_epsilon_pct=100 * couverture(P, E), Couverture_epsilon_PLS_pct=100 * couverture(E, P), Temps_PLS_s=archive['temps'], Budget_epsilon_cumule_s=900))
    h, l = axes.flat[0].get_legend_handles_labels()
    fig.legend(h, l, loc='outside lower center', ncol=2)
    fig.suptitle('Archives obtenues : conditions et budgets cumulés différents')
    fig.savefig(out / 'comparaison_PLS_epsilon.png', dpi=200)
    plt.close(fig)
    ecrire(out / 'comparaison_PLS_epsilon.csv', comp)

    # 3) Sensibilité du génétique (coût moyen +- écart-type pour chaque valeur testée)
    with (ROOT / 'resultats/sensibilite_etendue.csv').open(encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f, delimiter=';'))
    fig, axes = plt.subplots(2, 3, figsize=(12, 7), layout='constrained')
    for line, n in zip(axes, ['N50', 'N200']):
        for ax, param in zip(line, ['taille_population', 'proba_croisement', 'proba_mutation']):
            r = sorted([x for x in rows if x['Instance'] == n and x['Parametre'] == param], key=lambda x: float(x['Valeur']))
            ax.errorbar([float(x['Valeur']) for x in r], [float(x['Moyenne']) for x in r], yerr=[float(x['SD']) for x in r], marker='o', capsize=3)
            ax.set_title(f'{n} : {param}')
            ax.set_xlabel('Valeur')
            ax.set_ylabel('Coût moyen ± écart-type')
    fig.savefig(out / 'sensibilite_AG.png', dpi=200)
    plt.close(fig)
    print('Analyses produites dans', out)


if __name__ == '__main__':
    main()