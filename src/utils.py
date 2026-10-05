"""Projede ortak kullanılan küçük yardımcı fonksiyonlar."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTERNAL = ROOT / "data" / "external"
PROCESSED = ROOT / "data" / "processed"

_TR_TO_ASCII = str.maketrans("İIıŞşĞğÜüÖöÇç", "IIISSGGUUOOCC")


def ilce_anahtari(ad: str) -> str:
    """İlçe adını veri setleri arasında eşleştirilebilir hale getirir.

    'Eyüpsultan' -> 'EYUPSULTAN', 'BAKIRKÖY' -> 'BAKIRKOY'
    """
    return ad.strip().translate(_TR_TO_ASCII).upper().replace(" ", "")


def mojibake_duzelt(metin: str) -> str:
    """UTF-8 metnin yanlışlıkla cp1252 olarak okunmasıyla bozulan karakterleri düzeltir.

    'KADIKÃ–Y' -> 'KADIKÖY'. Zaten düzgün olan metne dokunmaz.
    """
    try:
        return metin.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return metin


def gtfs_koordinat(deger: str) -> float:
    """GTFS dosyasındaki bozuk koordinatı düzeltir.

    Dosyada binlik ayırıcı gibi noktalar var: '409.169.730.005.406' -> 40.9169730005406
    İstanbul'un enlem (40-41) ve boylamları (27-29) iki haneli olduğu için
    noktalar silinip ilk iki haneden sonra ondalık ayırıcı eklenir.
    Kurtarılamayacak kadar bozuk değerler (birkaç satır) NaN döner.
    """
    rakamlar = str(deger).replace(".", "")
    if not rakamlar.isdigit():
        return float("nan")
    return float(rakamlar[:2] + "." + rakamlar[2:])
