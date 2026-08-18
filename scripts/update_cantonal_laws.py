#!/usr/bin/env python3
"""Refresh Rulix Espanso cantonal legislation snippets from official GE/VD/VS sources."""
from pathlib import Path
from html import unescape
import csv
import json
import os
import re
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'ge': 'https://silgeneve.ch/legis/program/books/rsg/toc.htm?app=SIL',
    'vd': 'https://prestations.vd.ch/pub/blv-publication/api/actes/rechercher?keyword=&textes=ABREVIATION&textes=COTE&textes=TITRE&statuts=EN_VIGUEUR&importances=MAJEUR&categories=CONSOLIDE&sortBy=COTE',
    'vs': 'https://lex.vs.ch/api/fr/texts_of_law/lightweight_index?show_abrogated=false',
}
HEADERS = {'User-Agent': 'Mozilla/5.0'}


def fetch_text(url, encoding='utf-8'):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as response:
        data = response.read()
    return data.decode(encoding, errors='ignore')


def clean_html_text(value):
    value = unescape(value)
    value = re.sub(r'<[^>]+>', ' ', value)
    value = value.replace('\xa0', ' ')
    return ' '.join(value.split())


def normalize_key(value):
    return re.sub(r'[^a-z0-9]', '', value.lower())


def is_acronym(value):
    if not value:
        return False
    value = value.strip()
    if len(value) < 2 or len(value) > 28:
        return False
    letters = re.findall(r'[A-Za-zÀ-ÖØ-öø-ÿ]', value)
    if not letters:
        return False
    uppers = re.findall(r'[A-ZÀ-ÖØ-Þ]', value)
    ratio = len(uppers) / len(letters)
    return ratio >= 0.45 or ('-' in value and re.match(r'^[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ0-9.-]+(?:-[A-Za-zÀ-ÖØ-öø-ÿ0-9.-]+)+$', value))


def parse_ge(html):
    pattern = re.compile(r'<a href="(?P<href>htm/rsg_[^"]+\.htm)">(?P<num>.*?)</a>(?P<body>.*?)(?=<a href="htm/rsg_|</body>)', re.S | re.I)
    rows = []
    for match in pattern.finditer(html.replace('\r', '')):
        rs = clean_html_text(match.group('num'))
        body = clean_html_text(match.group('body'))
        abbrs = re.findall(r'\(([^()]{2,40})\)', body)
        if not abbrs:
            continue
        abbr = abbrs[-1].strip()
        if not is_acronym(abbr):
            continue
        title = re.sub(r'\s+\d{2}\.\d{2}\.\d{4}.*$', '', body).strip()
        title = re.sub(r'\s*\(' + re.escape(abbr) + r'\)\s*$', '', title).strip()
        if title:
            rows.append({'canton': 'ge', 'abbr': abbr, 'rs': rs, 'title': title, 'url': 'https://silgeneve.ch/legis/program/books/rsg/' + match.group('href'), 'source': 'rsGE table systématique'})
    return rows


def parse_vd(data):
    rows = []
    for item in data:
        abbr = (item.get('abreviation') or '').strip()
        if not is_acronym(abbr):
            continue
        title = (item.get('titreCompletSansCote') or item.get('titreComplet') or item.get('titre') or '').replace('\xa0', ' ')
        title = re.sub(r'\s*\(' + re.escape(abbr) + r'\)\s*$', '', title).strip()
        title = re.sub(r'\s*\(' + re.escape(abbr) + r';\s*BLV\s+[^)]*\)\s*$', '', title).strip()
        title = ' '.join(title.split())
        cote = item.get('cote') or item.get('code')
        if title and cote:
            rows.append({'canton': 'vd', 'abbr': abbr, 'rs': cote, 'title': title, 'url': f"https://prestations.vd.ch/pub/blv-publication/actes/consolide/{cote}/?id={item.get('id')}", 'source': 'BLV actes majeurs en vigueur'})
    return rows


def parse_vs(index):
    rows = []
    for section_items in index.values():
        for item in section_items:
            title = item.get('title') or ''
            matches = re.findall(r'\(([^()]{2,40})\)\s*$', title)
            if not matches:
                continue
            abbr = matches[-1].strip()
            if not is_acronym(abbr):
                continue
            clean_title = re.sub(r'\s*\(' + re.escape(abbr) + r'\)\s*$', '', title).strip()
            rows.append({'canton': 'vs', 'abbr': abbr, 'rs': item.get('systematic_number'), 'title': ' '.join(clean_title.split()), 'url': f"https://lex.vs.ch/app/fr/texts_of_law/{item.get('systematic_number')}", 'source': 'LexVS lightweight_index'})
    return rows


