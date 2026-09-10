# piscine-tester

Testeur maison pour la piscine 42 : teste tes exos avant la moulinette,
simule un examen, et propose une aide IA pour l'explications et la comprehension des sujets.

![Screenshot](assets/chatbot.png)
## Installation

```bash
pip install -r requirements.txt
```

Pour l'aide IA :
```bash
export OPENAI_API_KEY=sk-...
```

## Utilisation

```bash
# lister les exercices disponibles
./cli.py list

# tester un exercice
./cli.py test ft_strdup /chemin/vers/mon/rendu/

# simuler un examen 
./cli.py exam

# lancer le chatbot 
./cli.py melo

```
