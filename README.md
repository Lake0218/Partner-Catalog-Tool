# Partner Catalog Zero-Sales Tool

A Streamlit in Snowflake app that reads UPCs from column A starting at row 3 in a partner catalog Excel file, checks 12-month sales totals in Snowflake, and writes `0 USD` into column I for UPCs with zero sales.

## How it works

- Upload the partner catalog `.xlsx`
- Enter the Snowflake sales table and column names
- The app queries Snowflake for sales totals over the last 24 months
- The app updates column I on rows where UPC sales are zero or missing
- Download the updated workbook

## Workbook assumptions

- UPCs are in **column A**
- Data starts on **row 3**
- Output should be written to **column I**

## Snowflake authentication

The app uses Streamlit's Snowflake connection:

```python
conn = st.connection("snowflake")
```

When the app runs inside Snowflake, authentication is handled by the Streamlit app's Snowflake runtime and query warehouse. No Snowflake password secret is required.

For local development, create `.streamlit/secrets.toml` and configure the Snowflake connection. If your account uses SSO, use `authenticator = "externalbrowser"` instead of a password:

```toml
[connections.snowflake]
account = "JD38204-MT76814"
user = "L.HAWK@FETCHREWARDS.COM"
authenticator = "externalbrowser"
login_timeout = 300
warehouse = "YOUR_WAREHOUSE"
database = "YOUR_DATABASE"
schema = "YOUR_SCHEMA"
role = "H_DATASCI"
```

When local SSO starts, the app shows an `Open Snowflake SSO` button. Open it, complete the Snowflake sign-in, then return to the app and click `Process catalog` again.

If your Snowflake account allows username/password authentication, you can use `password = "YOUR_PASSWORD"` in the same block instead of `authenticator`.

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
WHERE SALE_DATE >= DATEADD(month, -12, CURRENT_DATE())
GROUP BY TO_VARCHAR(UPC)
