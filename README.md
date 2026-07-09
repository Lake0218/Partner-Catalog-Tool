# Partner Catalog Zero-Sales Tool

A Streamlit in Snowflake app that reads UPCs from column A starting at row 3 in a partner catalog Excel file, checks 24-month sales totals in Snowflake, and writes `0 USD` into column I for UPCs with zero sales.

## How it works

- Select the business you are working in
- Upload the partner catalog `.xlsx`
- Enter the Snowflake sales table and column names
- The app queries Snowflake for sales totals over the last 24 months
- The app updates column I on rows where UPC sales are zero or missing
- Download the updated workbook

## Business selector

Business names and Snowflake business IDs are loaded from Snowflake:

```sql
SELECT ID, NAME
FROM ANALYTICS_PROD.DURIN_SERVICE.P_BUSINESS
```

The selected business ID is saved in Streamlit session state as `selected_business_id` so it can be added to the sales query later.

## Workbook assumptions

- UPCs are in **column A**
- Data starts on **row 3**
- Output should be written to **column I**

## Snowflake authentication

The app requires each user to enter their own Snowflake email and complete SSO in the browser. The Snowflake connection is stored in that user's Streamlit session instead of being shared across everyone using the app.

For local development, create `.streamlit/secrets.toml` with shared Snowflake account settings only. Do not include a `user` or `password`; each person signs in with their own Snowflake user:

```toml
[connections.snowflake]
account = "JD38204-MT76814"
authenticator = "externalbrowser"
login_timeout = 300
warehouse = "YOUR_WAREHOUSE"
database = "YOUR_DATABASE"
schema = "YOUR_SCHEMA"
role = "H_DATASCI"
```

When local SSO starts, the app shows an `Open Snowflake SSO` button. Open it, complete the Snowflake sign-in, then return to the app and refresh. The business dropdown will load for the signed-in Snowflake user.

## Snowflake assumptions

The sales table must contain:

- a UPC column
- a sales amount column
- a sale date column

Example query shape:

```sql
SELECT
  TO_VARCHAR(UPC) AS UPC,
  COALESCE(SUM(SALES_AMOUNT), 0) AS TOTAL_SALES
FROM SALES_TABLE
WHERE SALE_DATE >= DATEADD(month, -24, CURRENT_DATE())
GROUP BY TO_VARCHAR(UPC)
