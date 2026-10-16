# last_word

Fichiers à rendre : `last_word.c`
Autorisé : `write`

Écrivez un programme qui prend une chaîne de caractères et affiche son
dernier mot suivi d'un \n.

Un mot est une portion de chaîne délimitée par des espaces/tabulations ou
par le début/la fin de la chaîne.

Si le nombre de paramètres n'est pas 1, ou s'il n'y a aucun mot, affichez un
retour à la ligne.

Exemples :

    $> ./last_word "FOR PONY" | cat -e
    PONY$
    $> ./last_word "this        ...       is sparta, then again, maybe    not" | cat -e
    not$
    $> ./last_word "   " | cat -e
    $
    $> ./last_word "a" "b" | cat -e
    $
    $> ./last_word "  lorem,ipsum  " | cat -e
    lorem,ipsum$
