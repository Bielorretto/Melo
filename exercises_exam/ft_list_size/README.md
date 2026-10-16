# ft_list_size

Fichiers à rendre : `ft_list_size.c`, `ft_list.h`
Autorisé : aucune

Écrivez une fonction qui retourne le nombre d'éléments de la liste chaînée
passée en paramètre.

Prototype :

    int ft_list_size(t_list *begin_list);

Vous devez utiliser la structure suivante, et la rendre dans un fichier
appelé `ft_list.h` :

    typedef struct    s_list
    {
        struct s_list *next;
        void          *data;
    }                 t_list;
