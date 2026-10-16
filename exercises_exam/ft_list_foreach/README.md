# ft_list_foreach

Fichiers à rendre : `ft_list_foreach.c`, `ft_list.h`
Autorisé : aucune

Écrivez une fonction qui prend une liste et un pointeur de fonction, et
applique cette fonction à chaque élément de la liste.

Prototype :

    void ft_list_foreach(t_list *begin_list, void (*f)(void *));

La fonction pointée par `f` sera utilisée ainsi :

    (*f)(list_ptr->data);

Vous devez utiliser la structure suivante, et la rendre dans un fichier
appelé `ft_list.h` :

    typedef struct    s_list
    {
        struct s_list *next;
        void          *data;
    }                 t_list;
