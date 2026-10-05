-- =====================================================================
-- 03 - Her binişi bir ilçeye bağlar (ilce_yolculuk tablosu)
-- =====================================================================
-- Sorun : Normal otobüs satırlarında binişin hangi ilçede olduğu yok.
-- Çözüm : Otobüs yolcularını, hattın duraklarının ilçelere dağılımına
--         göre paylaştırırız (hat_ilce_payi, GTFS'ten).
--         Ör. 500T'nin duraklarının %30'u Şişli'deyse, yolcularının
--         %30'unu Şişli'ye yazarız.
-- Varsayım: Biniş, hattın duraklarına eşit dağılır. Kaba ama tutarlı.
-- =====================================================================

CREATE OR REPLACE TABLE ilce_yolculuk AS
WITH esli AS (
    SELECT
        y.tarih,
        y.saat,
        y.yol_turu,
        y.hat_kodu,
        y.aktarma_mi,
        y.bilet_grubu,
        -- İstasyonlu satırlarda ilçe zaten var; yoksa hattın ilçe payından gelir
        COALESCE(y.ilce, h.ilce)                        AS ilce,
        y.yolcu_sayisi * COALESCE(h.durak_payi, 1.0)    AS yolcu,
        (y.ilce IS NULL AND h.ilce IS NULL)             AS eslesmedi
    FROM yolculuk y
    LEFT JOIN hat_ilce_payi h
           ON y.ilce IS NULL
          AND y.yol_turu = 'OTOYOL'
          AND y.hat_kodu = h.hat_kodu
)
SELECT
    *,
    CASE
        WHEN saat BETWEEN 7  AND 9  THEN 'sabah_zirve'   -- 07:00-10:00
        WHEN saat BETWEEN 10 AND 15 THEN 'gun_ortasi'    -- 10:00-16:00
        ELSE                             'aksam_zirve'   -- 16:00-20:00
    END AS saat_dilimi
FROM esli;

-- Eşleşme kalitesi: yolcuların ne kadarı bir ilçeye bağlanabildi?
SELECT
    yol_turu,
    ROUND(SUM(yolcu) FILTER (WHERE NOT eslesmedi) / SUM(yolcu) * 100, 1) AS eslesen_yuzde,
    ROUND(SUM(yolcu) / 1e6, 1)                                          AS toplam_milyon_yolcu
FROM ilce_yolculuk
GROUP BY yol_turu
ORDER BY toplam_milyon_yolcu DESC;
