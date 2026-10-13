"""Best-effort product-name transliteration, never a database write.

Google Input Tools is unofficial: suggestions always require human review.
Only alphabetic tokens are sent externally, not item IDs/prices/whole records.
"""
import hashlib
import re
from concurrent.futures import ThreadPoolExecutor

import requests
from django.conf import settings
from django.core.cache import cache

LETTERS = dict(zip('ABCDEFGHIJKLMNOPQRSTUVWXYZ', [
    'اے', 'بی', 'سی', 'ڈی', 'ای', 'ایف', 'جی', 'ایچ', 'آئی', 'جے', 'کے', 'ایل',
    'ایم', 'این', 'او', 'پی', 'کیو', 'آر', 'ایس', 'ٹی', 'یو', 'وی', 'ڈبلیو', 'ایکس', 'وائی', 'زیڈ',
]))
GLOSSARY = {'LIGHT': 'لائٹ', 'PANEL': 'پینل', 'WAY': 'وے', 'BULB': 'بلب',
            'OSAKA': 'اوساکا', 'SWITCH': 'سوئچ', 'SOCKET': 'ساکٹ', 'WIRE': 'وائر',
            'CABLE': 'کیبل', 'FAN': 'فین', 'BOX': 'باکس', 'GANG': 'گینگ',
            'DIMMER': 'ڈمر', 'HOLDER': 'ہولڈر'}
TOKEN = re.compile(r'[A-Za-z0-9]+')
URDU = re.compile(r'[\u0600-\u06ff]')


def glossary():
    return {**GLOSSARY, **{str(k).upper(): str(v) for k, v in
                         getattr(settings, 'INVENTORY_URDU_GLOSSARY', {}).items()}}


def parts(token, known):
    # Keep mixed model codes/wattages intact: O12, A12B, 12W, 24V, IP65.
    # Numeric prefixes on recognizable words: 24WAY, 3LIGHT, 3VM.
    prefix = re.fullmatch(r'(\d+)([A-Za-z]{2,})', token)
    if prefix:
        number, word = prefix.groups()
        if word.upper() in known or len(word) > 3 or word.upper() in ('VM', 'SR'):
            return number + '-', word
    if re.fullmatch('[A-Za-z]+', token):
        return '', token
    return '', None


def local_word(word, known):
    if word.upper() in known:
        return known[word.upper()]
    if len(word) <= 3 and word.isupper():
        return ' '.join(LETTERS[c] for c in word) + f' ({word})'
    return None


def provider_word(word):
    key = 'inventory-urdu:v1:' + hashlib.sha256(word.lower().encode()).hexdigest()
    cached = cache.get(key)
    if cached:
        return cached
    try:
        response = requests.get(
            'https://inputtools.google.com/request',
            params={'itc': 'ur-t-i0-und', 'num': 1, 'cp': 0, 'cs': 1, 'ie': 'utf-8',
                    'oe': 'utf-8', 'app': 'demopage', 'text': word.lower()},
            timeout=(3, 5), allow_redirects=False,
        )
        response.raise_for_status()
        data = response.json()
        candidate = data[1][0][1][0] if data[0] == 'SUCCESS' else None
        if not isinstance(candidate, str) or len(candidate) > 200 or not URDU.search(candidate):
            return None
        cache.set(key, candidate, 60 * 60 * 24 * 7)
        return candidate
    except (requests.RequestException, ValueError, IndexError, KeyError, TypeError):
        return None


def suggest_names(names):
    known = glossary()
    unknown = set()
    for name in names:
        for token in TOKEN.findall(name):
            _, word = parts(token, known)
            if word and local_word(word, known) is None:
                unknown.add(word.lower())
    if len(unknown) > 30:
        raise ValueError('Too many different words. Select fewer or shorter item names.')
    # Bounded parallelism and token deduplication; failures are never cached.
    with ThreadPoolExecutor(max_workers=4) as pool:
        translated = dict(zip(sorted(unknown), pool.map(provider_word, sorted(unknown))))
    results = []
    for name in names:
        missing = set()

        def replace(match):
            token = match.group()
            prefix, word = parts(token, known)
            if word is None:
                return token
            value = local_word(word, known)
            if value is None:
                value = translated.get(word.lower())
            if not value:
                missing.add(word)
                return token
            return prefix + value

        suggestion = TOKEN.sub(replace, name)
        suggestion = re.sub(r'\s+', ' ', suggestion.replace('+', ' + ')).strip()
        usable = not missing and bool(URDU.search(suggestion)) and len(suggestion) <= 500
        results.append({'source': name, 'suggestion': suggestion if usable else None,
                        'error': ('Provider unavailable or returned no Urdu for: ' + ', '.join(sorted(missing))) if missing
                        else ('' if usable else 'No Urdu suggestion, or result exceeds 500 characters.')})
    return results