# Rulix Espanso

Snippets Espanso pour citer rapidement les principales lois fédérales suisses et quelques conventions internationales, avec liens Fedlex officiels.

## Installation rapide

Copier le script et le ou les fichiers de langue voulus dans la configuration Espanso :

```sh
cp espanso/scripts/rulix_fedlex.rb "$HOME/Library/Application Support/espanso/scripts/"
cp espanso/scripts/rulix_cantonal.rb "$HOME/Library/Application Support/espanso/scripts/"
cp espanso/match/rulix-fedlex-fr.yml "$HOME/Library/Application Support/espanso/match/"
cp espanso/match/rulix-cantonal-fr.yml "$HOME/Library/Application Support/espanso/match/"
espanso service restart
```

Pour l'allemand, copier aussi `rulix-fedlex-de.yml`. Pour l'italien, copier aussi `rulix-fedlex-it.yml`.

## Utilisation

- Français : `$rs` ouvre le menu des lois, `rscc` insère la citation du Code civil, `cc176 ` insère `art. 176 CC` avec un lien Fedlex.
- Allemand : `$sr` ouvre le menu, `srzgb` insère la citation du ZGB, `zgb176 ` insère `Art. 176 ZGB` avec un lien Fedlex.
- Italien : `$rsi` ouvre le menu, `rsitcc` insère la citation du CC, `cc176 ` insère `art. 176 CC` avec un lien Fedlex.

Les références d'article acceptent aussi les suffixes usuels :

- `cc176i ` -> art. 176 al. 1 CC
- `cc176ib ` -> art. 176 al. 1 let. b CC
- `cc176i1 ` -> art. 176 al. 1 ch. 1 CC

Les liens pointent vers l'article, pas vers l'alinéa.

## Législation cantonale GE/VD/VS

Le fichier `rulix-cantonal-fr.yml` ajoute les textes cantonaux genevois, vaudois et valaisans dotés d'un sigle.

Exemples :

- `rsvslacc` -> citation complète de la LACC valaisanne avec lien RS/VS.
- `vslacc1i ` -> `art. 1 al. 1 LACC/VS` avec lien vers l'acte officiel.
- `rsgelacc` / `gelacc1i ` fonctionnent selon le même principe pour Genève, avec les clés générées depuis les sigles officiels.
- `$rsc` ouvre un menu de recherche dans les textes cantonaux.

Les sites cantonaux ne fournissent pas tous des ancres d'article stables. Les références d'article cantonales lient donc vers l'acte officiel, plutôt que vers une ancre fragile.

## Structure

- `espanso/match/rulix-fedlex-fr.yml` : snippets français.
- `espanso/match/rulix-fedlex-de.yml` : snippets allemands.
- `espanso/match/rulix-fedlex-it.yml` : snippets italiens.
- `espanso/scripts/rulix_fedlex.rb` : moteur local pour les citations et références d'articles fédérales.
- `espanso/scripts/rulix_cantonal.rb` : moteur local pour les citations et références d'articles cantonales.
- `data/laws.psv` : table source fédérale éditable.
- `data/cantonal_laws.psv` : table source cantonale éditable.

## Sources

Les URLs vont vers Fedlex officiel. La structure de données de référence peut être enrichie depuis le dépôt public [`droid-f/fedlex`](https://github.com/droid-f/fedlex), qui publie des métadonnées Fedlex en dépôt Git, notamment `eli/cc`, `eli/treaty` et les expressions multilingues. Fedlex expose aussi ses métadonnées en RDF/SPARQL via `fedlex.data.admin.ch`.

## Licence

CC BY-NC-SA 4.0. Voir `LICENSE`.

Les métadonnées Fedlex et les intitulés légaux doivent être vérifiés avant usage sensible. Ce dépôt fournit une base de travail pratique pour Espanso, pas une garantie d'exhaustivité juridique.
