{{ config(materialized='view') }}

COPY (
    SELECT
    *
FROM
    {{ ref('int_transaction_detail') }}
) TO 'prm_transaction_detail.csv' (HEADER, DELIMITER, ',')