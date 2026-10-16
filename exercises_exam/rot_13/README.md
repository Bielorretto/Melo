# rot_13

Fichiers à rendre : `rot_13.c`
Autorisé : `write`

Écrivez un programme qui prend une chaîne de caractères et l'affiche en
remplaçant chaque lettre par la lettre située 13 places plus loin dans
l'alphabet.

'z' devient 'm' et 'Z' devient 'M'. La casse n'est pas modifiée.

La sortie est suivie d'un retour à la ligne.

Si le nombre d'arguments n'est pas 1, le programme affiche un retour à la
ligne.

Exemples :

    $> ./rot_13 "abc"
    nop
    $> ./rot_13 "My horse is Amazing." | cat -e
    Zl ubefr vf Nznmvat.$
    $> ./rot_13 "AkjhZ zLKIJz , 23y " | cat -e
    NxwuM mYXVWm , 23l $
    $> ./rot_13 | cat -e
    $
    $> ./rot_13 "" | cat -e
    $
