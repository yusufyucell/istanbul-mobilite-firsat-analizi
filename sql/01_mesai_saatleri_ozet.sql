-- =====================================================================
-- 01 - Ham saatlik toplu taşıma verisini mesai saatlerine indirger
-- =====================================================================
-- Girdi : İBB "Saatlik Toplu Ulaşım Veri Seti" (aylık CSV, ~1,5 GB)
-- Çıktı : Hafta içi 07:00-20:00 arası, özetlenmiş satırlar
--
-- {source} ve {target} yer tutucularını src/build_transport.py doldurur.
-- =====================================================================

COPY (
    SELECT
        CAST(transition_date AS DATE)                AS tarih,
        CAST(transition_hour AS INTEGER)             AS saat,
        road_type                                    AS yol_turu,      -- OTOYOL / RAYLI / DENİZ
        line_name                                    AS hat_kodu,      -- 500T, M2, 34 ...
        line                                         AS hat_adi,
        -- İstasyon bilgisi raylı sistem ve metrobüste dolu, otobüste boş
        station_poi_desc_cd                          AS istasyon,
        -- Normal otobüs satırlarındaki ilçe alanı biniş yerini göstermiyor
        -- (ör. 500T yolcularının %95'i "BAKIRKOY"). İstasyonlu satırlarda
        -- (raylı, deniz, metrobüs) ise güvenilir; sadece onlarda tutulur.
        CASE WHEN road_type <> 'OTOYOL' OR station_poi_desc_cd IS NOT NULL
             THEN town END                           AS ilce,
        transfer_type = 'Aktarma'                    AS aktarma_mi,
        -- Bilet tipi: abonman (düzenli kullanıcı), kontür, aktarma, ücretsiz
        CASE
            WHEN transaction_type_desc LIKE '%Abonman%' THEN 'ABONMAN'
            WHEN transaction_type_desc LIKE '%Aktarma%' THEN 'AKTARMA'
            WHEN transaction_type_desc LIKE '%Kontur%'  THEN 'KONTUR'
            WHEN transaction_type_desc = 'Ucretsiz'     THEN 'UCRETSIZ'
            ELSE 'DIGER'
        END                                          AS bilet_grubu,
        CASE
            WHEN product_kind = 'TAM'             THEN 'TAM'
            WHEN product_kind LIKE 'INDIRIMLI%'   THEN 'INDIRIMLI'
            WHEN product_kind = 'UCRETSIZ'        THEN 'UCRETSIZ'
            ELSE 'DIGER'
        END                                          AS kart_turu,
        SUM(number_of_passage)                       AS gecis_sayisi,
        SUM(number_of_passenger)                     AS yolcu_sayisi
    FROM read_csv(
        '{source}',
        header = true,
        columns = {
            'transition_date': 'VARCHAR', 'transition_hour': 'VARCHAR',
            'transport_type_id': 'VARCHAR', 'road_type': 'VARCHAR',
            'line': 'VARCHAR', 'transfer_type': 'VARCHAR',
            'number_of_passage': 'BIGINT', 'number_of_passenger': 'BIGINT',
            'product_kind': 'VARCHAR', 'transaction_type_desc': 'VARCHAR',
            'town': 'VARCHAR', 'line_name': 'VARCHAR', 'station_poi_desc_cd': 'VARCHAR'
        }
    )
    WHERE CAST(transition_hour AS INTEGER) BETWEEN 7 AND 19          -- 07:00-19:59
      AND dayofweek(CAST(transition_date AS DATE)) BETWEEN 1 AND 5   -- Pzt-Cum
      AND CAST(transition_date AS DATE) NOT IN ('2024-01-01')        -- resmi tatil
    GROUP BY ALL
) TO '{target}' (FORMAT parquet, COMPRESSION zstd);
