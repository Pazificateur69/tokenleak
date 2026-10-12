<p align="center"><img src="assets/logo.png" width="96" alt="logo tokenleak"></p>

<h1 align="center">tokenleak</h1>

<p align="center"><b>Trouve et colmate les fuites de tokens de ton agent de code.</b><br>
Rien à voir avec des clés API qui fuient : il s'agit des tokens que ton agent IA brûle en contexte inutile.</p>

<p align="center"><a href="README.md">English</a></p>

**−40 % de coût sur un benchmark A/B de 40 runs, même taux de réussite (20/20).** Méthode et limites : [section Benchmark](README.md#benchmark).

## Pourquoi

Dans une boucle d'agent, **chaque résultat d'outil qui entre dans le contexte est renvoyé à chaque appel suivant**, jusqu'à la compaction. Un log de tests de 6k tokens lu à l'appel 5 d'une session de 60 appels est payé ~55 fois de plus. Chaque aller-retour supplémentaire renvoie tout le contexte.

La facture ne dépend donc pas de la longueur des réponses de l'agent, mais de **ce qu'il laisse entrer dans son contexte, et quand**. Raccourcir les réponses économise la partie bon marché ; sur de vraies sessions de code, l'essentiel du coût vient des relectures de contexte.

tokenleak fait deux choses :

1. **Des règles** (un skill d'environ 850 tokens) pour que n'importe quel agent ne laisse entrer que ce dont la prochaine décision a besoin : localiser puis lire, calculer plutôt que lire les données, borner la sortie de chaque commande, ne jamais relire, grouper les appels indépendants, des diffs plutôt que des fichiers, éditer plutôt que réécrire. Avec des garde-fous : jamais d'économie en devinant un fichier ou en sautant une vérification.
2. **Un audit** qui lit *tes* transcripts Claude Code et Codex et montre où sont vraiment partis les tokens : lectures surdimensionnées, logs bavards, appels gaspillés, allers-retours en série. Chacun est chiffré par la **taxe de contexte** qu'il a imposée, avec la règle qui le corrige. Local, lecture seule, zéro dépendance.

## Installation

**Claude Code (plugin, recommandé)** : règles injectées au démarrage, après compaction et dans chaque sous-agent, plus le skill `/tokenleak`.

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
curl -fsSL https://raw.githubusercontent.com/Pazificateur69/tokenleak/main/skills/tokenleak/SKILL.md | awk 'f>=2;/^---$/{f++}' >> AGENTS.md
```

## L'audit

```bash
curl -fsSL https://raw.githubusercontent.com/Pazificateur69/tokenleak/main/skills/tokenleak/scripts/tokenleak.py | python3 - --since 30d
```

Options : `--since 7d|30d|all`, `--here` (ce dossier), `--current` (dernière session), `--json`, `--share` (carte anonymisée à partager), `--redact` (masque commandes, chemins et projets). Ou demande simplement à ton agent : *« audite mes fuites de tokens »*.

Tout reste sur ta machine : aucun accès réseau, aucune télémétrie.

## Benchmark

Voir [la section Benchmark du README anglais](README.md#benchmark) : méthode, chiffres bruts et limites.

Licence MIT.
