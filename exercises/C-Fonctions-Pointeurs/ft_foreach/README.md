Exercice 0 : ft_foreach

Exercice: 0
ft_foreach
Répertoire: ex0/
Fichiers à Rendre: ft_foreach.c
Autorisé: None

- Créez la fonction ft_foreach qui applique une fonction donnée à tous les
  éléments d'un tableau d'entiers, dans l'ordre du tableau.

Prototype :
void ft_foreach(int *tab, int length, void(*f)(int));

Exemple d'utilisation :
ft_foreach(tab, 1337, &ft_putnbr);
