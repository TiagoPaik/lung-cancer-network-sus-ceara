import unicodedata
import pandas as pd


def normalizar_nome(txt):
    if pd.isna(txt):
        return txt

    txt = str(txt).upper().strip()
    txt = unicodedata.normalize('NFKD', txt)
    txt = ''.join(c for c in txt if not unicodedata.combining(c))
    txt = ' '.join(txt.split())

    return txt