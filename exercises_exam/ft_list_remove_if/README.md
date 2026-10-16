# ft_list_remove_if

Fichiers à rendre : `ft_list_remove_if.c`, `ft_list.h`
Autorisé : `free`

Écrivez une fonction `ft_list_remove_if` qui supprime de la liste passée
en paramètre tout élément dont la donnée est "égale" à la donnée de
référence.

Prototype :

    void ft_list_remove_if(t_list **begin_list, void *data_ref, int (*cmp)());

`cmp` prend deux `void *` et retourne 0 quand les deux paramètres sont
égaux.

Vous devez utiliser le fichier `ft_list.h`, qui contiendra :

    typedef struct      s_list
    {
        struct s_list   *next;
        void            *data;
    }                   t_list;
