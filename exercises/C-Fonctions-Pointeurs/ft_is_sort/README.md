Exercice 4 : ft_is_sort

Exercice: 4
ft_is_sort
Répertoire: ex4/
Fichiers à Rendre: ft_is_sort.c
Autorisé: None

- Créez une fonction ft_is_sort qui retourne 1 si le tableau est trié
  (croissant ou décroissant), sinon 0.
- La fonction de comparaison fournie doit retourner :
  - un nombre négatif si a < b,
  - 0 si a == b,
  - un nombre positif sinon.

Prototype :
int ft_is_sort(int *tab, int length, int(*f)(int, int));
