Exercice 10 : ft_putstr_non_printable

Exercice: 10
ft_putstr_non_printable
Répertoire: ex10/
Fichiers à Rendre: ft_putstr_non_printable.c
Autorisé: write

- Créez une fonction qui affiche la chaine donnée en parametre sur la
  sortie standard. Si cette chaine contient des caracteres non
  imprimables, ils doivent etre affiches sous forme hexadecimale (en
  minuscules), precedes d'un unique antislash '\'.

Exemple :
"Hello\nHow are you ?" s'affiche "Hello\0aHow are you ?"

Prototype :
void ft_putstr_non_printable(char *str);
