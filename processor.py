from io import BytesIO

import pandas as pd
from openpyxl import load_workbook

UPC_COL = "A"
OUTPUT_COL = "I"
START_ROW = 3


def normalize_upc(value):
    if value is None or pd.isna(value):
        return None

    if isinstance(value, float) and value.is_integer():
        value = int(value)

    return str(value).strip()


def run_snowflake_query(conn, sql):
    if hasattr(conn, "query"):
        return conn.query(sql)

    cur = conn.cursor()
    try:
        cur.execute(sql)
        rows = cur.fetchall()
    finally:
        cur.close()

    return pd.DataFrame(rows, columns=["UPC", "TOTAL_SALES"])


def load_sales_lookup(conn, lookback_months=24):
    sql = f"""
        SELECT
            ITEM_BARCODE AS UPC,
            COALESCE(SUM(ITEM_FINAL_EXTENDED_PRICE), 0) AS TOTAL_SALES
        FROM ANALYTICS_PROD.FETCH360.TRANSACTION360
        WHERE RECEIPT_PURCHASE_DATE >= DATEADD(month, -{lookback_months}, CURRENT_DATE())
        GROUP BY ITEM_BARCODE
    """

    df = run_snowflake_query(conn, sql)
    if df.empty:
        return {}

    df["UPC"] = df["UPC"].apply(normalize_upc)
    df["TOTAL_SALES"] = pd.to_numeric(df["TOTAL_SALES"], errors="coerce").fillna(0)

    return dict(zip(df["UPC"], df["TOTAL_SALES"]))


def update_partner_catalog(workbook_file, sales_lookup):
    try:
        workbook_file.seek(0)
        wb = load_workbook(workbook_file)
    except Exception as exc:
        raise ValueError(
            "Could not load the uploaded workbook. Make sure it is a valid .xlsx file."
        ) from exc

    ws = wb[wb.sheetnames[0]]

    total_rows = 0
    zero_sales_rows = 0
    missing_rows = 0
    matched_rows = 0
    missing_upcs = []

    for row in range(START_ROW, ws.max_row + 1):
        upc = normalize_upc(ws[f"{UPC_COL}{row}"].value)
        if not upc:
            continue

        total_rows += 1
        total_sales = sales_lookup.get(upc)

        if total_sales is None:
            missing_rows += 1
            missing_upcs.append(upc)
            ws[f"{OUTPUT_COL}{row}"] = "0 USD"
            zero_sales_rows += 1
        else:
            matched_rows += 1
            if float(total_sales) == 0:
                ws[f"{OUTPUT_COL}{row}"] = "0 USD"
                zero_sales_rows += 1

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    summary = {
        "total_rows": total_rows,
        "zero_sales_rows": zero_sales_rows,
        "missing_rows": missing_rows,
        "missing_upcs": missing_upcs,
        "matched_rows": matched_rows,
    }

    return output, summary
