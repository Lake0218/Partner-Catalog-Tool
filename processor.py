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
        columns = [column[0] for column in cur.description]
    finally:
        cur.close()

    return pd.DataFrame(rows, columns=columns)


def load_sales_lookup(conn):
    sql = """
        WITH partner_barcodes AS (
            SELECT DISTINCT fc.barcode
            FROM fetch_services_prod.staging.fido_catalog_cleaned_stage fc
                LEFT JOIN analytics_prod.durin_service.p_brands b
                    ON fc.brand_id = b.id
                LEFT JOIN analytics_prod.durin_service.p_business biz
                    ON b.business_id = biz.id
            WHERE biz.id = '61dc504a5806c5140572e822'
                AND fc.deleted_date IS NULL
                AND fc.added_date < DATEADD(MONTH, -6, CURRENT_DATE)
                AND COALESCE(b.deleted_ts, b.be_soft_deleted_ts) IS NULL
                AND biz.deleted_ts IS NULL
        )
        SELECT
            pb.barcode AS UPC,
            SUM(ri.final_sale) AS TOTAL_SALES
        FROM partner_barcodes AS pb
            LEFT JOIN analytics_prod.partner_analytics.pa_receipts_items AS ri
                ON ri.barcode = pb.barcode
                AND ri.purchase_date::DATE >= DATEADD(MONTH, -24, CURRENT_DATE)
        GROUP BY pb.barcode
        HAVING TOTAL_SALES IS NULL
        ORDER BY pb.barcode
    """

    df = run_snowflake_query(conn, sql)
    if df.empty:
        return {}

    df.columns = [str(column).upper() for column in df.columns]
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
        has_zero_sales = upc in sales_lookup

        if has_zero_sales:
            matched_rows += 1
            ws[f"{OUTPUT_COL}{row}"] = "0 USD"
            zero_sales_rows += 1
        else:
            missing_rows += 1
            missing_upcs.append(upc)

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
