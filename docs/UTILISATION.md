# Utiliser le projet Nexovia

Ce guide correspond à l’organisation du dépôt ; les rapports conservent les noms de fichiers du rendu initial. Les commandes se lancent depuis la racine du dépôt, avec Python 3.12. Pour isoler les dépendances :

```bash
python -m venv .venv
source .venv/bin/activate
# Windows : .venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Parcourir le notebook

[Nexovia.ipynb](../Nexovia.ipynb) présente les méthodes dans l’ordre du projet et propose des exemples courts. Les fonctions sont définies dans les fichiers Python de `code/` ; le notebook les importe. Pour l’ouvrir localement :

```bash
python -m pip install jupyterlab
python -m jupyterlab Nexovia.ipynb
```

Les campagnes de descente, de tabou et d’hybride du notebook sont lancées uniquement si `LANCER_CAMPAGNES = True`. Leur durée peut atteindre plusieurs heures.

## Fichiers Python

| Programme | Rôle |
|---|---|
| `socle.py` | Lecture des données, contraintes, coût et glouton |
| `local_tabou.py` | Voisinage, deux descentes, recherche tabou et hybride |
| `recuit.py`, `recuit_P.py` | Recuit simulé et variante à essais indépendants |
| `genetique.py` | Génétique du rendu, avec renouvellement à 20 % / 40 % |
| `genetique_renouvellement.py` | Variante utilisée pour comparer les taux de renouvellement |
| `epsilon_contrainte.py`, `multiobjectif.py` | ε-contrainte et PLS |
| `exact_N0.py` | Énumération exacte sur N0 |

Les deux fichiers du génétique correspondent à deux protocoles distincts. Le premier conserve les paramètres du rendu ; le second permet de faire varier le renouvellement. Les fonctions des algorithmes sont celles de la version finale du projet.

## Lancer les expériences

### Génétique et PLS

```bash
python code/lancer.py genetique --instances N50 --secondes 180 --graines 1 2 3 4 5
python code/lancer.py pls --instances N50 --secondes 180
```

Les nouvelles sorties sont horodatées dans `nouveaux_resultats/`. Le format de ce lanceur est regroupé ; les scripts d’analyse ci-dessous lisent les archives du rendu.

Le réglage du génétique se lance avec `sensibilite_diversite.py` :

```bash
python code/sensibilite_diversite.py sensibilite
python code/sensibilite_diversite.py combinaisons
python code/sensibilite_diversite.py diversite
```

Pour un essai court, ajouter `--instances N50 --graines 1 --secondes 1`.

### Recuit et ε-contrainte

`campagne_recuit.py` contient les campagnes monoobjectif, de sensibilité et d’ε-contrainte. Les paramètres se trouvent dans le programme. `analyse_recuit.py` analyse leurs sorties lorsqu’elles sont disponibles.

```bash
python code/campagne_recuit.py mono '{"tau0": 0.1, "alpha": 0.99, "k_palier": 20}'
python code/campagne_recuit.py eps 0.1
python code/comparer_P.py
```

`comparer_P.py` compare le recuit du rendu à la variante à 1, 3 ou 5 essais indépendants, sur N50, N100 et N200. La campagne complète représente 60 exécutions de 180 secondes.

### Compléments sur le génétique

Un seul programme permet de lancer chaque étude ou l’ensemble :

```bash
python code/experiences.py --etude temps-long
python code/experiences.py --etude renouvellement
python code/experiences.py --etude temoin
python code/experiences.py
```

| Étude | Protocole |
|---|---|
| `temps-long` | Génétique original sur N200, cinq graines, 400 s par essai |
| `renouvellement` | N50, politiques 0/0, 10/20 et 20/40 %, cinq graines, 20 s par essai |
| `temoin` | Recuit sur N200, cinq graines, 180 s par essai |

Sans option, les trois études sont exécutées. `--graines 1` limite le nombre d’essais et `--processus 1` limite la concurrence sur N200. N50 conserve trois processus synchronisés pour comparer les politiques par graine. Utiliser `--plan` pour afficher les essais prévus sans les lancer.

Les sorties vont dans `nouveaux_resultats/complements/`. Choisir un autre dossier avec `--sortie` pour recommencer une campagne ; le programme refuse d’écraser des résultats existants.

## Refaire les tableaux et les figures

Ces commandes analysent les fichiers déjà enregistrés, sans relancer les méthodes :

```bash
python code/analyser.py
python code/analyser_apports.py
```

La première lit les archives AG, PLS et ε-contrainte de `resultats/`. La seconde lit les compléments dans `resultats/complements/`. Les analyses sont écrites dans `analyses_regenerees/` et `analyses/`.

## Départs et résultats conservés

Les comparaisons finales utilisent `donnees/S0_communs.json`. Le départ exploratoire N50 de coût 614,036 est sauvegardé dans `donnees/S0_exploratoires.json` : le recalcul du glouton peut varier selon les départages de pandas. Les archives PLS conservent leur départ historique. Ces protocoles sont décrits dans les rapports.

Le dépôt contient 45 sorties du génétique, neuf archives PLS et 25 sorties des compléments. Pour les autres méthodes, les synthèses du rapport sont fournies ; toutes les sorties individuelles ne sont pas disponibles. Les valeurs des documents n’ont pas été recalculées pour le dépôt.

Les méthodes sont heuristiques, sauf l’énumération de N0. La recherche tabou peut s’arrêter lorsque tous les mouvements deviennent tabous ; cette version ne comporte pas de critère d’aspiration. Les temps muraux dépendent de la machine et du nombre de processus.

## Vérifier les solutions

```bash
python code/verifier.py
python -m unittest discover -s tests -v
```

Le premier contrôle indépendamment les coûts, la faisabilité et la non-dominance des archives AG et PLS depuis les CSV, puis lance quelques essais courts. Les tests couvrent aussi les départs, le renouvellement, le recuit et les 25 solutions des compléments.

Pour exécuter toutes les cellules du notebook dans une copie temporaire :

```bash
python -m pip install -r requirements-dev.txt
python tools/verifier_notebook.py
```

Ces vérifications sont aussi exécutées par GitHub Actions. Elles contrôlent la cohérence des solutions, sans garantir l’optimalité des heuristiques.
