# Nexovia - planification des interventions

Projet d’Introduction au Génie Industriel réalisé à Mines Nancy par **Maroua Nabih, Mathis Raffin et Axel Chasteauneuf** (2026–2027).

L’objectif est de construire le planning d’une journée de techniciens : affecter les interventions, choisir leur ordre et limiter les déplacements ainsi que les reports. Les solutions doivent respecter les compétences, les horaires et les disponibilités.

## Travail réalisé

Nous avons étudié neuf instances, de 8 à 200 interventions, avec plusieurs approches :

- Construction d’un planning initial par une heuristique gloutonne, puis amélioration par deux descentes locales.
- Comparaison de la recherche tabou, du recuit simulé et d’un algorithme génétique ; essais d’une méthode hybride ALNS + tabou.
- Étude du compromis entre distance et nombre de reports avec l’ε-contrainte et la recherche locale de Pareto (PLS).
- Réglage des paramètres et expériences complémentaires sur le recuit et le génétique.

Les méthodes, les résultats et leurs limites sont présentés dans le [rapport final](docs/Rapport_final_Nexovia.pdf) et son [complément](docs/Complement_Nexovia.pdf).

## Utilisation

Avec Python 3.12, depuis le dossier du projet :

```bash
python -m pip install -r requirements.txt
```

Ouvrir [Nexovia.ipynb](Nexovia.ipynb) pour parcourir les méthodes et exécuter les exemples. Les implémentations sont dans `code/` ; le notebook les importe sans les recopier. Les campagnes longues sont désactivées par défaut.

Pour un premier essai depuis le terminal :

```bash
python code/lancer.py genetique --instances N0 --secondes 1 --graines 1
```

Le [guide d’utilisation](docs/UTILISATION.md) rassemble les autres commandes, les paramètres et les vérifications.

## Contenu du dépôt

| Dossier | Contenu |
|---|---|
| `code/` | Algorithmes, expériences et analyses |
| `donnees/` | Instances CSV et solutions de départ |
| `resultats/` | Résultats du rendu et expériences complémentaires |
| `docs/` | Rapport, complément et guide d’utilisation |
| `tests/`, `tools/` | Vérifications des solutions et du notebook |

Les résultats conservés sont ceux du projet. Les calculs étant limités en temps, une nouvelle exécution peut donner des valeurs différentes selon la machine et la graine utilisée.
