"""
coleta.py
---------
Coleta de dados do SIHSUS e CNES via PySUS.
Requer Linux (WSL) para rodar.

Gera:
    dados/dados_sih_2024.csv         -> todas as internacoes CE 2024
    dados/dados_sih_2024_pulmao.csv  -> filtrado por CID C34 (cancer de pulmao)
    dados/cnes_porte_CE_2024.csv     -> hospitais com classificacao por porte
"""

import os
import pandas as pd
from pysus.ftp.databases.sih import SIH
from pysus.ftp.databases.cnes import CNES
from pysus.ftp import FTPSingleton

# ------------------------------------------------------------------ #
# Configuracoes
# ------------------------------------------------------------------ #
UF          = "CE"
ANO         = [2024]
MESES       = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
DIR_DBC     = "./dados/DBC"
DIR_DADOS   = "./dados"

os.makedirs(DIR_DBC,   exist_ok=True)
os.makedirs(DIR_DADOS, exist_ok=True)

FTPSingleton.timeout = 180

# ------------------------------------------------------------------ #
# 1. Coleta SIH — todas as internacoes CE 2024
# ------------------------------------------------------------------ #
print("=" * 60)
print("FASE 1 — Coleta SIH (todas as internacoes)")
print("=" * 60)

sih = SIH().load()
files = sih.get_files("RD", uf=UF, year=ANO, month=MESES)
print(f"{len(files)} arquivos encontrados.")

arquivos = sih.download(files, local_dir=DIR_DBC)
print("Download concluido.")

csv_sih = os.path.join(DIR_DADOS, "dados_sih_2024.csv")
if os.path.exists(csv_sih):
    os.remove(csv_sih)

first = True
for arquivo in arquivos:
    df = arquivo.to_dataframe()
    df.to_csv(csv_sih, mode="a", header=first, index=False)
    first = False
    print(f"  salvo: {arquivo}")

print(f"CSV gerado: {csv_sih}\n")

# ------------------------------------------------------------------ #
# 2. Filtro cancer de pulmao — CID C34
# ------------------------------------------------------------------ #
print("=" * 60)
print("FASE 2 — Filtro cancer de pulmao (CID C34)")
print("=" * 60)

csv_pulmao = os.path.join(DIR_DADOS, "dados_sih_2024_pulmao.csv")
if os.path.exists(csv_pulmao):
    os.remove(csv_pulmao)

first = True
for arquivo in arquivos:
    df = arquivo.to_dataframe()
    df_c34 = df[df["DIAG_PRINC"].astype(str).str.startswith("C34", na=False)]
    if not df_c34.empty:
        df_c34.to_csv(csv_pulmao, mode="a", header=first, index=False)
        first = False
        print(f"  {len(df_c34)} registros C34 em {arquivo}")

print(f"CSV gerado: {csv_pulmao}\n")

# ------------------------------------------------------------------ #
# 3. Coleta CNES — leitos e classificacao por porte
# ------------------------------------------------------------------ #
print("=" * 60)
print("FASE 3 — Coleta CNES (leitos e porte dos hospitais)")
print("=" * 60)

cnes = CNES().load()
files_st = cnes.get_files("ST", uf=UF, year=2024, month=12)
print(f"{len(files_st)} arquivos ST encontrados.")

arquivos_st = cnes.download(files_st, local_dir=DIR_DBC)

# Tenta carregar o parquet direto se o download retornar lista vazia
parquet_st = os.path.join(DIR_DBC, "STCE2412.parquet")
if os.path.exists(parquet_st):
    df_st = pd.read_parquet(parquet_st)
elif arquivos_st:
    df_st = arquivos_st[0].to_dataframe()
else:
    raise FileNotFoundError("Arquivo STCE2412.parquet nao encontrado. Rode novamente.")

# Selecionar colunas relevantes
colunas_porte = ["CNES", "LEITOS_SUS", "LEITOS_EXIST"] if "LEITOS_SUS" in df_st.columns else None

if colunas_porte:
    df_porte = df_st[colunas_porte].copy()
    df_porte["TOTAL_LEITOS_SUS"] = pd.to_numeric(df_porte["LEITOS_SUS"], errors="coerce").fillna(0)
else:
    # Fallback: usar arquivo LT (leitos)
    files_lt = cnes.get_files("LT", uf=UF, year=2024, month=12)
    arquivos_lt = cnes.download(files_lt, local_dir=DIR_DBC)
    parquet_lt = os.path.join(DIR_DBC, "LTCE2412.parquet")

    if os.path.exists(parquet_lt):
        df_lt = pd.read_parquet(parquet_lt)
    elif arquivos_lt:
        df_lt = arquivos_lt[0].to_dataframe()
    else:
        raise FileNotFoundError("Arquivo LTCE2412.parquet nao encontrado.")

    df_lt["QT_SUS"] = pd.to_numeric(df_lt["QT_SUS"], errors="coerce").fillna(0)
    df_porte = df_lt.groupby("CNES")["QT_SUS"].sum().reset_index()
    df_porte.columns = ["CNES", "TOTAL_LEITOS_SUS"]

# Classificar por porte (CONASS 2014)
def classificar_porte(leitos):
    if leitos <= 50:
        return "Pequeno"
    elif leitos <= 150:
        return "Medio"
    elif leitos <= 500:
        return "Grande"
    else:
        return "Especial"

df_porte["CNES"]            = df_porte["CNES"].astype(str)
df_porte["TOTAL_LEITOS_SUS"] = df_porte["TOTAL_LEITOS_SUS"].astype(float)
df_porte["PORTE"]           = df_porte["TOTAL_LEITOS_SUS"].apply(classificar_porte)

print(df_porte["PORTE"].value_counts().to_string())

csv_porte = os.path.join(DIR_DADOS, "cnes_porte_CE_2024.csv")
df_porte.to_csv(csv_porte, index=False)
print(f"CSV gerado: {csv_porte}\n")

print("=" * 60)
print("Coleta finalizada!")
print(f"  {csv_sih}")
print(f"  {csv_pulmao}")
print(f"  {csv_porte}")
print("=" * 60)