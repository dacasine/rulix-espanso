#!/usr/bin/env python3
# Build cantonal Espanso snippets from official cantonal legislation sources.
# German cantonal snippets are written to a separate file so they can remain unused
# on French workstations.
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / 'data' / 'cantonal_laws.psv'
SCRIPT_PATH = ROOT / 'espanso' / 'scripts' / 'rulix_cantonal.rb'
MATCH_DIR = ROOT / 'espanso' / 'match'
HF_CACHE = Path(os.environ.get('RULIX_HF_CACHE', '/tmp/rulix_swiss_legislation_parquet'))
ABBR_CACHE = Path(os.environ.get('RULIX_ABBR_CACHE', '/tmp/rulix_cantonal_abbreviation_cache.json'))
HEADERS = {'User-Agent': 'rulix-espanso/1.0 (+https://github.com/dacasine/rulix-espanso)'}
HF_PARQUET_ENDPOINT = 'https://datasets-server.huggingface.co/parquet?dataset=voilaj%2Fswiss-legislation'

CANTONS = ['AG', 'AI', 'AR', 'BE', 'BL', 'BS', 'FR', 'GE', 'GL', 'GR', 'JU', 'LU', 'NE', 'NW', 'OW', 'SG', 'SH', 'SO', 'SZ', 'TG', 'TI', 'UR', 'VD', 'VS', 'ZG', 'ZH']

COLLECTION_LABELS = {
    ('AG', 'fr'): 'RS/AG', ('AG', 'de'): 'SAR',
    ('AI', 'fr'): 'RS/AI', ('AI', 'de'): 'GS/AI',
    ('AR', 'fr'): 'RS/AR', ('AR', 'de'): 'bGS/AR',
    ('BE', 'fr'): 'RS/BE', ('BE', 'de'): 'BSG',
    ('BL', 'fr'): 'RS/BL', ('BL', 'de'): 'SGS/BL',
    ('BS', 'fr'): 'RS/BS', ('BS', 'de'): 'SG/BS',
    ('FR', 'fr'): 'RSF', ('FR', 'de'): 'SGF',
    ('GE', 'fr'): 'rs/GE', ('GE', 'de'): 'rs/GE',
    ('GL', 'fr'): 'RS/GL', ('GL', 'de'): 'GS/GL',
    ('GR', 'fr'): 'RS/GR', ('GR', 'de'): 'BR/GR',
    ('JU', 'fr'): 'RSJU', ('JU', 'de'): 'RSJU',
    ('LU', 'fr'): 'RS/LU', ('LU', 'de'): 'SRL',
    ('NE', 'fr'): 'RSN', ('NE', 'de'): 'RSN',
    ('NW', 'fr'): 'RS/NW', ('NW', 'de'): 'NG/NW',
    ('OW', 'fr'): 'RS/OW', ('OW', 'de'): 'GDB/OW',
    ('SG', 'fr'): 'RS/SG', ('SG', 'de'): 'sGS',
    ('SH', 'fr'): 'RS/SH', ('SH', 'de'): 'SHR',
    ('SO', 'fr'): 'RS/SO', ('SO', 'de'): 'BGS',
    ('SZ', 'fr'): 'RS/SZ', ('SZ', 'de'): 'SRSZ',
    ('TG', 'fr'): 'RS/TG', ('TG', 'de'): 'RB/TG',
    ('TI', 'fr'): 'RS/TI', ('TI', 'de'): 'RL/TI',
    ('UR', 'fr'): 'RS/UR', ('UR', 'de'): 'RB/UR',
    ('VD', 'fr'): 'BLV', ('VD', 'de'): 'BLV',
    ('VS', 'fr'): 'RS/VS', ('VS', 'de'): 'SGS/VS',
    ('ZG', 'fr'): 'RS/ZG', ('ZG', 'de'): 'BGS/ZG',
    ('ZH', 'fr'): 'RS/ZH', ('ZH', 'de'): 'LS/ZH',
}

