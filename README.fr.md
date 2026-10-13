<p align="center"><img src="assets/logo.png" width="96" alt="logo tokenleak"></p>

<h1 align="center">tokenleak</h1>

<p align="center"><b>Trouve et colmate les fuites de tokens de ton agent de code.</b><br>
Rien à voir avec des clés API qui fuient : il s'agit des tokens que ton agent IA brûle en contexte inutile.</p>

<p align="center"><a href="README.md">English</a></p>

<p align="center"><img src="assets/demo.gif" alt="L'audit des 30 derniers jours de Claude Code de l'auteur : ce que Claude a écrit pèse 12 % du coût, le contexte 88 % ; 62 % des appels portaient plus de 200k tokens de contexte ; rejouées avec une compaction à 300k, ces sessions auraient coûté environ 21 % de moins (estimation)." width="900"></p>

**Essaie-le, rien à installer :** vois où sont partis tes propres tokens. L'audit lit tes transcripts en local et n'envoie rien (Python 3.8+, aucune dépendance).

```bash
uvx tokenleak --since 7d
```

Sans uv : `pipx run tokenleak --since 7d`.

**Les règles de tokenleak réduisent de 32 % le coût de Claude Code sur Sonnet 5** (40 runs par bras, IC à 95 % de −42 % à −20 %, 40/40 réussis des deux côtés ; −19 % sans la tâche qui gagne le plus). Tâches petites et synthétiques : [BENCHMARK.md](BENCHMARK.md) donne chaque chiffre avec son intervalle, y compris ceux qui vont dans l'autre sens.

## Pourquoi

Dans une boucle d'agent, **chaque résultat d'outil qui entre dans le contexte est renvoyé à chaque appel suivant**, jusqu'à la compaction. Un log de tests de 6k tokens lu à l'appel 5 d'une session de 60 appels est payé ~55 fois de plus. Chaque aller-retour supplémentaire renvoie tout le contexte.

La facture ne dépend donc pas de la longueur des réponses de l'agent, mais de **ce qu'il laisse entrer dans son contexte, et quand**. Dans les runs du [benchmark](README.md#benchmark) sans tokenleak, tout ce que le modèle a écrit (réponses, appels d'outils, réflexion) pesait 7 % du coût d'un run sur Sonnet et 10 à 11 % sur Haiku (médianes) ; le reste, c'était du contexte. Raccourcir les réponses économise la petite part. L'audit montre cette répartition sur vos propres sessions.

tokenleak fait deux choses :

1. **Des règles** (un skill d'environ 770 tokens) pour que n'importe quel agent ne laisse entrer que ce dont la prochaine décision a besoin : localiser puis lire, calculer plutôt que lire les données, borner la sortie de chaque commande, ne jamais relire, grouper les appels indépendants, des diffs plutôt que des fichiers, éditer plutôt que réécrire. Avec des garde-fous : jamais d'économie en devinant un fichier ou en sautant une vérification.
2. **Un audit** qui lit *tes* transcripts Claude Code et Codex et montre où sont vraiment partis les tokens : lectures surdimensionnées, logs bavards, appels gaspillés, allers-retours en série. Chacun est chiffré par la **taxe de contexte** qu'il a imposée, avec la règle qui le corrige. Local, lecture seule, zéro dépendance.

## Sessions longues : le réglage qui compte le plus

Avec une fenêtre de contexte d'un million de tokens, Claude Code ne compacte qu'à l'approche de la limite. Jusque-là, tout reste dans le contexte et repart à chaque appel, y compris ce que le modèle a lui-même écrit (réflexion, réponses, appels d'outils) : 42 % de tout le contexte renvoyé dans les sessions de l'auteur sur 30 jours, plus que tous les résultats d'outils réunis. L'audit rejoue vos propres sessions avec une compaction plus précoce (`autoCompactWindow`, un réglage natif de Claude Code : tokenleak dit seulement s'il faut le régler, et à quelle valeur) et vous dit ce qu'elle aurait économisé ; sur ces 30 jours, `300000` donnait −21 % sur toute la facture. Mesuré en direct sur une session plus longue : une compaction précoce a réduit de 44 % le contexte renvoyé, à coût égal et qualité égale (4/4) ; en régime 1M (Sonnet 5, 4 runs par bras) : −16 % de coût (IC à 95 % : −36 % à −6 %). La qualité a tenu même au réglage le plus dur (100k, 1 à 3 compactions en pleine tâche : 12/12 runs Haiku et 3/3 Sonnet réussis), mais sur des sessions courtes la compaction coûte plus qu'elle ne rapporte : l'audit ne recommande une valeur que si vos sessions montrent un gain d'au moins 5 %. Détails et méthode : [README anglais](README.md#long-sessions-the-setting-that-matters-most).

## Installation

**Claude Code (plugin, recommandé)** : règles injectées au démarrage, après compaction et dans chaque sous-agent, plus un **garde-fou de lecture** (la lecture entière d'un gros fichier texte est stoppée ; pour du code ou du Markdown, l'agent reçoit à la place le plan du fichier, définitions ou titres avec leurs numéros de ligne, pour ne lire que la partie utile ; passer `limit` passe toujours) et le skill `/tokenleak`. Désactivable avec `TOKENLEAK_GUARD=0`.

```
/plugin marketplace add Pazificateur69/tokenleak
/plugin install tokenleak@tokenleak
```

**Tout agent compatible Agent Skills** (Codex, Cursor, Gemini CLI, GitHub Copilot, Windsurf, Cline, OpenCode…) :

```bash
npx skills add Pazificateur69/tokenleak -g
```

**Toujours actif, sans installation** : ajoute les règles à ton fichier d'instructions (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.cursorrules`…).

```bash
curl -fsSL https://raw.githubusercontent.com/Pazificateur69/tokenleak/v1.9.0/skills/tokenleak/SKILL.md | awk '/^## Audit/{exit} f>=2; /^---$/{f++}' >> AGENTS.md
```

## L'audit

```bash
curl -fsSLO https://raw.githubusercontent.com/Pazificateur69/tokenleak/v1.9.0/skills/tokenleak/scripts/tokenleak.py
shasum -a 256 tokenleak.py   # 983cd19a96327d13d75d9fc13bbf75f6ea67e90369dcebe4629dab96e7612b70
python3 tokenleak.py --since 30d
```

Ou installez la CLI depuis [PyPI](https://pypi.org/project/tokenleak/) : `pipx install tokenleak` (ou `uvx tokenleak`).

Options : `--since 7d|30d|all`, `--here` (ce dossier), `--current` (dernière session), `--json`, `--share` (carte anonymisée à partager), `--redact` (masque commandes, chemins et projets). Ou demande simplement à ton agent : *« audite mes fuites de tokens »*.

Tout reste sur ta machine : aucun accès réseau, aucune télémétrie.

## Benchmark

Voir [la section Benchmark du README anglais](README.md#benchmark) : méthode, chiffres bruts et limites.

Licence MIT.
