# Rulix Espanso

Snippets Espanso pour citer rapidement les principales lois fédérales suisses, des conventions internationales et les législations cantonales suisses dotées d'un sigle, avec liens vers les sources officielles quand elles sont disponibles.

## Installation rapide

Copier le script et le ou les fichiers de langue voulus dans la configuration Espanso :

```sh
cp espanso/scripts/rulix_fedlex.rb "$HOME/Library/Application Support/espanso/scripts/"
cp espanso/scripts/rulix_cantonal.rb "$HOME/Library/Application Support/espanso/scripts/"
cp espanso/match/rulix-fedlex-fr.yml "$HOME/Library/Application Support/espanso/match/"
cp espanso/match/rulix-cantonal-fr.yml "$HOME/Library/Application Support/espanso/match/"
espanso service restart
```

Pour l'allemand fédéral, copier aussi `rulix-fedlex-de.yml`. Pour l'italien fédéral, copier aussi `rulix-fedlex-it.yml`. Pour les snippets cantonaux alémaniques, copier `rulix-cantonal-de.yml`; il est séparé volontairement pour ne pas l'activer sur les postes francophones.

## Utilisation fédérale

- Français : `$rs` ouvre le menu des lois, `rscc` insère la citation du Code civil, `cc176 ` insère `art. 176 CC` avec un lien Fedlex.
- Allemand : `$sr` ouvre le menu, `srzgb` insère la citation du ZGB, `zgb176 ` insère `Art. 176 ZGB` avec un lien Fedlex.
- Italien : `$rsi` ouvre le menu, `rsitcc` insère la citation du CC, `cc176 ` insère `art. 176 CC` avec un lien Fedlex.

Les références d'article acceptent aussi les suffixes usuels :

- `cc176i ` -> art. 176 al. 1 CC
- `cc176ib ` -> art. 176 al. 1 let. b CC
- `cc176i1 ` -> art. 176 al. 1 ch. 1 CC

Les liens pointent vers l'article, pas vers l'alinéa.

## Utilisation cantonale

`rulix-cantonal-fr.yml` expose les textes cantonaux des 26 cantons dans une interface francophone. Les textes disponibles seulement en allemand ou en italien gardent leur titre original, mais les formules générées restent en style français.

`rulix-cantonal-de.yml` expose les textes cantonaux disponibles en allemand avec une interface et des références allemandes.

Exemples français :

- `$rsc` ouvre un menu de recherche dans les textes cantonaux.
- `rsvslacc` -> citation complète de la LACC valaisanne avec lien RS/VS.
- `vslacc1i ` -> `art. 1 al. 1 LACC/VS` avec lien vers l'acte officiel.
- `rsvdcstvd` -> citation complète de la Constitution vaudoise avec lien BLV.
- `vdcstvd1i ` -> `art. 1 al. 1 Cst-VD/VD` avec lien vers l'acte officiel.

Exemples allemands :

- `$src` ouvre le menu cantonal allemand.
- `srbehg` -> citation complète de la loi bernoise `HG/BE`.
- `bevrpg12iia3 ` -> `Art. 12 Abs. 2 lit. a Ziff. 3 VRPG/BE` avec lien vers l'acte officiel.

Les sites cantonaux ne fournissent pas tous des ancres d'article stables. Les références d'article cantonales ajoutent une ancre `#art_N` quand elle est plausible, mais le lien reste principalement un lien vers l'acte officiel.

## Structure

- `espanso/match/rulix-fedlex-fr.yml` : snippets fédéraux français.
- `espanso/match/rulix-fedlex-de.yml` : snippets fédéraux allemands.
- `espanso/match/rulix-fedlex-it.yml` : snippets fédéraux italiens.
- `espanso/match/rulix-cantonal-fr.yml` : snippets cantonaux tous cantons, interface française.
- `espanso/match/rulix-cantonal-de.yml` : snippets cantonaux alémaniques, interface allemande.
- `espanso/scripts/rulix_fedlex.rb` : moteur local pour les citations et références d'articles fédérales.
- `espanso/scripts/rulix_cantonal.rb` : moteur local pour les citations et références d'articles cantonales.
- `data/laws.psv` : table source fédérale éditable.
- `data/cantonal_laws.psv` : table source cantonale générée.
- `scripts/update_cantonal_laws.py` : génération des données cantonales et des fichiers Espanso.

## Sources

Les URLs fédérales vont vers Fedlex officiel. La structure de données fédérale peut être enrichie depuis le dépôt public [`droid-f/fedlex`](https://github.com/droid-f/fedlex), qui publie des métadonnées Fedlex en dépôt Git, notamment `eli/cc`, `eli/treaty` et les expressions multilingues. Fedlex expose aussi ses métadonnées en RDF/SPARQL via `fedlex.data.admin.ch`.

Les URLs cantonales sont construites depuis les portails officiels cantonaux disponibles, notamment les API LexWork/Clex, le SIL genevois, la BLV vaudoise, LexVS et les portails officiels spécialisés. Le générateur utilise aussi le jeu de données [`voilaj/swiss-legislation`](https://huggingface.co/datasets/voilaj/swiss-legislation), issu du pipeline OpenCaseLaw, comme fallback pour les cantons qui ne publient pas d'index exploitable avec sigles.

## Licence

CC BY-NC-SA 4.0. Voir `LICENSE`.

Les métadonnées Fedlex/cantonales et les intitulés légaux doivent être vérifiés avant usage sensible. Ce dépôt fournit une base de travail pratique pour Espanso, pas une garantie d'exhaustivité juridique.
