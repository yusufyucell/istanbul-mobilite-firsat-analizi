"""
Coğrafi ölçütler (SQL yerine geopandas ile hesaplanır).

erisim_ilce  : İlçedeki otobüs duraklarının en yakın raylı sistem /
               metrobüs istasyonuna uzaklığı.
               Durakları "insanların yaşadığı ve çalıştığı yerlerin" vekili
               olarak kullanıyoruz: İETT durakları yerleşim olan her yerde var.
trafik_ilce  : Geohash hücrelerindeki zirve saat hızlarının ilçe ortalaması.
"""
import geopandas as gpd
import pandas as pd

from utils import PROCESSED

REF = PROCESSED / "referans"
METRE_CRS = "EPSG:32635"  # UTM 35N: İstanbul için metre cinsinden mesafe
YURUME_ESIGI_M = 1000     # ~12-15 dk yürüyüş; ötesi "istasyona uzak"


def erisim_ilce() -> pd.DataFrame:
    duraklar = gpd.read_parquet(REF / "duraklar.parquet").dropna(subset=["ilce"]).to_crs(METRE_CRS)
    istasyonlar = gpd.read_parquet(REF / "istasyonlar.parquet").to_crs(METRE_CRS)

    en_yakin = gpd.sjoin_nearest(
        duraklar[["stop_id", "ilce", "geometry"]],
        istasyonlar[["istasyon", "tur", "geometry"]],
        how="left",
        distance_col="istasyona_mesafe_m",
    ).drop_duplicates("stop_id")  # eşit uzaklıkta iki istasyon varsa tek satır

    return (
        en_yakin.groupby("ilce")
        .agg(
            durak_sayisi=("stop_id", "size"),
            medyan_istasyon_mesafesi_m=("istasyona_mesafe_m", "median"),
            uzak_durak_payi=("istasyona_mesafe_m", lambda m: (m > YURUME_ESIGI_M).mean()),
        )
        .reset_index()
    )


def trafik_ilce(hucreler: pd.DataFrame) -> pd.DataFrame:
    """hucreler: sql/06_trafik_zirve.sql çıktısı."""
    ilceler = gpd.read_parquet(REF / "ilceler.parquet")
    g = gpd.GeoDataFrame(
        hucreler,
        geometry=gpd.points_from_xy(hucreler["boylam"], hucreler["enlem"]),
        crs="EPSG:4326",
    )
    g = gpd.sjoin(g, ilceler[["ilce", "geometry"]], predicate="within")

    # Araç sayısıyla ağırlıklı ortalama: yoğun yollardaki hız daha önemli
    def agirlikli(df: pd.DataFrame) -> pd.Series:
        w = df["zirve_arac"]
        return pd.Series({
            "zirve_hiz_kmh": (df["zirve_hiz"] * w).sum() / w.sum(),
            "gun_ortasi_hiz_kmh": (df["gun_ortasi_hiz"] * w).sum() / w.sum(),
            "hucre_sayisi": len(df),
        })

    out = g.groupby("ilce").apply(agirlikli, include_groups=False).reset_index()
    out["sikisiklik_orani"] = out["zirve_hiz_kmh"] / out["gun_ortasi_hiz_kmh"]
    return out