OFFICIAL_INDEXES = {
    ('AG', 'de'): 'https://gesetzessammlungen.ag.ch/api/de/texts_of_law/lightweight_index?show_abrogated=false',
    ('AI', 'de'): 'https://ai.clex.ch/api/de/texts_of_law/lightweight_index?show_abrogated=false',
    ('AR', 'de'): 'https://ar.clex.ch/api/de/texts_of_law/lightweight_index?show_abrogated=false',
    ('BE', 'de'): 'https://www.belex.sites.be.ch/api/de/texts_of_law/lightweight_index?show_abrogated=false',
    ('BL', 'de'): 'https://bl.clex.ch/api/de/texts_of_law/lightweight_index?show_abrogated=false',
    ('BS', 'de'): 'https://www.gesetzessammlung.bs.ch/api/de/texts_of_law/lightweight_index?show_abrogated=false',
    ('FR', 'fr'): 'https://fr.clex.ch/api/fr/texts_of_law/lightweight_index?show_abrogated=false',
    ('FR', 'de'): 'https://fr.clex.ch/api/de/texts_of_law/lightweight_index?show_abrogated=false',
    ('GL', 'de'): 'https://gl.clex.ch/api/de/texts_of_law/lightweight_index?show_abrogated=false',
    ('GR', 'de'): 'https://www.gr-lex.gr.ch/api/de/texts_of_law/lightweight_index?show_abrogated=false',
    ('LU', 'de'): 'https://srl.lu.ch/api/de/texts_of_law/lightweight_index?show_abrogated=false',
    ('NW', 'de'): 'https://nw.clex.ch/api/de/texts_of_law/lightweight_index?show_abrogated=false',
    ('OW', 'de'): 'https://ow.clex.ch/api/de/texts_of_law/lightweight_index?show_abrogated=false',
    ('SG', 'de'): 'https://www.gesetzessammlung.sg.ch/api/de/texts_of_law/lightweight_index?show_abrogated=false',
    ('SH', 'de'): 'https://sh.clex.ch/api/de/texts_of_law/lightweight_index?show_abrogated=false',
    ('SO', 'de'): 'https://bgs.so.ch/api/de/texts_of_law/lightweight_index?show_abrogated=false',
    ('TG', 'de'): 'https://www.rechtsbuch.tg.ch/api/de/texts_of_law/lightweight_index?show_abrogated=false',
    ('UR', 'de'): 'https://rechtsbuch.ur.ch/api/de/texts_of_law/lightweight_index?show_abrogated=false',
    ('VS', 'fr'): 'https://lex.vs.ch/api/fr/texts_of_law/lightweight_index?show_abrogated=false',
    ('VS', 'de'): 'https://vs.clex.ch/api/de/texts_of_law/lightweight_index?show_abrogated=false',
    ('ZG', 'de'): 'https://zg.clex.ch/api/de/texts_of_law/lightweight_index?show_abrogated=false',
}

GE_TOC = 'https://silgeneve.ch/legis/program/books/rsg/toc.htm?app=SIL'
VD_API = 'https://prestations.vd.ch/pub/blv-publication/api/actes/rechercher?' + urllib.parse.urlencode({
    'textes': ['ABREVIATION', 'COTE', 'TITRE'],
    'statuts': ['EN_VIGUEUR'],
    'importances': ['MAJEUR'],
    'categories': ['CONSOLIDE'],
    'sortBy': 'COTE',
    'sortOrder': 'asc',
}, doseq=True)

ACRONYM_EXTRACTION_RE = re.compile(r'\(([^()]{2,80})\)\s*$')
ACRONYM_CHARS_RE = re.compile(r'^[A-Za-zÀ-ÖØ-Þ0-9][A-Za-zÀ-ÖØ-Þ0-9./& +\-]{1,31}$')

@dataclass
class Law:
    lang: str
    canton: str
    key: str
    abbr: str
    rs: str
    title: str
    url: str
    source: str
    detail_url: str = ''


def fetch_bytes(url: str, timeout: int = 30, limit: int | None = None) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read(limit) if limit else response.read()


def fetch_text(url: str, timeout: int = 30) -> str:
    return fetch_bytes(url, timeout=timeout).decode('utf-8', errors='replace')


def fetch_json(url: str, timeout: int = 30) -> Any:
    return json.loads(fetch_text(url, timeout=timeout))


def clean_html_text(value: Any) -> str:
    value = '' if value is None else str(value)
    value = re.sub(r'<[^>]+>', ' ', value)
    value = html.unescape(value)
    return re.sub(r'\s+', ' ', value).strip(' \t\n\r;,.')


