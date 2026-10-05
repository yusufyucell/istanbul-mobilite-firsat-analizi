"""
Büyük aylık veri setlerini (Ekim 2023 - Mart 2024) SQL ile mesai saatlerine
indirger ve aylık parquet olarak kaydeder.

  toplu_tasima : ~1,5 GB/ay CSV  ->  sql/01_mesai_saatleri_ozet.sql
  trafik       : ~125 MB/ay CSV  ->  sql/02_trafik_ozet.sql

Her ay geçici klasöre indirilir (kesilirse yeniden denenir), işlenir ve
hemen silinir; proje klasöründe sadece küçük parquet'ler kalır.

Çalıştırma:  python src/build_monthly.py            (ikisi de)
             python src/build_monthly.py trafik     (sadece biri)
"""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

import duckdb
import requests

ROOT = Path(__file__).resolve().parents[1]
API = "https://data.ibb.gov.tr/api/3/action/package_show?id={}"
MONTHS = ["202310", "202311", "202312", "202401", "202402", "202403"]
TMP = Path(tempfile.gettempdir()) / "istanbul-mobilite"

JOBS = {
    "toplu_tasima": ("hourly-public-transport-data-set", "01_mesai_saatleri_ozet.sql"),
    "trafik": ("hourly-traffic-density-data-set", "02_trafik_ozet.sql"),
}


def month_urls(dataset_id: str) -> dict[str, str]:
    resources = requests.get(API.format(dataset_id), timeout=60).json()["result"]["resources"]
    return {
        m: next(r["url"] for r in resources if r["url"].endswith(f"_{m}.csv"))
        for m in MONTHS
    }


def indir(url: str, hedef: Path) -> None:
    """curl ile indirir. İBB sunucusu kaldığı yerden devam etmeyi desteklemediği
    için kesilen indirme silinip baştan başlatılır."""
    for deneme in range(1, 11):
        hedef.unlink(missing_ok=True)
        sonuc = subprocess.run(
            ["curl", "-sS", "-L", "--retry", "5", "--retry-delay", "10",
             "--speed-limit", "10000", "--speed-time", "120", "-o", str(hedef), url]
        )
        if sonuc.returncode == 0:
            return
        print(f"    indirme kesildi (kod {sonuc.returncode}), baştan deneniyor... [{deneme}]", flush=True)
        time.sleep(10)
    raise RuntimeError(f"İndirilemedi: {url}")


def run(job: str, con: duckdb.DuckDBPyConnection) -> None:
    dataset_id, sql_file = JOBS[job]
    sql = (ROOT / "sql" / sql_file).read_text(encoding="utf-8")
    out = ROOT / "data" / "processed" / job
    out.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(exist_ok=True)
    for month, url in month_urls(dataset_id).items():
        target = out / f"{month}.parquet"
        if target.exists():
            print(f"[{job}] {month}: zaten var", flush=True)
            continue
        t0 = time.time()
        csv = TMP / f"{job}_{month}.csv"
        indir(url, csv)
        t1 = time.time()
        tmp = target.with_suffix(".part")
        con.execute(sql.replace("{source}", csv.as_posix()).replace("{target}", tmp.as_posix()))
        tmp.replace(target)
        csv.unlink()
        rows = con.execute(f"SELECT COUNT(*) FROM '{target.as_posix()}'").fetchone()[0]
        print(f"[{job}] {month}: {rows:,} satır, {target.stat().st_size / 1e6:.1f} MB "
              f"(indirme {t1 - t0:.0f} sn, işleme {time.time() - t1:.0f} sn)", flush=True)
    shutil.rmtree(TMP, ignore_errors=True)


def main() -> None:
    con = duckdb.connect()
    for job in sys.argv[1:] or JOBS:
        run(job, con)


if __name__ == "__main__":
    main()
