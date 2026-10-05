"""
DuckDB bağlantısı: işlenmiş parquet dosyalarını SQL tablosu (view) olarak tanımlar,
sql/ klasöründeki sorguları çalıştırıp pandas DataFrame döndürür.

Notebook'larda kullanım:
    from db import baglan, sorgu
    con = baglan()
    df = sorgu(con, "03_ilce_talep.sql")
"""
from pathlib import Path

import duckdb
import pandas as pd

from utils import PROCESSED, ROOT

REF = PROCESSED / "referans"

VIEWS = {
    "yolculuk": PROCESSED / "toplu_tasima" / "*.parquet",
    "trafik": PROCESSED / "trafik" / "*.parquet",
    "hat_ilce_payi": REF / "hat_ilce_payi.parquet",
    "hat_saat_sefer": REF / "hat_saat_sefer.parquet",
    "ilce_nufus": REF / "ilce_nufus.parquet",
    "ilce_sosyal_yardim": REF / "ilce_sosyal_yardim.parquet",
}


def baglan() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    for ad, yol in VIEWS.items():
        con.execute(f"CREATE OR REPLACE VIEW {ad} AS SELECT * FROM read_parquet('{yol.as_posix()}')")
    # İstanbul ilçe listesi (Kocaeli'deki Marmaray istasyonlarını dışarıda bırakmak için)
    con.execute("CREATE OR REPLACE VIEW istanbul_ilceleri AS SELECT ilce FROM ilce_nufus")
    return con


def sorgu(con: duckdb.DuckDBPyConnection, dosya: str) -> pd.DataFrame:
    """sql/ klasöründeki bir dosyayı çalıştırır, son ifadenin sonucunu döndürür."""
    sql = (ROOT / "sql" / dosya).read_text(encoding="utf-8")
    return con.execute(sql).df()
