{{ config(materialized='table') }}

SELECT
    "Office Key" as office_key,
    "Transaction Type" as transaction_type,
    "Chart Number" as encounter_id,
    "Visit #" as visit_number,
    "Facility Name" as facility_name,
    "Charge Code" as charge_code,
    "Transaction Code" as transaction_code,
    "Transaction Code Desc" as transaction_code_description,
    "Modifiers" as modifiers,
    "Visit - Primary Carrier" as primary_carrier,
    "Visit - Secondary Carrier" as secondary_carrier,
    "Transaction Carrier" as transaction_carrier,
    "Primary Dx (ICD-9)" as primary_diagnostic_icd9,
    "Primary Dx (ICD-10)" as primary_diagnostic_icd10,
    "Payment Method" as payment_method,
    "Check Number" as check_number,
    "Date of Service"::DATE as date_of_service,
    "Date of Entry"::DATE as date_of_entry,
    "Date of Deposit"::DATE as date_of_deposit,
    "Units" as units,
    CASE
    WHEN "Charges" LIKE '(%' THEN
        -1 * CAST(regexp_replace(regexp_replace("Charges", '[$()]', '', 'g'), ',', '') AS DOUBLE)
    ELSE
        CAST(regexp_replace(regexp_replace("Charges", '[$,]', '', 'g'), ',', '') AS DOUBLE)
    END AS charges,
    CAST(REPLACE("Patient Payments",'$','') AS DOUBLE) as patient_payments,
    CASE
    WHEN "Insurance Payments" LIKE '(%' THEN
        -1 * CAST(regexp_replace(regexp_replace("Insurance Payments", '[$()]', '', 'g'), ',', '') AS DOUBLE)
    ELSE
        CAST(regexp_replace(regexp_replace("Insurance Payments", '[$,]', '', 'g'), ',', '') AS DOUBLE)
    END AS insurance_payments,
    CASE
    WHEN "Total Payments" LIKE '(%' THEN
        -1 * CAST(regexp_replace(regexp_replace("Total Payments", '[$()]', '', 'g'), ',', '') AS DOUBLE)
    ELSE
        CAST(regexp_replace(regexp_replace("Insurance Payments", '[$,]', '', 'g'), ',', '') AS DOUBLE)
    END AS total_payments,
    CASE
    WHEN "Adjustments" LIKE '(%' THEN
        -1 * CAST(regexp_replace(regexp_replace("Adjustments", '[$()]', '', 'g'), ',', '') AS DOUBLE)
    ELSE
        CAST(regexp_replace(regexp_replace("Adjustments", '[$,]', '', 'g'), ',', '') AS DOUBLE)
    END AS adjustments
FROM
    {{ ref('staging_transaction_detail')}}