Exercice 7 : ft_atoi

Exercice: 7
ft_atoi
Répertoire: ex7/
Fichiers à Rendre: ft_atoi.c
Autorisé: None

- Ecrivez une fonction qui convertit la portion initiale de la chaine
  pointee par str en sa representation entiere.
- La chaine peut commencer par un nombre arbitraire d'espaces (au sens
  de isspace(3)).
- La chaine peut etre precedee d'un nombre arbitraire de signes + et -.
- Un signe - changera le signe de l'entier retourne selon que le nombre
  de - est impair ou pair.
- La fonction doit lire la chaine jusqu'a rencontrer un caractere non
  numerique et retourner le nombre trouve jusque-la.
- Vous n'avez pas besoin de gerer les depassements (overflow/underflow) ;
  le resultat peut etre indefini dans ce cas.

Exemple :
$> ./a.out " --+-+1234ab567"
-1234

Prototype :
int ft_atoi(char *str);
