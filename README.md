# Catalog Coroner

A Streamlit in Snowflake app that reads UPCs from column A starting at row 3 in a partner catalog Excel file, checks 24-month sales totals in Snowflake, and writes `0 USD` into column I for UPCs with zero sales.

## How it works

- Select the business you are working in
- Upload the partner catalog `.xlsx`
- Click `Process catalog` to run the Snowflake sales query and update the workbook
- Enter the Snowflake sales table and column names
- The app queries Snowflake for sales totals over the last 24 months
- The app updates column I on rows where UPC sales are zero or missing
- The output workbook removes columns with `Status`, `Errors`, or `warnings` headers
- Download the updated workbook

Sales data queries are run with Streamlit query caching disabled so each workbook update uses fresh Snowflake results.

## Business selector

Business names and Snowflake business IDs are loaded from Snowflake:

```sql
SELECT ID, NAME
FROM ANALYTICS_PROD.DURIN_SERVICE.P_BUSINESS
```

The selected business ID is used to scope the Snowflake sales query for the uploaded workbook.

## Workbook assumptions

- UPCs are in **column A**
- Data starts on **row 3**
- Output should be written to **column I**

## Snowflake authentication

For shared team use, the best per-user authentication path is to deploy the app as Streamlit in Snowflake and share it through Snowsight. Users sign in to Snowflake before opening the app, and the app uses Streamlit's Snowflake runtime connection.

For Streamlit Community Cloud or another shared Streamlit host, configure server-side Snowflake credentials in app secrets. Do not use `authenticator = "externalbrowser"` on a shared URL:

```toml
[connections.snowflake]
account = "JD38204-MT76814"
user = "YOUR_SERVICE_USER"
password = "YOUR_SERVICE_PASSWORD"
warehouse = "YOUR_WAREHOUSE"
database = "YOUR_DATABASE"
schema = "YOUR_SCHEMA"
role = "H_DATASCI"
```

If Snowflake returns an error like `Incoming request with IP/Token ... is not allowed to access Snowflake`, the app reached Snowflake but Snowflake's network policy blocked the shared Streamlit server's outbound source. Ask a Snowflake administrator to allow the source shown in the error, for example `34.83.176.217`, on the relevant account or user network policy.

For new Snowflake network policy configuration, Snowflake recommends creating network rules and adding them to the policy.

For local development, create `.streamlit/secrets.toml` with shared Snowflake account settings only. Do not include a `user` or `password`; the person running the app enters their own Snowflake email in the app:

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

Local `externalbrowser` SSO only works when the browser and Streamlit Python process are on the same computer. It should not be used as the sign-in flow for multiple users on a shared Streamlit server, because Snowflake redirects the browser back to `localhost`.

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
