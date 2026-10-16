# alpha_mirror

Fichiers à rendre : `alpha_mirror.c`
Autorisé : `write`

Écrivez un programme `alpha_mirror` qui prend une chaîne de caractères et
l'affiche après avoir remplacé chaque caractère alphabétique par le
caractère alphabétique opposé, suivie d'un retour à la ligne.

'a' devient 'z', 'Z' devient 'A'
'd' devient 'w', 'M' devient 'N'

etc. La casse n'est pas modifiée.

Si le nombre d'arguments n'est pas 1, affichez uniquement un retour à la
ligne.

Exemples :

    $> ./alpha_mirror "abc"
    zyx
    $> ./alpha_mirror "My horse is Amazing." | cat -e
    Nb slihv rh Znzarmt.$
    $> ./alpha_mirror | cat -e
    $
