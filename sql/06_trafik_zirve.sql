-- =====================================================================
-- 06 - Zirve saat trafik sıkışıklığı (geohash hücresi bazında)
-- =====================================================================
-- sikisiklik_orani = zirve saat ortalama hızı / gün ortası ortalama hızı
--   1.0  -> zirvede trafik gün ortası kadar akıcı
--   0.7  -> zirvede araçlar %30 daha yavaş
-- Düşük oran = o bölgede araçla (taksi, paylaşımlı araç) gitmek zirvede
-- toplu taşımaya karşı avantajını kaybeder.
--
-- Hücreler Python tarafında (geopandas) ilçelere bağlanır.
-- =====================================================================

WITH hucre AS (
    SELECT
        geohash,
        AVG(enlem)  AS enlem,
        AVG(boylam) AS boylam,
        -- 6 ayın ortalaması, her ayı gün sayısıyla ağırlıklandırarak
        SUM(ort_hiz * gun_sayisi) FILTER (WHERE saat BETWEEN 7 AND 9 OR saat BETWEEN 16 AND 19)
          / SUM(gun_sayisi)       FILTER (WHERE saat BETWEEN 7 AND 9 OR saat BETWEEN 16 AND 19) AS zirve_hiz,
        SUM(ort_hiz * gun_sayisi) FILTER (WHERE saat BETWEEN 10 AND 15)
          / SUM(gun_sayisi)       FILTER (WHERE saat BETWEEN 10 AND 15)                       AS gun_ortasi_hiz,
        AVG(ort_arac) FILTER (WHERE saat BETWEEN 7 AND 9 OR saat BETWEEN 16 AND 19)           AS zirve_arac
    FROM trafik
    GROUP BY geohash
)
SELECT
    *,
    zirve_hiz / gun_ortasi_hiz AS sikisiklik_orani
FROM hucre
WHERE zirve_hiz IS NOT NULL
  AND gun_ortasi_hiz > 0;
