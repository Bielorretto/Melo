# sort_list

Fichiers à rendre : `sort_list.c`
Autorisé : aucune

Écrivez la fonction suivante :

    t_list *sort_list(t_list *lst, int (*cmp)(int, int));

Cette fonction doit trier la liste passée en paramètre, en utilisant le
pointeur de fonction `cmp` pour choisir l'ordre à appliquer, et retourne
un pointeur vers le premier élément de la liste triée.

Les doublons doivent être conservés.

Les entrées seront toujours cohérentes.

Vous devez utiliser le type `t_list` décrit dans le fichier `list.h` qui
vous est fourni. Vous devez l'inclure (`#include "list.h"`), mais vous ne
devez pas le rendre. Nous utiliserons le nôtre pour compiler votre
exercice.

Les fonctions passées en `cmp` retourneront toujours une valeur différente
de 0 si a et b sont dans le bon ordre, 0 sinon.

Par exemple, la fonction suivante utilisée comme `cmp` trie la liste par
ordre croissant :

    int ascending(int a, int b)
    {
        return (a <= b);
    }
