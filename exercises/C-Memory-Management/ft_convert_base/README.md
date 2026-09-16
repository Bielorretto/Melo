Exercice 4 : ft_convert_base

Exercice: 4
ft_convert_base
Répertoire: ex4/
Fichiers à Rendre: ft_convert_base.c, ft_convert_base2.c
Autorisé: malloc, free

- Créez une fonction qui retourne le resultat de la conversion de la
  chaine nbr d'une base base_from vers une base base_to.
- Le systeme de base est constitue de tous les symboles utilises pour
  representer le nombre (ex: "0123456789" pour le decimal, "01" pour le
  binaire, "0123456789ABCDEF" pour l'hexadecimal, "poneyvif" pour un
  systeme octal personnalise).
- nbr, base_from, base_to peuvent ne pas etre modifiables.
- nbr est exprime dans la base base_from.
- Le nombre represente par nbr doit tenir dans un int.
- Si une base est invalide, NULL doit etre retourne. Exemples d'arguments
  invalides :
  - la base est vide ou n'a qu'un seul caractere,
  - la base contient des caracteres dupliques,
  - la base contient '+', '-', ou des espaces.
- Le nombre retourne ne doit etre prefixe que par un seul et unique '-'
  si necessaire, sans espace, sans '+'.

Prototype :
char *ft_convert_base(char *nbr, char *base_from, char *base_to);
