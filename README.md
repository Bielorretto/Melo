# Simulateur de piscine Melo

Simulateur maison pour la Piscine 42.

`Melo` permet de tester ses exercices avant la Moulinette, de simuler un examen, de vérifier des modules entiers et d'obtenir de l'aide grâce à un assistant IA.

## Features

* 🤖 **Assistant IA** — Melo explique les sujets et répond aux questions sur les exercices.
* 📝 **Exam Simulator** — Simule les conditions d'un examen avec une progression par niveaux.
* 🧪 **Moulinette Simulator** — Permet de tester plusieurs exercices d'un même module.

---

# ⚙️ Installation

Clone le projet puis installe les dépendances :

```bash
git clone <URL_DU_REPO>
cd Melo
pip install -r requirements.txt
```

Pour utiliser l'Assistant IA :

```bash
export OPENAI_API_KEY=sk-...
```


# 🚲 Lancer Melo

Clone Melo **dans le dossier de ton module** (ta libft, ton dossier de piscine...) : Melo teste toujours son dossier parent.

```bash
cd ~/libft
git clone <URL_DU_REPO> Melo
cd Melo
./cli.py melo
```

Tout se fait ensuite dans le menu, en tapant juste un numéro :

```text
1. 🏊 Piscine          →   1. 📝 Exam
2. 🎓 Common Core          2. 🧪 Module
                           3. 🤖 IA
```

Dans chaque menu : `r` (ou `retour`) revient au menu précédent, `q` quitte Melo.


# 🤖 Assistant IA


![Melo AI Assistant](assets/chatbot.png)

**Melo** est un chatbot qui fonctionne via des appels API directement depuis le terminal.

Elle n'a **pas accès directement aux fichiers de ton projet**.

À la place, Melo dispose d'un outil appelé `get_exercise_subject`.

Lorsque tu lui demandes d'expliquer un exercice :

1. Melo identifie le nom de l'exercice.
2. Elle appelle `get_exercise_subject`.
3. Le programme recherche le `README.md` correspondant dans `exercises/`.
4. Le contenu du sujet est envoyé à l'IA.
5. Melo lit le sujet et te l'explique avec ses propres mots.
6. Elle ne fournit jamais le code de la solution.

Cela permet à Melo de connaître uniquement le sujet dont tu lui demandes l'explication, plutôt que d'avoir accès directement à tous les fichiers du projet.

### Lancer l'Assistant IA

`./cli.py melo`, choisis ton parcours, puis **🤖 IA**. Tape `retour` pour revenir au menu.

Pour utiliser l'API OpenAI, configure ta clé :

```bash
export OPENAI_API_KEY=sk-...
```


# 📝 Exam Simulator

![Exam Simulator](assets/exam.png)


Le mode `exam` permet de simuler une session d'examen avec une progression par niveaux.

### Lancer un examen

`./cli.py melo`, choisis ton parcours, puis **📝 Exam** : choisis ton exam et ton niveau de départ.
Ton code s'écrit dans `rendu/`. Commandes : `test`, `next`, `re`, `sujet`, `help`, `retour`, `quit`.

Le programme recherche les exercices dans :

```text
exercises_exam/
```

Chaque exercice possède son propre dossier contenant :

```text
exercises_exam/
└── ft_xxx/
    ├── README.md
    └── manifest.yaml
```

### README.md

Le `README.md` contient le **sujet de l'exercice**.

Il est affiché lorsque tu arrives sur l'exercice et sert uniquement à t'expliquer ce que tu dois coder.

Le `README.md` n'est **pas utilisé pour vérifier ton code**.

### manifest.yaml

Le `manifest.yaml` contient les **vrais tests** de l'exercice.

Chaque test :

1. compile ton code avec un petit programme `main`,
2. exécute le programme,
3. récupère sa sortie réelle,
4. compare cette sortie avec `expected_stdout`,
5. vérifie également `expected_exit`.

Exemple de fonctionnement :

```text
Ton code
   ↓
Compilation avec le main du test
   ↓
Exécution
   ↓
stdout / exit code
   ↓
Comparaison avec expected_stdout / expected_exit
   ↓
PASS / FAIL
```

### README vs manifest

Ces deux fichiers ont donc des rôles différents :

```text
README.md
    ↓
Explique quoi coder

manifest.yaml
    ↓
Vérifie si ton code fonctionne correctement
```

Il n'y a **aucune comparaison entre le README et le manifest**.

Le mode exam :

* choisit un exercice par niveau depuis `exams/*.yaml`,
* affiche son `README.md`,
* crée le fichier `.c` dans `rendu/`,
* attend que tu codes,
* puis lance les tests du `manifest.yaml` lorsque tu utilises `test`.


# 🧪 Moulinette Simulator

![Moulinette Simulator](assets/moulinette.png)

Le mode `test` permet de vérifier directement ton rendu avec les mêmes principes de tests que le mode exam.

### Lancer un test

`./cli.py melo`, choisis **🏊 Piscine**, puis **🧪 Module** et ton module (celui dans lequel Melo est cloné est marqué `détecté 📍`). Ensuite :

```text
test               # tout le module d'un coup
test ft_putnbr     # un seul exercice
test -v            # sortie complète du compilateur
retour             # revenir à la liste des modules
```

Le programme recherche l'exercice dans :

```text
exercises/
```

⚠️ Ce dossier est différent de `exercises_exam/`, utilisé par le mode exam.

Il récupère ensuite le `manifest.yaml` de l'exercice.

Pour chaque test, le programme :

1. compile ton code avec le `main` du test,
2. exécute le programme,
3. récupère la sortie réelle,
4. compare avec `expected_stdout`,
5. vérifie `expected_exit`,
6. indique si le test passe ou échoue.


