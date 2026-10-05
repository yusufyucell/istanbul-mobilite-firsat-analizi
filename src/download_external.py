"""
Yardımcı (küçük) veri setlerini İBB Açık Veri Portalı'ndan indirir.

Büyük veriler (saatlik toplu taşıma ve trafik yoğunluğu) diske indirilmeden
ayrı scriptlerde akış halinde işlenir.

Çalıştırma:  python src/download_external.py
"""
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "external"
API = "https://data.ibb.gov.tr/api/3/action/package_show?id={}"

# (veri seti kimliği, indirilecek dosya adlarının içermesi gereken metin)
DATASETS = {
    "rayli-sistem-istasyon-noktalari-verisi": ["rayli_sistem_istasyon_poi_verisi.geojson"],
    "nufus-bilgileri": ["nufus-bilgileri.xlsx"],
    "mahallelere-gore-sosyal-yardim-alan-hane-sayisi": ["2023.xlsx"],
    "iett-gtfs-verisi": ["routes.csv", "stops.csv", "trips.csv", "calendar.csv", "stop_times.zip"],
}


def download(url: str, target: Path) -> None:
    if target.exists() and target.stat().st_size > 0:
        print(f"  zaten var: {target.name}")
        return
    print(f"  indiriliyor: {target.name}")
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        tmp = target.with_suffix(target.suffix + ".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
        tmp.replace(target)


def main() -> None:
    for dataset_id, patterns in DATASETS.items():
        print(f"[{dataset_id}]")
        folder = OUT / dataset_id
        folder.mkdir(parents=True, exist_ok=True)
        resources = requests.get(API.format(dataset_id), timeout=60).json()["result"]["resources"]
        for pattern in patterns:
            matches = [r for r in resources if r["url"].endswith(pattern)]
            if not matches:
                print(f"  BULUNAMADI: {pattern}")
                continue
            url = matches[-1]["url"]  # aynı addan birden fazlaysa en sonuncusu
            download(url, folder / url.split("/")[-1])


if __name__ == "__main__":
    main()
