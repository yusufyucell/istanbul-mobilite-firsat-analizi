"""
Küçük referans veri setlerini temizler ve ilçe bazında birleştirilebilir hale getirir.

Çıktılar (data/processed/referans/):
  ilceler.parquet            ilçe sınırları (harita için)
  duraklar.parquet           İETT durakları + bulunduğu ilçe
  istasyonlar.parquet        mevcut raylı sistem istasyonları + ilçe
  hat_ilce_payi.parquet      her otobüs hattının duraklarının ilçelere dağılımı
  hat_saat_sefer.parquet     hafta içi, hat x saat planlanan sefer sayısı
  ilce_nufus.parquet         2023 nüfusu ve 15-64 yaş payı
  ilce_sosyal_yardim.parquet 2023 sosyal yardım alan hane sayısı

Çalıştırma:  python src/build_reference.py
"""
import zipfile

import geopandas as gpd
import pandas as pd

from utils import EXTERNAL, PROCESSED, gtfs_koordinat, ilce_anahtari, mojibake_duzelt

OUT = PROCESSED / "referans"
GTFS = EXTERNAL / "iett-gtfs-verisi"
HAFTA_ICI_SERVIS = "0"  # calendar.csv: 0 = WEEKDAYS


def ilceler() -> gpd.GeoDataFrame:
    g = gpd.read_file(EXTERNAL / "sinirlar" / "ilce_geojson.json")
    g["ilce_adi"] = g["display_name"].str.split(",").str[0]
    g["ilce"] = g["ilce_adi"].map(ilce_anahtari)
    return g[["ilce", "ilce_adi", "geometry"]]


