Exercice 5 : ft_split

Exercice: 5
ft_split
Répertoire: ex5/
Fichiers à Rendre: ft_split.c
Autorisé: malloc

- Créez une fonction qui decoupe une chaine de caracteres en fonction
  d'une autre chaine de caracteres.
- Chaque caractere de la chaine charset doit etre utilise comme
  separateur.
- La fonction retourne un tableau ou chaque element du tableau contient
  l'adresse d'une chaine encadree par deux separateurs. Le dernier
  element de ce tableau doit valoir 0 pour indiquer la fin du tableau.
- Il ne peut y avoir aucune chaine vide dans votre tableau. Tirez-en vos
  propres conclusions.
- La chaine donnee en argument ne doit pas etre modifiable.

Prototype :
char **ft_split(char *str, char *charset);
