# repeat_alpha

Fichiers à rendre : `repeat_alpha.c`
Autorisé : `write`

Écrivez un programme `repeat_alpha` qui prend une chaîne de caractères et
l'affiche en répétant chaque caractère alphabétique autant de fois que son
index dans l'alphabet, suivi d'un retour à la ligne.

'a' devient 'a', 'b' devient 'bb', 'e' devient 'eeeee', etc.
La casse reste inchangée.

Si le nombre d'arguments n'est pas 1, affichez simplement un retour à la ligne.

Exemples :

    $> ./repeat_alpha "abc"
    abbccc
    $> ./repeat_alpha "Alex." | cat -e
    Alllllllllllleeeeexxxxxxxxxxxxxxxxxxxxxxxx.$
    $> ./repeat_alpha 'abacadaba 42!' | cat -e
    abbacccaddddabba 42!$
    $> ./repeat_alpha | cat -e
    $
    $> ./repeat_alpha "" | cat -e
    $
