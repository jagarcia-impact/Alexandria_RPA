
{{ config(materialized='table') }}

SELECT
    *
FROM read_csv_auto('../raw_data/transaction_detail_ytd.csv')