def normalize_key(value: str) -> str:
    table = str.maketrans({
        'à': 'a', 'á': 'a', 'â': 'a', 'ä': 'a', 'ã': 'a', 'å': 'a',
        'ç': 'c', 'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e',
        'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i',
        'ñ': 'n', 'ò': 'o', 'ó': 'o', 'ô': 'o', 'ö': 'o', 'õ': 'o',
        'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u', 'ý': 'y', 'ÿ': 'y',
        'æ': 'ae', 'œ': 'oe', 'ß': 'ss',
    })
    lowered = value.lower().translate(table)
    return re.sub(r'[^a-z0-9]+', '', lowered)


def is_acronym(value: str) -> bool:
    value = value.strip()
    if len(value) < 2 or len(value) > 32:
        return False
    if re.fullmatch(r'\d{3,4}', value):
        return False
    if not ACRONYM_CHARS_RE.match(value):
        return False
    letters = re.findall(r'[A-Za-zÀ-ÖØ-Þ]', value)
    if not letters:
        return False
    uppercase = sum(1 for char in letters if char.upper() == char and char.lower() != char)
    return uppercase / len(letters) >= 0.35


def best_acronym_from_text(text: str) -> str:
    text = clean_html_text(text)
    matches = list(re.finditer(r'\(([^()]{2,80})\)', text))
    if not matches:
        return ''
    candidates: list[str] = []
    for chunk in reversed(matches):
        parts = re.split(r'\s*(?:,|;|/|\bou\b|\boder\b|\bo\b)\s*', chunk.group(1))
        candidates.extend(part.strip() for part in parts)
    for candidate in candidates:
        candidate = candidate.strip(' .;:,')
        if is_acronym(candidate):
            return candidate
    return ''


def strip_trailing_acronym(title: str, abbr: str) -> str:
    if abbr:
        title = re.sub(rf'\s*\({re.escape(abbr)}\)\s*,?', '', title, count=1).strip()
    else:
        title = re.sub(r'\s*\([^()]{2,80}\)\s*$', '', title).strip()
    return clean_html_text(title)


def collection_label(canton: str, lang: str) -> str:
    return COLLECTION_LABELS.get((canton, lang)) or COLLECTION_LABELS.get((canton, 'fr')) or f'RS/{canton}'


def official_app_url(index_url: str, lang: str, rs: str) -> str:
    parsed = urllib.parse.urlparse(index_url)
    return f'{parsed.scheme}://{parsed.netloc}/app/{lang}/texts_of_law/{urllib.parse.quote(rs, safe="")}'


def detail_api_url(index_url: str, lang: str, rs: str) -> str:
    parsed = urllib.parse.urlparse(index_url)
    return f'{parsed.scheme}://{parsed.netloc}/api/{lang}/texts_of_law/{urllib.parse.quote(rs, safe="")}'