# 📚 Common Core : Libft

Le mode `test` sait aussi tester une **libft complète** (sujet v1.3) : les 43 fonctions et toutes les règles du sujet.

### Lancer les tests

Clone Melo dans ta libft, puis `./cli.py melo`, **🎓 Common Core**, **🧪 Module** et **libft** :

```text
test                   # toute la libft
test ft_split          # une seule fonction
test makefile          # une seule section (rendu, makefile, header, symboles, norme, readme)
test --strict          # + vérifications plus sévères que la moulinette
test -h                # fonctions compilées sans libft.h
test ft_split -h       # les options se combinent avec une fonction
test -v                # sortie complète du compilateur
retour                 # revenir à la liste des modules
```

Par défaut, Melo teste comme la moulinette.
`--strict` ajoute des vérifications qu'elle ne fait pas mais qu'un correcteur peut demander :
échecs de malloc simulés, helpers en `static`, `make re`.

### Lire les résultats

- Une section entièrement réussie tient sur une ligne : `[OK] libft/ft_isdigit 4/4`. Seules les sections en échec sont détaillées.
- Chaque KO donne l'`appel` exact qui a échoué, ce qui est `obtenu`, ce qui est `attendu`, et la `règle` du sujet ou du man qui n'est pas respectée :

```text
  [KO] renvoie exactement 1 pour une lettre
       appel    : ft_isalpha('a')  (97)
       obtenu   : 1024
       attendu  : 1
       règle    : Melo attend exactement 1 ou 0 (le man dit seulement « non nul » ...)
```

- Les erreurs de compilation sont résumées en une ligne par erreur, en français : `ft_strlen.c:16  ft_strlen : type différent de sa déclaration dans libft.h:30 (ici size_t(const char *), là-bas int(const char *))`. `-v` affiche la sortie complète de gcc.
- Les erreurs de make courantes sont expliquées (tabulation manquante, `multiple target patterns`, fichier introuvable). Si make ne peut pas lire le Makefile, les autres vérifications du Makefile sont marquées non vérifiées au lieu d'échouer en cascade.
- À la fin, un résumé liste les sections en échec, leur premier KO et la commande pour relancer chacune seule.

### Mode sans header (`-h`)

Avec `-h`, Melo vérifie que chaque fonction se suffit à elle-même :

- un `.c` qui n'utilise ni `t_list` ni une autre fonction du sujet est compilé avec un `libft.h` **vide**. Il doit donc inclure lui-même ce dont il a besoin (`<unistd.h>` pour `write`, `<stdlib.h>` pour `malloc`, `<stddef.h>` pour `size_t`...). C'est cet objet qui est mis dans la lib testée ;
- un `.c` qui utilise `t_list` ou appelle une autre fonction du sujet (ex. `ft_strjoin` qui appelle `ft_strlen`) est compilé normalement avec ton `libft.h` ;
- les mains de test utilisent le `libft.h` de référence de Melo (prototypes exacts du sujet) au lieu du tien.

Ce mode n'est pas une règle de la moulinette : c'est un contrôle en plus, à lancer quand tu veux.

### Ce qui est testé

| Section | Vérifications |
|---------|---------------|
| `rendu` | fichiers obligatoires, tout à la racine, aucun fichier en trop, chaque `.c` compile avec `-Wall -Wextra -Werror`, pas de `restrict` |
| `makefile` | `make` crée `libft.a`, règles `$(NAME) all clean fclean re`, `cc` + flags, `ar` (pas `libtool`), pas de relink, aucun `.c` inutilisé, `clean`, `fclean` (+ `re` en `--strict`) |
| `header` | `libft.h` compile seul, protégé contre la double inclusion, `t_list` conforme, prototypes exacts du sujet |
| `symboles` | toutes les fonctions présentes, pas de variable globale, helpers en `static` (`--strict`), seules les fonctions externes autorisées par le sujet (`nm`) |
| `norme` | `norminette` sur tous les `.c` et `.h` (ignoré si non installée) |
| `readme` | première ligne en italique, sections Description / Instructions / Resources, usage de l'IA décrit |
| `ft_*` | comportement de chaque fonction comparé au sujet ou à la vraie libc, cas limites, fuites et erreurs mémoire (valgrind), **échecs de malloc simulés** en `--strict` (la fonction doit renvoyer NULL sans fuite) |

### Vérification du README de la libft

| Règle du sujet | Ce que Melo vérifie |
|----------------|---------------------|
| `README.md` à la racine | le fichier existe |
| Première ligne en italique | exactement `*This activity has been created as part of the 42 curriculum by <login1>[, <login2>...]*` (ou `_..._`, pas en gras) |
| Section Description | un titre `#` contenant « Description » |
| Section Instructions | un titre `#` contenant « Instructions » |
| Section Resources | un titre `#` contenant « Resources » (ou « Ressources ») |
| Usage de l'IA décrit dans Resources | une mention de l'IA (AI, IA, ChatGPT, LLM...) dans Resources ou ses sous-sections |

Non vérifié (à relire toi-même) : le contenu des sections, la description détaillée de la librairie, les références de Resources et le détail des tâches où l'IA a servi.

Le Makefile est testé sur une copie : ton dossier n'est jamais modifié.
Les fonctions sont testées avec une lib compilée par Melo, donc un Makefile cassé n'empêche pas de tester les fonctions.

⚠️ La simulation d'échec de malloc utilise `ld --wrap` : Linux uniquement.

### Où sont les tests

```text
projects/libft/project.yaml        # prototypes, fonctions autorisées, règle de chaque fonction, fichiers attendus
projects/libft/includes/           # helpers C des tests (melo.h, melo_malloc.h)
projects/libft/part1|2|3/ft_*/manifest.yaml
```
