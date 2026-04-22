import zipfile
import json
import re
import unicodedata


def load_scratch(file_path):
    """Încarcă fișierul JSON din arhiva .sb3"""
    with zipfile.ZipFile(file_path, 'r') as z:
        return json.loads(z.read('project.json'))


def clean_name(name):
    """
    Transformă orice nume din Scratch într-un nume valid de Flowgorithm:
    1. Elimină diacriticele (ă -> a, ș -> s etc.)
    2. Elimină orice caracter care nu este literă sau cifră (inclusiv _)
    3. Adaugă prefixul 'v' dacă numele începe cu o cifră.
    """
    if not name:
        return "var"

    # Pasul 1: Normalizare (eliminare diacritice)
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')

    # Pasul 2: Păstrează doar litere și cifre (fără underscore!)
    clean = re.sub(r'[^a-zA-Z0-9]', '', name)

    # Pasul 3: Flowgorithm nu acceptă nume care încep cu cifră
    if clean and clean[0].isdigit():
        clean = "v" + clean

    return clean or "var"