def flatten_index_payload(payload: Any) -> Iterable[dict[str, Any]]:
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                yield item
        return
    if isinstance(payload, dict):
        for key in ('texts_of_law', 'laws', 'items', 'content', 'results', 'data'):
            value = payload.get(key)
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        yield item
                return
        for value in payload.values():
            if isinstance(value, dict):
                yield from flatten_index_payload(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        yield item


def first_present(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, ''):
            return clean_html_text(value)
    return ''


def parse_official_index(canton: str, lang: str, index_url: str, url_fallbacks: dict[tuple[str, str, str], str]) -> list[Law]:
    payload = fetch_json(index_url)
    laws: list[Law] = []
    for row in flatten_index_payload(payload):
        if row.get('abrogated') is True or row.get('is_abrogated') is True:
            continue
        rs = first_present(row, 'rsNumber', 'srNumber', 'rs_number', 'number', 'systematicNumber', 'systematic_number', 'id')
        title = first_present(row, 'title', 'lawTitle', 'law_title', 'name', 'shortTitle', 'longTitle')
        if not rs or not title:
            continue
        abbr = first_present(row, 'abbreviation', 'abbr', 'shortName', 'short_name', 'acronym') or best_acronym_from_text(title)
        url = first_present(row, 'canonicalLink', 'canonical_link', 'url', 'htmlUrl', 'html_url')
        if not url:
            url = url_fallbacks.get((canton, lang, rs), '') or official_app_url(index_url, lang, rs)
        laws.append(Law(lang, canton, '', abbr, rs, strip_trailing_acronym(title, abbr), url, 'official', detail_api_url(index_url, lang, rs)))
    return laws


def parse_ge() -> list[Law]:
    text = fetch_text(GE_TOC)
    pattern = re.compile(r'<tr>.*?<td[^>]*>(.*?)</td>.*?<td[^>]*>(.*?)</td>.*?<a\s+href="([^"]+)"[^>]*>(.*?)</a>.*?</tr>', re.S | re.I)
    laws: list[Law] = []
    for rs_html, abbr_html, href, title_html in pattern.findall(text):
        rs = clean_html_text(rs_html)
        abbr = clean_html_text(abbr_html)
        title = clean_html_text(title_html)
        if not rs or not title or not is_acronym(abbr):
            continue
        url = urllib.parse.urljoin(GE_TOC, html.unescape(href))
        laws.append(Law('fr', 'GE', '', abbr, rs, strip_trailing_acronym(title, abbr), url, 'official'))
    return laws


def parse_vd() -> list[Law]:
    payload = fetch_json(VD_API)
    items = payload.get('content') if isinstance(payload, dict) else payload
    laws: list[Law] = []
    for row in items or []:
        if not isinstance(row, dict):
            continue
        rs = first_present(row, 'cote', 'numRs', 'numRS', 'rsNumber', 'numeroRS')
        abbr = first_present(row, 'abreviation', 'sigle', 'abrev', 'abbreviation')
        title = first_present(row, 'titreCompletSansCote', 'titreComplet', 'titreActeLegislatifComplet', 'titreActeLegislatifCourt', 'titre')
        uuid = row.get('id') or row.get('uuid')
        if not rs or not title or not is_acronym(abbr):
            continue
        url = f'https://prestations.vd.ch/pub/blv-publication/actes/consolide/{rs}?id={uuid}' if uuid else f'https://prestations.vd.ch/pub/blv-publication/actes/consolide/{rs}'
        laws.append(Law('fr', 'VD', '', abbr, rs, strip_trailing_acronym(title, abbr), url, 'official'))
    return laws


def download_hf_parquets() -> list[Path]:
    HF_CACHE.mkdir(parents=True, exist_ok=True)
    index = fetch_json(HF_PARQUET_ENDPOINT)
    files: list[Path] = []
    for item in index.get('parquet_files', []):
        if item.get('config') != 'cantonal':
            continue
        url = item.get('url')
        filename = item.get('filename') or os.path.basename(urllib.parse.urlparse(url).path)
        if not url or not filename:
            continue
        dest = HF_CACHE / filename
        if not dest.exists() or dest.stat().st_size == 0:
            print(f'download {filename}', file=sys.stderr)
            dest.write_bytes(fetch_bytes(url, timeout=90))
        files.append(dest)
    return sorted(files)


def load_hf_rows() -> list[Law]:
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise SystemExit('pyarrow is required. Install with: python3 -m pip install --target /tmp/rulix_pydeps pyarrow') from exc
    laws_by_key: dict[tuple[str, str, str, str], Law] = {}
    columns = ['canton', 'sr_number', 'law_title', 'language', 'is_active', 'original_url']
    for path in download_hf_parquets():
        table = pq.read_table(path, columns=columns)
        for row in table.to_pylist():
            if row.get('is_active') is False:
                continue
            canton = (row.get('canton') or '').upper()
            lang = (row.get('language') or '').lower()
            rs = clean_html_text(row.get('sr_number'))
            title = clean_html_text(row.get('law_title'))
            if canton not in CANTONS or lang not in {'fr', 'de', 'it'} or not rs or not title:
                continue
            identity = (lang, canton, rs, title)
            if identity in laws_by_key:
                continue
            abbr = best_acronym_from_text(title)
            laws_by_key[identity] = Law(lang, canton, '', abbr, rs, strip_trailing_acronym(title, abbr), row.get('original_url') or '', 'opencaselaw')
    return list(laws_by_key.values())


def decode_json_string_literal(value: str) -> str:
    try:
        return json.loads('"' + value + '"')
    except json.JSONDecodeError:
        return value


def fetch_detail_abbreviation(law: Law) -> str:
    if not law.detail_url:
        return ''
    try:
        raw = fetch_bytes(law.detail_url, timeout=30, limit=90000).decode('utf-8', errors='replace')
    except Exception:
        return ''
    match = re.search(r'"abbreviation"\s*:\s*"((?:\\.|[^"\\])*)"', raw)
    if match:
        value = decode_json_string_literal(match.group(1)).strip()
        if is_acronym(value):
            return value
    return best_acronym_from_text(raw[:25000])


def enrich_abbreviations(laws: list[Law], deep: bool) -> None:
    if not deep:
        return
    cache: dict[str, str] = {}
    if ABBR_CACHE.exists():
        try:
            cache = json.loads(ABBR_CACHE.read_text())
        except json.JSONDecodeError:
            cache = {}
    targets = [law for law in laws if not is_acronym(law.abbr) and law.detail_url]
    print(f'enrich abbreviations: {len(targets)} detail pages', file=sys.stderr)
    changed = False
    def key_for(law: Law) -> str:
        return f'{law.lang}|{law.canton}|{law.rs}'
    uncached = [law for law in targets if key_for(law) not in cache]
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_map = {executor.submit(fetch_detail_abbreviation, law): law for law in uncached}
        for index, future in enumerate(concurrent.futures.as_completed(future_map), 1):
            law = future_map[future]
            try:
                cache[key_for(law)] = future.result()
            except Exception:
                cache[key_for(law)] = ''
            changed = True
            if index % 250 == 0:
                print(f'  {index}/{len(uncached)} detail pages', file=sys.stderr)
    for law in targets:
        value = cache.get(key_for(law), '')
        if is_acronym(value):
            law.abbr = value
            law.title = strip_trailing_acronym(law.title, value)
    if changed:
        ABBR_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True) + '\n')


