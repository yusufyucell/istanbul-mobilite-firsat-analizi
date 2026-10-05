-- =====================================================================
-- 04 - İlçe bazında talep, işe gidip gelme ve aktarma ölçütleri
-- =====================================================================
-- Gerektirir: 03_ilce_yolculuk.sql (ilce_yolculuk tablosu)
--
-- gunluk_binis        : Hafta içi bir günde mesai saatlerinde ortalama biniş
-- zirve_binis         : Sabah + akşam zirvesindeki ortalama günlük biniş
-- abonman_payi        : Abonmanlı binişlerin payı -> düzenli (işe/okula)
--                       gidip gelen yolcu göstergesi
-- sabah_zirve_payi    : Binişlerin ne kadarı 07-10 arasında
-- aktarma_orani       : Zirve saatlerde binişlerin ne kadarı aktarma
--                       (yüksekse yolculuk tek araçla bitmiyor = zahmetli)
-- =====================================================================

WITH gun AS (
    SELECT COUNT(DISTINCT tarih) AS gun_sayisi FROM ilce_yolculuk
),
ozet AS (
    SELECT
        ilce,
        SUM(yolcu)                                                     AS toplam,
        SUM(yolcu) FILTER (WHERE saat_dilimi <> 'gun_ortasi')          AS zirve,
        SUM(yolcu) FILTER (WHERE saat_dilimi = 'sabah_zirve')          AS sabah,
        SUM(yolcu) FILTER (WHERE bilet_grubu = 'ABONMAN')              AS abonman,
        SUM(yolcu) FILTER (WHERE aktarma_mi AND saat_dilimi <> 'gun_ortasi') AS zirve_aktarma
    FROM ilce_yolculuk
    WHERE ilce IN (SELECT ilce FROM istanbul_ilceleri)
    GROUP BY ilce
)
SELECT
    o.ilce,
    ROUND(o.toplam / g.gun_sayisi)              AS gunluk_binis,
    ROUND(o.zirve  / g.gun_sayisi)              AS zirve_binis,
    ROUND(o.abonman / o.toplam, 3)              AS abonman_payi,
    ROUND(o.sabah / o.toplam, 3)                AS sabah_zirve_payi,
    ROUND(o.zirve_aktarma / o.zirve, 3)         AS aktarma_orani,
    n.nufus,
    n.nufus_15_64,
    ROUND(n.calisma_cagi_payi, 3)               AS calisma_cagi_payi,
    -- 15-64 yaş nüfus başına günlük zirve binişi: toplu taşımaya bağımlılık
    ROUND(o.zirve / g.gun_sayisi / n.nufus_15_64, 3) AS kisi_basi_zirve_binis
FROM ozet o
CROSS JOIN gun g
JOIN ilce_nufus n USING (ilce)
ORDER BY zirve_binis DESC;
