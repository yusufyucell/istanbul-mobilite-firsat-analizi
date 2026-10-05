-- =====================================================================
-- 02 - Saatlik trafik yoğunluğu verisini mesai saatlerine indirger
-- =====================================================================
-- Girdi : İBB "Saatlik Trafik Yoğunluk Veri Seti" (aylık CSV, ~125 MB)
--         Her satır: bir geohash hücresi (~1,2 km x 0,6 km) x bir saat
-- Çıktı : Hücre x saat bazında ortalama hız ve araç sayısı
-- =====================================================================

COPY (
    SELECT
        GEOHASH                               AS geohash,
        AVG(LATITUDE)                         AS enlem,
        AVG(LONGITUDE)                        AS boylam,
        hour(DATE_TIME)                       AS saat,
        COUNT(DISTINCT CAST(DATE_TIME AS DATE)) AS gun_sayisi,
        AVG(AVERAGE_SPEED)                    AS ort_hiz,
        AVG(NUMBER_OF_VEHICLES)               AS ort_arac
    FROM read_csv('{source}', header = true, timestampformat = '%Y-%m-%d %H:%M:%S')
    WHERE hour(DATE_TIME) BETWEEN 7 AND 19
      AND dayofweek(DATE_TIME) BETWEEN 1 AND 5
      AND CAST(DATE_TIME AS DATE) NOT IN ('2024-01-01')
    GROUP BY ALL
) TO '{target}' (FORMAT parquet, COMPRESSION zstd);