def assign_keys(laws: list[Law]) -> list[Law]:
    grouped: dict[tuple[str, str, str], list[Law]] = {}
    for law in laws:
        base = normalize_key(law.abbr)
        if base:
            grouped.setdefault((law.lang, law.canton, base), []).append(law)
    for (_lang, _canton, base), items in grouped.items():
        items.sort(key=lambda item: (item.rs, item.title))
        if len(items) == 1:
            items[0].key = base
            continue
        seen: set[str] = set()
        for item in items:
            suffix = normalize_key(item.rs.replace('.', '')) or str(len(seen) + 1)
            key = f'{base}{suffix}'
            cursor = 2
            while key in seen:
                key = f'{base}{suffix}{cursor}'
                cursor += 1
            seen.add(key)
            item.key = key
    return [law for law in laws if law.key]


def collect_rows(deep_abbreviations: bool) -> list[Law]:
    hf_laws = load_hf_rows()
    url_fallbacks = {(law.canton, law.lang, law.rs): law.url for law in hf_laws if law.url}
    by_identity: dict[tuple[str, str, str], Law] = {(law.lang, law.canton, law.rs): law for law in hf_laws}
    official_laws: list[Law] = []
    for (canton, lang), url in OFFICIAL_INDEXES.items():
        try:
            rows = parse_official_index(canton, lang, url, url_fallbacks)
            print(f'{canton} {lang}: official {len(rows)} rows', file=sys.stderr)
            official_laws.extend(rows)
        except Exception as exc:
            print(f'{canton} {lang}: official index failed: {exc}', file=sys.stderr)
    for parser, label in ((parse_ge, 'GE fr'), (parse_vd, 'VD fr')):
        try:
            rows = parser()
            print(f'{label}: official {len(rows)} rows', file=sys.stderr)
            official_laws.extend(rows)
        except Exception as exc:
            print(f'{label}: official parser failed: {exc}', file=sys.stderr)
    enrich_abbreviations(official_laws, deep_abbreviations)
    for law in official_laws:
        by_identity[(law.lang, law.canton, law.rs)] = law
    candidates = [law for law in by_identity.values() if law.canton in CANTONS and law.lang in {'fr', 'de', 'it'} and is_acronym(law.abbr) and law.title and law.rs and law.url]
    candidates = assign_keys(candidates)
    candidates.sort(key=lambda law: (law.lang, law.canton, law.key, law.rs))
    return candidates


def safe_field(value: str) -> str:
    return clean_html_text(value).replace('|', '/').replace('\n', ' ')


def write_psv(laws: list[Law]) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DATA_PATH.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle, delimiter='|', lineterminator='\n')
        writer.writerow(['lang', 'canton', 'key', 'abbr', 'rs', 'title', 'url', 'source'])
        for law in laws:
            writer.writerow([law.lang, law.canton, law.key, law.abbr, law.rs, safe_field(law.title), law.url, law.source])


