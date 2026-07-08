# Partner Catalog Zero-Sales Tool

A Streamlit app that:

- uploads a partner catalog Excel file
- reads UPCs from column A starting at row 3
- queries Snowflake for sales over the last 12 months
- writes `0 USD` into column I for UPCs with zero sales
- downloads an updated workbook

## Project structure

```text
partner_catalog_zero_sales_tool/
├── app.py
├── processor.py
├── requirements.txt
├── README.md
└── .streamlit/
    └── secrets.toml
```

## Setup

1. Create a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Add Snowflake credentials to `.streamlit/secrets.toml`.
4. Run the app:

```bash
streamlit run app.py
```

## Snowflake config

Use `.streamlit/secrets.toml` like this:

```toml
[connections.snowflake]
account = "YOUR_ACCOUNT"
user = "YOUR_USERNAME"
password = "YOUR_PASSWORD"
role = "YOUR_ROLE"
warehouse = "YOUR_WAREHOUSE"
database = "YOUR_DATABASE"
schema = "YOUR_SCHEMA"
```

## Assumptions

- UPCs are in column A.
- Data starts on row 3.
- The output column is I.
- Snowflake has a table with UPC, sale date, and sales amount.

## Notes

The app writes the text `0 USD` into the workbook. If you later want a numeric zero with a currency format instead, that can be changed in `processor.py`.
