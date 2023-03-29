DDL_BRONZE_DAILY_EXCHANGE_RATES_DROP = """
    DROP TABLE IF EXISTS bronze.daily_exchange_rates;
"""

DDL_DAILY_EXCHANGE_RATES_CREATE = """
    CREATE TABLE IF NOT EXISTS {stage}.daily_exchange_rates(dt Date, base String, cur String, val Decimal(20,6)) 
    ENGINE = MergeTree
    PARTITION BY toYYYYMMDD(dt)
    ORDER BY (dt, base)    
"""

DDL_BRONZE_DAILY_EXCHANGE_RATES_INSERT = """
    INSERT INTO bronze.daily_exchange_rates
    SELECT
    toDate('{date}') as dt,
    '{base}' as base,
    tupleElement(array, 1) AS cur,
    tupleElement(array, 2) AS val       
    FROM
    (
        SELECT
            {data} AS array
    )
    ARRAY JOIN array;  
"""    

DDL_GOLD_DAILY_EXCHANGE_RATES_EXCHANGE = """
    ALTER TABLE gold.daily_exchange_rates REPLACE PARTITION {date} FROM bronze.daily_exchange_rates;
"""