def duraklar(ilce_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    s = pd.read_csv(GTFS / "stops.csv", sep=";", dtype=str)
    s["enlem"] = s["stop_lat"].map(gtfs_koordinat)
    s["boylam"] = s["stop_lon"].map(gtfs_koordinat)
    s = s.dropna(subset=["enlem", "boylam"])
    gdf = gpd.GeoDataFrame(
        s[["stop_id", "stop_code", "stop_name", "enlem", "boylam"]],
        geometry=gpd.points_from_xy(s["boylam"], s["enlem"]),
        crs="EPSG:4326",
    )
    return gpd.sjoin(gdf, ilce_gdf[["ilce", "geometry"]], how="left", predicate="within").drop(
        columns="index_right"
    )


def istasyonlar(ilce_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    g = gpd.read_file(EXTERNAL / "rayli-sistem-istasyon-noktalari-verisi"
                      / "rayli_sistem_istasyon_poi_verisi.geojson")
    g = g[g["PROJE_ASAMA"] == "Mevcut Hattaki İstasyon"]
    g = g.rename(columns={"ISTASYON": "istasyon", "PROJE_ADI": "hat", "HAT_TURU": "tur"})
    g = g[["istasyon", "hat", "tur", "geometry"]].to_crs("EPSG:4326")
    return gpd.sjoin(g, ilce_gdf[["ilce", "geometry"]], how="left", predicate="within").drop(
        columns="index_right"
    )


METROBUS_HATLARI = {"34", "34A", "34AS", "34BZ", "34C", "34G", "34Z"}


def gtfs_hatlar(durak_gdf: gpd.GeoDataFrame) -> tuple[pd.DataFrame, pd.DataFrame, set]:
    routes = pd.read_csv(GTFS / "routes.csv", sep=";", dtype=str)
    trips = pd.read_csv(GTFS / "trips.csv", sep=";", dtype=str)
    with zipfile.ZipFile(GTFS / "stop_times.zip") as z:
        st = pd.read_csv(z.open("stop_times.txt"), dtype=str,
                         usecols=["trip_id", "stop_id", "stop_sequence", "departure_time"])

    trips = trips[trips["service_id"] == HAFTA_ICI_SERVIS].merge(
        routes[["route_id", "route_short_name"]], on="route_id"
    ).rename(columns={"route_short_name": "hat_kodu"})
    st = st.merge(trips[["trip_id", "hat_kodu"]], on="trip_id")

    # 1) Hat x saat sefer sayısı: seferin ilk duraktan kalkış saati
    ilk = st[st["stop_sequence"] == "1"].dropna(subset=["departure_time"])
    ilk = ilk.assign(saat=ilk["departure_time"].str[:2].astype(int) % 24)
    sefer = ilk.groupby(["hat_kodu", "saat"]).size().rename("sefer_sayisi").reset_index()

    # 2) Hattın uğradığı (tekil) durakların ilçelere dağılımı
    hat_durak = st[["hat_kodu", "stop_id"]].drop_duplicates().merge(
        durak_gdf[["stop_id", "ilce"]], on="stop_id"
    ).dropna(subset=["ilce"])
    pay = hat_durak.groupby(["hat_kodu", "ilce"]).size().rename("durak_sayisi").reset_index()
    pay["durak_payi"] = pay["durak_sayisi"] / pay.groupby("hat_kodu")["durak_sayisi"].transform("sum")

    # 3) Metrobüs durakları (raylı sistem listesinde yok, istasyon olarak eklenecek)
    metrobus = set(st.loc[st["hat_kodu"].isin(METROBUS_HATLARI), "stop_id"])
    return sefer, pay, metrobus


def nufus(yil: int = 2023) -> pd.DataFrame:
    p = pd.read_excel(EXTERNAL / "nufus-bilgileri" / "nufus-bilgileri.xlsx")
    p = p[p["Yıl"] == yil].copy()
    yas_kolonlari = [c for c in p.columns if " ve " in c]
    calisma_cagi = [c for c in yas_kolonlari
                    if c.split(" ve ")[1] in {"15-19", "20-24", "25-29", "30-34", "35-39",
                                              "40-44", "45-49", "50-54", "55-59", "60-64"}]
    out = pd.DataFrame({
        "ilce": p["İlçe"].map(ilce_anahtari),
        "nufus": p[yas_kolonlari].sum(axis=1),
        "nufus_15_64": p[calisma_cagi].sum(axis=1),
    })
    out["calisma_cagi_payi"] = out["nufus_15_64"] / out["nufus"]
    return out


def sosyal_yardim() -> pd.DataFrame:
    s = pd.read_excel(EXTERNAL / "mahallelere-gore-sosyal-yardim-alan-hane-sayisi"
                      / "mahallelere-gore-sosyal-yardm-alan-hane-says_2023.xlsx")
    s["ilce"] = s["İLÇE"].map(ilce_anahtari)
    return s.groupby("ilce", as_index=False)["HANE SAYISI"].sum().rename(
        columns={"HANE SAYISI": "sosyal_yardim_hane"})


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ilce_gdf = ilceler()
    ilce_gdf.to_parquet(OUT / "ilceler.parquet")

    durak_gdf = duraklar(ilce_gdf)
    durak_gdf.to_parquet(OUT / "duraklar.parquet")
    print(f"duraklar: {len(durak_gdf):,}, ilçesi bulunamayan: {durak_gdf['ilce'].isna().sum()}")

    sefer, pay, metrobus_ids = gtfs_hatlar(durak_gdf)
    mb = durak_gdf[durak_gdf["stop_id"].isin(metrobus_ids)]
    mb = mb.assign(istasyon=mb["stop_name"], hat="Metrobüs", tur="Metrobüs")
    ist = pd.concat([istasyonlar(ilce_gdf), mb[["istasyon", "hat", "tur", "geometry", "ilce"]]],
                    ignore_index=True)
    ist.to_parquet(OUT / "istasyonlar.parquet")
    print(f"istasyonlar: {len(ist)}, türler: {ist['tur'].value_counts().to_dict()}")

    sefer.to_parquet(OUT / "hat_saat_sefer.parquet")
    pay.to_parquet(OUT / "hat_ilce_payi.parquet")
    print(f"hatlar: {sefer['hat_kodu'].nunique()}, hafta içi toplam sefer: {sefer['sefer_sayisi'].sum():,}")

    n = nufus()
    n.to_parquet(OUT / "ilce_nufus.parquet")
    sy = sosyal_yardim()
    sy.to_parquet(OUT / "ilce_sosyal_yardim.parquet")

    # Tüm veri setlerinin ilçe anahtarları sınır dosyasıyla eşleşiyor mu?
    anahtarlar = set(ilce_gdf["ilce"])
    for ad, df in [("nüfus", n), ("sosyal yardım", sy)]:
        eksik = set(df["ilce"]) ^ anahtarlar
        print(f"{ad}: {len(df)} ilçe, eşleşmeyen: {sorted(eksik) or 'yok'}")


if __name__ == "__main__":
    main()
