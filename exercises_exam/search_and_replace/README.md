# search_and_replace

Fichiers à rendre : `search_and_replace.c`
Autorisé : `write`, `exit`

Écrivez un programme `search_and_replace` qui prend 3 arguments : une
chaîne dans laquelle remplacer une lettre (2e argument) par une autre
(3e argument).

Les 2e et 3e arguments doivent être des lettres uniques : si l'un d'eux ne
fait pas exactement un caractère, le programme affiche uniquement un retour
à la ligne.

Si le nombre d'arguments n'est pas 3, affichez simplement un retour à la
ligne.

Si le 2e argument n'est pas présent dans la chaîne, le programme réaffiche
simplement la chaîne suivie d'un retour à la ligne.

Exemples :

    $> ./search_and_replace "Papache est un sabre" "a" "o"
    Popoche est un sobre
    $> ./search_and_replace "zaz" "art" "zul" | cat -e
    $
    $> ./search_and_replace "zaz" "r" "u" | cat -e
    zaz$
    $> ./search_and_replace "jacob" "a" "b" "c" "e" | cat -e
    $
    $> ./search_and_replace "ZoZ eT Dovid oiME le METol." "o" "a" | cat -e
    ZaZ eT David aiME le METal.$
    $> ./search_and_replace "wNcOre Un ExEmPle Pas Facilw a Ecrirw " "w" "e" | cat -e
    eNcOre Un ExEmPle Pas Facile a Ecrire $
