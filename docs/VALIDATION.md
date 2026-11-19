# Préparation de l’édition GitHub

Date : 19 novembre 2026. Source : notebook final transmis par Axel (`Nexovia_code_complet.ipynb`, 112 cellules). Empreinte SHA-256 de l’original :

```
c68f7f95ad444209363bda44c36990aee22e4ecdc62a5c2dd417d61cc7669abf
```

## Changements dans la copie publiée

- L’export du socle est déplacé après la définition du glouton, pour éviter une utilisation avant définition.
- La liste des instances est définie avant la première boucle qui l’utilise.
- Les campagnes finales de descente, tabou et hybride lisent les départs communs de `S0_communs.json`. Les gloutons recalculés restent disponibles pour les exemples et les études exploratoires.
- Les campagnes longues sont protégées par `LANCER_CAMPAGNES = False`. Les exemples courts restent actifs. L’activation explicite lance aussi les campagnes intermédiaires de réglage.
- Les fonctions locales, tabou et hybrides sont exportées dans `code/local_tabou.py` pour un usage sans notebook.
- Le script exact crée son dossier de sortie s’il manque ; le lecteur CSV indépendant ferme explicitement ses fichiers.
- Le départ historique N50 est extrait des archives dans `S0_exploratoires.json` et chargé explicitement par les lanceurs exploratoires. La première exécution sur GitHub a révélé que le glouton recalculé pouvait donner 687,919 au lieu de 614,036 selon la version de pandas ; charger le planning sauvegardé conserve le protocole des compléments.
- Les sorties intégrées au notebook sont retirées. Les archives de résultats sont conservées dans leurs dossiers, séparément des nouveaux calculs.
- La déclaration d’assistance IA est précisée, et la limite connue du blocage tabou est expliquée.

Les fonctions des algorithmes ne sont pas réécrites pour cette publication. Les modules des cellules `%%writefile` sont extraits tels quels, à l’exception des corrections de gestion des fichiers et du chargement explicite du départ historique N50. Le socle et les méthodes locales assemblent les définitions du notebook. Les formats de sortie des lanceurs historiques sont conservés ; le README distingue leurs usages.

## Vérifications

Le notebook a été exécuté jusqu’au bout dans un noyau Jupyter vierge, sur une copie temporaire, avec les campagnes longues désactivées. Les exemples incluent recuit, génétique, hybride, ε-contrainte et PLS.

`code/verifier.py` recalcule indépendamment depuis les CSV les coûts et la faisabilité des **45 solutions AG** et des **397 points des neuf archives PLS**, puis vérifie la non-dominance dans chaque archive. Il réalise aussi de courts essais AG sur N0, N50 et N200 et un essai PLS sur N0.

Les tests supplémentaires contrôlent les neuf départs communs, la distinction entre le départ exploratoire N50 et le départ commun, les trois politiques de renouvellement sur un essai court, le recuit et sa variante P, la dominance et les **25 solutions finales des compléments**.

Les longues campagnes ne sont pas relancées pour cette publication. Les sorties brutes de la variante du recuit à P essais et des campagnes tabou/hybride ne faisaient pas partie des archives disponibles ; les programmes sont présents, mais aucun résultat n’est reconstruit ou inventé. Les valeurs du complément PDF restent celles du document du groupe.

## Reproductibilité

Les données CSV et `S0_communs.json` sont identiques à ceux du dossier final disponible. Les résultats historiques et les synthèses du rapport final sont copiés, sans modification numérique. Le rapport du 7 novembre et le complément final du 18 novembre sont joints comme documents de référence. Les sorties PLS volumineuses contiennent aussi leurs historiques ; elles sont gardées pour conserver la traçabilité complète.

Les budgets sont des temps muraux : changer de machine, de charge ou de nombre de processus peut changer les solutions, même à graine identique. La vérification garantit la faisabilité et la cohérence des coûts des solutions contrôlées, pas l’optimalité ni une reproduction exacte des valeurs à durée fixée.
