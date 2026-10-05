-- =====================================================================
-- 05 - Otobüs yük göstergesi (hat x saat dilimi ve ilçe bazında)
-- =====================================================================
-- Gerçek doluluk verisi yok. Yaklaşık gösterge:
--
--   yuk = (dilimde hatta binen ortalama yolcu / dilimde kalkan sefer)
--         / ortalama otobüs kapasitesi
--
-- Neden saat değil de dilim? 7:55'te kalkan otobüse 8:10'da binen yolcu
-- "8'deki sefere" yazılınca saatlik oranlar abartılı çıkıyor (ör. 36L 08:00
-- için 6x). 3-4 saatlik dilimlerde bu kayma büyük ölçüde dengeleniyor.
--
-- Varsayımlar (README'de yazılı):
--   * Kapasite 100 kişi (solo ~90, körüklü ~150, midibüs ~60 ortalaması)
--   * Biniş sayısı, aynı anda otobüsteki kişi sayısı değildir; yolcular yol
--     boyunca iner-biner. Bu yüzden 1'in üstü "taşma" değil, "yoğun hat"
--     anlamına gelir. Ölçüt, hatları KENDİ ARALARINDA karşılaştırmak içindir.
--   * Sefer planı 2026 GTFS'inden; yolcu verisi 2023-24. Hat planlarının büyük
--     ölçüde aynı kaldığı varsayılır.
-- =====================================================================

CREATE OR REPLACE TABLE hat_dilim_yuk AS
WITH gun AS (
    SELECT COUNT(DISTINCT tarih) AS gun_sayisi FROM yolculuk
),
dilimli AS (
    SELECT
        hat_kodu,
        saat,
        yolcu_sayisi,
        CASE
            WHEN saat BETWEEN 7  AND 9  THEN 'sabah_zirve'
            WHEN saat BETWEEN 10 AND 15 THEN 'gun_ortasi'
            ELSE                             'aksam_zirve'
        END AS saat_dilimi
    FROM yolculuk
    WHERE yol_turu = 'OTOYOL'
      AND istasyon IS NULL                -- metrobüs hariç, normal otobüs
),
yolcu AS (
    SELECT hat_kodu, saat_dilimi, SUM(yolcu_sayisi) AS yolcu
    FROM dilimli
    GROUP BY ALL
),
sefer AS (
    SELECT
        hat_kodu,
        CASE
            WHEN saat BETWEEN 7  AND 9  THEN 'sabah_zirve'
            WHEN saat BETWEEN 10 AND 15 THEN 'gun_ortasi'
            WHEN saat BETWEEN 16 AND 19 THEN 'aksam_zirve'
        END AS saat_dilimi,
        SUM(sefer_sayisi) AS sefer
    FROM hat_saat_sefer
    WHERE saat BETWEEN 7 AND 19
    GROUP BY ALL
)
SELECT
    y.hat_kodu,
    y.saat_dilimi,
    y.yolcu / g.gun_sayisi                         AS ort_yolcu,
    s.sefer,
    y.yolcu / g.gun_sayisi / s.sefer               AS sefer_basi_yolcu,
    y.yolcu / g.gun_sayisi / s.sefer / 100.0       AS yuk
FROM yolcu y
CROSS JOIN gun g
JOIN sefer s USING (hat_kodu, saat_dilimi);

-- İlçe bazında zirve yükü: ilçeden geçen hatların yüklerinin,
-- o ilçeye düşen yolcu sayısıyla ağırlıklı ortalaması
SELECT
    p.ilce,
    ROUND(SUM(h.yuk * h.ort_yolcu * p.durak_payi)
          / SUM(h.ort_yolcu * p.durak_payi), 3)    AS zirve_otobus_yuku,
    COUNT(DISTINCT h.hat_kodu)                     AS hat_sayisi
FROM hat_dilim_yuk h
JOIN hat_ilce_payi p USING (hat_kodu)
WHERE h.saat_dilimi IN ('sabah_zirve', 'aksam_zirve')
GROUP BY p.ilce
ORDER BY zirve_otobus_yuku DESC;
