# Analyse statistique exploratoire

Les unités sont les huit instances N10 à N200, et non les graines. Nous utilisons les moyennes à 180 s arrondies au centième. N0 est exclue en raison du départ différent du tabou. Cette analyse décrit les résultats disponibles : machines, réglages et budgets effectifs diffèrent et les instances ne constituent pas un échantillon aléatoire. Elle ne démontre pas une supériorité causale de l’algorithme.

Friedman corrigé des ex æquo : Q = 7.4667. Probabilité par permutation exacte des étiquettes de méthode au sein de chaque instance : p = 0.019762.

Rangs moyens (plus petit = mieux) : RS = 1.250, Tabou = 2.500, AG = 2.250.

| Comparaison des moyennes par instance | Différences non nulles | p Wilcoxon exact | p corrigé Holm |
|---|---:|---:|---:|
| RS / Tabou | 8 | 0.02344 | 0.07031 |
| RS / AG | 6 | 0.03125 | 0.07031 |
| Tabou / AG | 8 | 0.38281 | 0.38281 |

Wilcoxon : rangs moyens des différences absolues, zéros retirés et distribution exacte des signes ; correction de Holm sur trois comparaisons. Les arrondis peuvent transformer une petite différence en ex æquo. Ces calculs ne remplacent pas des tests sur cinq sorties individuelles complètes par méthode dans des conditions contrôlées. Les quartiles du recuit et du tabou ne sont pas disponibles pour toutes les instances ; aucune boîte à moustaches n’a été inventée à partir de leurs moyennes.