def ruby_string_literal(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def write_ruby(laws: list[Law]) -> None:
    data_rows = [
        [law.lang, law.canton, law.key, law.abbr, law.rs, safe_field(law.title), law.url, law.source]
        for law in laws
    ]
    ruby = r"""#!/usr/bin/env ruby
# frozen_string_literal: true

require 'json'

DATA_ROWS = JSON.parse(__DATA_ROWS_JSON__)

LAWS = DATA_ROWS.map do |row|
  lang, canton, key, abbr, rs, title, url, source = row
  { lang: lang, canton: canton, key: key, abbr: abbr, rs: rs, title: title, url: url, source: source }
end

LAWS_BY_KEY = LAWS.to_h { |law| [[law[:lang], law[:canton], law[:key]], law] }

COLLECTION_LABELS = {
  ['AG', 'fr'] => 'RS/AG', ['AG', 'de'] => 'SAR',
  ['AI', 'fr'] => 'RS/AI', ['AI', 'de'] => 'GS/AI',
  ['AR', 'fr'] => 'RS/AR', ['AR', 'de'] => 'bGS/AR',
  ['BE', 'fr'] => 'RS/BE', ['BE', 'de'] => 'BSG',
  ['BL', 'fr'] => 'RS/BL', ['BL', 'de'] => 'SGS/BL',
  ['BS', 'fr'] => 'RS/BS', ['BS', 'de'] => 'SG/BS',
  ['FR', 'fr'] => 'RSF', ['FR', 'de'] => 'SGF',
  ['GE', 'fr'] => 'rs/GE', ['GE', 'de'] => 'rs/GE',
  ['GL', 'fr'] => 'RS/GL', ['GL', 'de'] => 'GS/GL',
  ['GR', 'fr'] => 'RS/GR', ['GR', 'de'] => 'BR/GR',
  ['JU', 'fr'] => 'RSJU', ['JU', 'de'] => 'RSJU',
  ['LU', 'fr'] => 'RS/LU', ['LU', 'de'] => 'SRL',
  ['NE', 'fr'] => 'RSN', ['NE', 'de'] => 'RSN',
  ['NW', 'fr'] => 'RS/NW', ['NW', 'de'] => 'NG/NW',
  ['OW', 'fr'] => 'RS/OW', ['OW', 'de'] => 'GDB/OW',
  ['SG', 'fr'] => 'RS/SG', ['SG', 'de'] => 'sGS',
  ['SH', 'fr'] => 'RS/SH', ['SH', 'de'] => 'SHR',
  ['SO', 'fr'] => 'RS/SO', ['SO', 'de'] => 'BGS',
  ['SZ', 'fr'] => 'RS/SZ', ['SZ', 'de'] => 'SRSZ',
  ['TG', 'fr'] => 'RS/TG', ['TG', 'de'] => 'RB/TG',
  ['TI', 'fr'] => 'RS/TI', ['TI', 'de'] => 'RL/TI',
  ['UR', 'fr'] => 'RS/UR', ['UR', 'de'] => 'RB/UR',
  ['VD', 'fr'] => 'BLV', ['VD', 'de'] => 'BLV',
  ['VS', 'fr'] => 'RS/VS', ['VS', 'de'] => 'SGS/VS',
  ['ZG', 'fr'] => 'RS/ZG', ['ZG', 'de'] => 'BGS/ZG',
  ['ZH', 'fr'] => 'RS/ZH', ['ZH', 'de'] => 'LS/ZH'
}

ROMAN_VALUES = {
  'i' => 1, 'ii' => 2, 'iii' => 3, 'iv' => 4, 'v' => 5, 'vi' => 6,
  'vii' => 7, 'viii' => 8, 'ix' => 9, 'x' => 10, 'xi' => 11, 'xii' => 12
}

def collection_label(law, ui_lang)
  COLLECTION_LABELS[[law[:canton], ui_lang]] || COLLECTION_LABELS[[law[:canton], law[:lang]]] || "RS/#{law[:canton]}"
end

def display_law_title(law, ui_lang)
  marker = ui_lang == 'de' ? 'nachfolgend' : 'ci-après'
  "#{law[:title]} (#{marker} #{law[:abbr]}/#{law[:canton]}, [#{collection_label(law, ui_lang)} #{law[:rs]}](#{law[:url]}))"
end

def article_url(law, article)
  base = law[:url].to_s
  anchor = "art_#{article.gsub(/[^0-9A-Za-z]/, '_')}"
  base.include?('#') ? base : base + "##{anchor}"
end

def parse_reference(ref)
  text = ref.to_s.downcase
  article = text[/\A\d+/]
  rest = text[article.length..] || ''
  article_suffix = ''
  paragraph = nil
  letter = nil
  number = nil

  unless rest.empty?
    roman = ROMAN_VALUES.keys.sort_by { |key| -key.length }.find { |roman_key| rest.start_with?(roman_key) }
    if roman
      paragraph = ROMAN_VALUES[roman]
      rest = rest[roman.length..] || ''
    elsif rest =~ /\A[a-z]/
      article_suffix = rest[0]
      rest = rest[1..] || ''
    end
  end

  unless rest.empty?
    roman = ROMAN_VALUES.keys.sort_by { |key| -key.length }.find { |roman_key| rest.start_with?(roman_key) }
    if roman
      paragraph = ROMAN_VALUES[roman]
      rest = rest[roman.length..] || ''
    end
  end

  if rest =~ /\A[a-z]/
    letter = rest[0]
    rest = rest[1..] || ''
  end

  number = rest[/\A\d+/] if rest =~ /\A\d+/
  { article: article + article_suffix, paragraph: paragraph, letter: letter, number: number }
end

def article_label(law, ref, ui_lang)
  parsed = parse_reference(ref)
  parts = []
  if ui_lang == 'de'
    parts << "Art. #{parsed[:article]}"
    parts << "Abs. #{parsed[:paragraph]}" if parsed[:paragraph]
    parts << "lit. #{parsed[:letter]}" if parsed[:letter]
    parts << "Ziff. #{parsed[:number]}" if parsed[:number]
  else
    parts << "art. #{parsed[:article]}"
    parts << "al. #{parsed[:paragraph]}" if parsed[:paragraph]
    parts << "let. #{parsed[:letter]}" if parsed[:letter]
    parts << "ch. #{parsed[:number]}" if parsed[:number]
  end
  [parts.join(' '), "#{law[:abbr]}/#{law[:canton]}"].join(' ')
end

def law_for_any_lang(ui_lang, canton, key)
  LAWS_BY_KEY[[ui_lang, canton, key]] || LAWS.find { |law| law[:canton] == canton && law[:key] == key }
end

command = ARGV.shift
case command
when 'labels'
  ui_lang = ARGV.shift || 'fr'
  rows = LAWS.select { |law| ui_lang == 'de' ? law[:lang] == 'de' : true }
  rows = rows.sort_by { |law| [law[:canton], law[:abbr], law[:rs]] }
  puts rows.map { |law| "#{law[:lang]}|#{law[:canton]}|#{law[:key]}|#{law[:canton]} · #{law[:abbr]} · #{law[:title]} (#{collection_label(law, ui_lang)} #{law[:rs]})" }.join('\n')
when 'citation'
  value = ARGV.join(' ')
  lang, canton, key = value.split('|', 4)
  law = LAWS_BY_KEY[[lang, canton, key]] || law_for_any_lang(lang || 'fr', canton, key)
  abort '' unless law
  puts display_law_title(law, lang || 'fr')
when 'article'
  ui_lang, canton, key, ref = ARGV
  law = law_for_any_lang(ui_lang || 'fr', canton, key)
  abort '' unless law && ref
  parsed = parse_reference(ref)
  puts "[#{article_label(law, ref, ui_lang || 'fr')}](#{article_url(law, parsed[:article])})"
when 'keys'
  ui_lang, canton = ARGV
  keys = LAWS.select { |law| law[:canton] == canton && (ui_lang == 'de' ? law[:lang] == 'de' : true) }.map { |law| law[:key] }.uniq.sort
  puts keys.join('|')
else
  abort 'usage: rulix_cantonal.rb labels|citation|article|keys ...'
end
"""
    ruby = ruby.replace('__DATA_ROWS_JSON__', ruby_string_literal(json.dumps(data_rows, ensure_ascii=False)))
    SCRIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCRIPT_PATH.write_text(ruby, encoding='utf-8')
    SCRIPT_PATH.chmod(0o755)


def yaml_scalar(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def select_for_ui(laws: list[Law], ui_lang: str) -> list[Law]:
    if ui_lang == 'de':
        return [law for law in laws if law.lang == 'de']
    by_canton_rs: dict[tuple[str, str], Law] = {}
    for law in laws:
        key = (law.canton, law.rs)
        existing = by_canton_rs.get(key)
        if law.lang == 'fr' or not existing:
            by_canton_rs[key] = law
    return sorted(by_canton_rs.values(), key=lambda law: (law.canton, law.key, law.rs))


def write_yaml(laws: list[Law], ui_lang: str) -> None:
    selected = select_for_ui(laws, ui_lang)
    trigger_menu = '$src' if ui_lang == 'de' else '$rsc'
    static_prefix = 'sr' if ui_lang == 'de' else 'rs'
    title = 'Rulix cantonal legislation snippets (DE)' if ui_lang == 'de' else 'Rulix références cantonales (FR)'
    lines = [
        '# yaml-language-server: $schema=https://raw.githubusercontent.com/espanso/espanso/dev/schemas/match.schema.json',
        '# Generated by scripts/update_cantonal_laws.py. Do not edit by hand.',
        f'name: {yaml_scalar("rulix-cantonal-" + ui_lang)}',
        f'title: {yaml_scalar(title)}',
        'matches:',
        f'  - trigger: {yaml_scalar(trigger_menu)}',
        '    replace: "{{rulix_cantonal_citation}}"',
        '    vars:',
        '      - name: rulix_cantonal_choice',
        '        type: choice',
        '        params:',
        '          values:',
        f'            - label: {yaml_scalar("Choisir une loi cantonale" if ui_lang == "fr" else "Kantonalen Erlass wählen")}',
        '              id: __noop__',
        '            - type: shell',
        f'              cmd: {yaml_scalar("ruby \"$HOME/Library/Application Support/espanso/scripts/rulix_cantonal.rb\" labels " + ui_lang)}',
        '      - name: rulix_cantonal_citation',
        '        type: shell',
        f'        params:\n          cmd: {yaml_scalar("ruby \"$HOME/Library/Application Support/espanso/scripts/rulix_cantonal.rb\" citation \"{{rulix_cantonal_choice}}\"")}',
    ]
    for law in selected:
        prefix = f'{static_prefix}{law.canton.lower()}{law.key}'
        citation = f'ruby "$HOME/Library/Application Support/espanso/scripts/rulix_cantonal.rb" citation "{law.lang}|{law.canton}|{law.key}"'
        lines.extend([
            f'  - trigger: {yaml_scalar(prefix)}',
            '    replace: "{{output}}"',
            '    vars:',
            '      - name: output',
            '        type: shell',
            f'        params:\n          cmd: {yaml_scalar(citation)}',
        ])
    by_canton: dict[str, list[Law]] = {}
    for law in selected:
        by_canton.setdefault(law.canton, []).append(law)
    for canton in sorted(by_canton):
        keys = sorted({law.key for law in by_canton[canton]})
        if not keys:
            continue
        pattern = f'(?P<rulix_law>{"|".join(re.escape(key) for key in keys)})(?P<rulix_ref>\\d+[a-z0-9]*)\\s'
        trigger = canton.lower() + pattern
        command = f'ruby "$HOME/Library/Application Support/espanso/scripts/rulix_cantonal.rb" article {ui_lang} {canton} "{{{{rulix_law}}}}" "{{{{rulix_ref}}}}"'
        lines.extend([
            f'  - regex: {yaml_scalar(trigger)}',
            '    replace: "{{output}}"',
            '    vars:',
            '      - name: output',
            '        type: shell',
            f'        params:\n          cmd: {yaml_scalar(command)}',
        ])
    (MATCH_DIR / f'rulix-cantonal-{ui_lang}.yml').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def write_outputs(laws: list[Law]) -> None:
    write_psv(laws)
    write_ruby(laws)
    write_yaml(laws, 'fr')
    write_yaml(laws, 'de')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--deep-abbreviations', action='store_true', help='fetch detail pages to extract official abbreviations')
    args = parser.parse_args()
    laws = collect_rows(args.deep_abbreviations)
    write_outputs(laws)
    by_lang = {lang: sum(1 for law in laws if law.lang == lang) for lang in sorted({law.lang for law in laws})}
    by_canton = {canton: sum(1 for law in laws if law.canton == canton) for canton in CANTONS}
    print(f'wrote {len(laws)} cantonal laws: {by_lang}')
    print('by canton: ' + ', '.join(f'{canton}={count}' for canton, count in by_canton.items()))


if __name__ == '__main__':
    main()
