# rev_print

Fichiers à rendre : `rev_print.c`
Autorisé : `write`

Écrivez un programme qui prend une chaîne de caractères et l'affiche en
inverse, suivie d'un retour à la ligne.

Si le nombre de paramètres n'est pas 1, le programme affiche un retour à la
ligne.

Exemples :

    $> ./rev_print "zaz" | cat -e
    zaz$
    $> ./rev_print "dub0 a POIL" | cat -e
    LIOP a 0bud$
    $> ./rev_print | cat -e
    $