def collect_rows():
    ge_html = fetch_text(SOURCES['ge'], encoding='cp1252')
    vd_json = json.loads(fetch_text(SOURCES['vd']))
    vs_json = json.loads(fetch_text(SOURCES['vs']))
    rows = parse_ge(ge_html) + parse_vd(vd_json) + parse_vs(vs_json)
    seen = set()
    unique = []
    for row in rows:
        sig = (row['canton'], row['abbr'], row['rs'])
        if sig in seen:
            continue
        seen.add(sig)
        unique.append(row)
    counts = {}
    for row in unique:
        counts[(row['canton'], normalize_key(row['abbr']))] = counts.get((row['canton'], normalize_key(row['abbr'])), 0) + 1
    for row in unique:
        base = normalize_key(row['abbr'])
        row['key'] = base if counts[(row['canton'], base)] == 1 else base + normalize_key(row['rs'])
    return sorted(unique, key=lambda r: (r['canton'], r['key'], r['rs']))


def write_psv(rows):
    path = ROOT / 'data/cantonal_laws.psv'
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['canton', 'key', 'abbr', 'rs', 'title', 'url', 'source'], delimiter='|', lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    return path


def json_scalar(value):
    return json.dumps(value, ensure_ascii=False)


def citation_for(row):
    rs_label = {'ge': 'rs/GE', 'vd': 'BLV', 'vs': 'RS/VS'}[row['canton']]
    suffix = row['canton'].upper()
    return f"{row['title']} (ci-après {row['abbr']}/{suffix}, [{rs_label} {row['rs']}]({row['url']}))"


def write_yaml(rows):
    canton_groups = {'ge': [], 'vd': [], 'vs': []}
    for row in rows:
        canton_groups[row['canton']].append(row)
    lines = ['# Rulix Espanso - législation cantonale GE/VD/VS', '# SPDX-License-Identifier: CC-BY-NC-SA-4.0', 'matches:']
    lines += [f'  - trigger: {json_scalar("$rsc")}', f'    label: {json_scalar("Droit cantonal: choisir une loi")}', '    replace: "{{rulix_cantonal_citation}}"', '    vars:', '      - name: rulix_cantonal_choice', '        type: choice', '        params:', '          values:']
    for row in rows:
        lines.append(f'            - {json_scalar(row["canton"] + "|" + row["key"] + "|" + row["abbr"] + "/" + row["canton"].upper() + " - " + row["title"] + " - " + row["rs"])}')
    lines += ['      - name: rulix_cantonal_citation', '        type: shell', '        params:', f'          cmd: {json_scalar("ruby \\\"$HOME/Library/Application Support/espanso/scripts/rulix_cantonal.rb\\\" citation \\\"{{rulix_cantonal_choice}}\\\"")}', '']
    for canton, sub in canton_groups.items():
        keys_regex = '|'.join(sorted({k for row in sub for k in [row['key'], normalize_key(row['abbr'])]}, key=lambda x: (-len(x), x)))
        pattern = canton + r'(?P<rulix_law>' + keys_regex + r')(?P<rulix_ref>\d+[a-z0-9]*)\s'
        lines += [f'  - regex: {json_scalar(pattern)}', f'    label: {json_scalar("Droit cantonal " + canton.upper() + ": article")}', '    replace: "{{rulix_cantonal_article}}"', '    vars:', '      - name: rulix_cantonal_article', '        type: shell', '        params:', f'          cmd: {json_scalar("ruby \\\"$HOME/Library/Application Support/espanso/scripts/rulix_cantonal.rb\\\" article " + canton + " \\\"{{rulix_law}}\\\" \\\"{{rulix_ref}}\\\"")}', '']
    for row in rows:
        rs_label = {'ge': 'rs/GE', 'vd': 'BLV', 'vs': 'RS/VS'}[row['canton']]
        suffix = row['canton'].upper()
        lines += [f'  - trigger: {json_scalar("rs" + row["canton"] + row["key"])}', f'    label: {json_scalar(rs_label + " " + row["rs"] + " - " + row["abbr"] + "/" + suffix)}', f'    markdown: {json_scalar(citation_for(row))}', '']
    (ROOT / 'espanso/match/rulix-cantonal-fr.yml').write_text('\n'.join(lines), encoding='utf-8')


def main():
    rows = collect_rows()
    write_psv(rows)
    write_yaml(rows)
    print(f"Updated {len(rows)} cantonal laws")


if __name__ == '__main__':
    main()
