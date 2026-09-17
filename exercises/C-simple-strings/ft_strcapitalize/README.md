Exercice 7 : ft_strcapitalize

Exercice: 7
ft_strcapitalize
Répertoire: ex7/
Fichiers à Rendre: ft_strcapitalize.c
Autorisé: None

- Créez une fonction qui capitalise une chaine, directement dans cette
  chaine (en place) : la premiere lettre de chaque mot doit etre mise en
  majuscule, et le reste des lettres du mot en minuscule.
- Un mot est une suite de caracteres alphanumeriques ; tout caractere non
  alphanumerique (espace, ponctuation...) delimite les mots et n'est pas
  modifie. Les chiffres ne sont jamais modifies mais restent rattaches au
  mot courant.
- La fonction retourne la chaine modifiee.

Exemple :
"bonjour, tout LE monde !" devient "Bonjour, Tout Le Monde !"

Prototype :
char *ft_strcapitalize(char *str);
