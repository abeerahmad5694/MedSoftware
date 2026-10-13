import re
import requests
from deep_translator import GoogleTranslator

# This Google API is free, no key needed
def transliterate_word(word):
    """ LIGHT -> لائٹ, PANEL -> پینل """
    if not word or len(word) <= 2: # Don't translate SR, VM, DB etc
        return f"{transliterate_abbr(word)} ({word})" if word.isalpha() else word

    try:
        # itc=ur-t-i0-und is Urdu transliteration
        url = "https://inputtools.google.com/request"
        params = {
            "itc": "ur-t-i0-und",
            "num": 1,
            "cp": 0, "cs": 1, "ie": "utf-8", "oe": "utf-8",
            "app": "demopage",
            "text": word.lower()
        }
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
        # response is like [[ "light", ["لائٹ"] ]]
        if data[0] == "SUCCESS":
            return data[1][0][1][0]
    except:
        pass

    # fallback to Google Translator if transliteration fails
    try:
        return GoogleTranslator(source='en', target='ur').translate(word)
    except:
        return word

def transliterate_abbr(abbr):
    # VM -> وی ایم, SR -> ایس آر
    map_abbr = {
        'A':'اے','B':'بی','C':'سی','D':'ڈی','E':'ای','F':'ایف',
        'G':'جی','H':'ایچ','I':'آئی','J':'جے','K':'کے','L':'ایل',
        'M':'ایم','N':'این','O':'او','P':'پی','Q':'کیو','R':'آر',
        'S':'ایس','T':'ٹی','U':'یو','V':'وی','W':'ڈبلیو','X':'ایکس',
        'Y':'وائی','Z':'زیڈ'
    }
    return " ".join([map_abbr.get(c, c) for c in abbr.upper()])

def convert_inventory_auto(text):
    """
    007=24WAY 3LIGHT+3VM PANEL SR
    -> 007=24-وے 3-لائٹ + 3-وی ایم (VM) پینل ایس آر (SR)
    """
    # split keeping numbers
    def repl(match):
        token = match.group(0)
        # 24WAY -> 24 + WAY
        m = re.match(r'^(\d+)([A-Z]+)$', token)
        if m:
            num, word = m.groups()
            return f"{num}-{transliterate_word(word)}"

        if token.isalpha():
            # keep small codes as وی ایم (VM)
            if len(token) <= 3 and token.isupper():
                ur = transliterate_abbr(token)
                return f"{ur} ({token})"
            return transliterate_word(token)
        return token

    pattern = r'\d+[A-Z]+|[A-Z]+'
    result = re.sub(pattern, repl, text.upper())
    result = result.replace("+", " + ")
    return re.sub(r'\s+', ' ', result).strip()

# TEST
print(convert_inventory_auto("O12 BULB 12W OSAKA"))