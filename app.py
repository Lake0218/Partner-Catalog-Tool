import threading
import time
import webbrowser
from html import escape
from importlib import reload
from urllib.parse import urlparse

import streamlit as st
import pandas as pd
import snowflake.connector

import businesses
from processor import load_sales_lookup, update_partner_catalog

businesses = reload(businesses)

st.set_page_config(page_title="Partner Catalog Zero-Sales Tool", layout="wide")
WEBBROWSER_CAPTURE_LOCK = threading.Lock()
LOCAL_HOSTNAMES = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


def inject_styles():
    st.markdown(
        """
        <style>
        :root {
            --app-bg: #f7f0ff;
            --panel: #fffdf8;
            --panel-strong: #f0e3ff;
            --panel-border: #d9c4ff;
            --text: #33243f;
            --muted: #6d5b7b;
            --accent: #8b3dff;
            --accent-dark: #6d28d9;
            --accent-hover: #581cbe;
            --sun: #ffbf47;
            --coral: #ff6a3d;
            --pink: #d946ef;
            --teal: #137f73;
            --ink: #281833;
        }

        .stApp {
            background:
                linear-gradient(180deg, #efe2ff 0%, #fff6eb 460px, var(--app-bg) 100%),
                var(--app-bg);
            color: var(--text);
        }

        .block-container {
            max-width: 1180px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        div[data-testid="stSidebar"] {
            background: #f1e5ff;
            border-right: 1px solid #d8c2ff;
        }

        div[data-testid="stSidebar"] * {
            color: var(--text);
        }

        div[data-testid="stSidebar"] .stCodeBlock pre {
            background: #fffdf8 !important;
            border: 1px solid #d8c2ff;
            border-radius: 8px;
        }

        .app-hero {
            border: 1px solid var(--panel-border);
            border-top: 5px solid var(--accent);
            background:
                radial-gradient(circle at top right, rgba(217, 70, 239, 0.20), transparent 30%),
                radial-gradient(circle at 85% 75%, rgba(255, 106, 61, 0.16), transparent 24%),
                var(--panel);
            border-radius: 8px;
            box-shadow: 0 18px 45px rgba(86, 42, 137, 0.14);
            padding: 1.7rem 1.8rem 1.55rem;
            margin-bottom: 1.1rem;
        }

        .app-eyebrow {
            color: var(--accent-dark);
            font-size: 0.76rem;
            font-weight: 750;
            letter-spacing: 0;
            text-transform: uppercase;
            margin-bottom: 0.35rem;
        }

        .app-title {
            color: var(--ink);
            font-size: clamp(2rem, 3.4vw, 3rem);
            line-height: 1.04;
            font-weight: 760;
            letter-spacing: 0;
            margin: 0;
        }

        .app-subtitle {
            color: var(--muted);
            max-width: 760px;
            margin: 0.85rem 0 1.2rem;
            font-size: 1rem;
            line-height: 1.55;
        }

        .hero-facts {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.75rem;
        }

        .fact-card {
            border: 1px solid #e4d5ff;
            border-radius: 8px;
            padding: 0.75rem 0.85rem;
            background: rgba(255, 253, 248, 0.74);
        }

        .fact-label {
            color: var(--muted);
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0;
            text-transform: uppercase;
            margin-bottom: 0.2rem;
        }

        .fact-value {
            color: var(--ink);
            font-size: 1.02rem;
            font-weight: 760;
            line-height: 1.25;
        }

        .section-heading {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 1rem;
        }

        .section-title-group {
            display: flex;
            align-items: flex-start;
            gap: 0.85rem;
        }

        .step-index {
            width: 2.35rem;
            height: 2.35rem;
            flex: 0 0 2.35rem;
            border-radius: 8px;
            display: grid;
            place-items: center;
            color: #fffaf2;
            background: var(--accent);
            font-size: 0.86rem;
            font-weight: 780;
            letter-spacing: 0;
        }

        .section-title {
            color: var(--ink);
            font-size: 1.12rem;
            font-weight: 760;
            line-height: 1.2;
            margin-top: 0.1rem;
        }

        .section-copy {
            color: var(--muted);
            font-size: 0.92rem;
            line-height: 1.4;
            margin-top: 0.18rem;
        }

        .section-status {
            border: 1px solid #dec9ff;
            background: #f2e8ff;
            color: var(--accent-dark);
            border-radius: 999px;
            padding: 0.32rem 0.62rem;
            font-size: 0.78rem;
            font-weight: 720;
            white-space: nowrap;
        }

        div.st-key-snowflake_panel,
        div.st-key-business_panel,
        div.st-key-catalog_panel {
            background: var(--panel);
            border-color: var(--panel-border);
            border-radius: 8px;
            box-shadow: 0 10px 30px rgba(86, 42, 137, 0.10);
            padding: 1.1rem 1.15rem;
        }

        div.st-key-snowflake_panel,
        div.st-key-business_panel {
            margin-bottom: 0.9rem;
        }

        .stButton > button,
        .stDownloadButton > button,
        .stLinkButton > a {
            border-radius: 8px !important;
            min-height: 2.65rem;
            font-weight: 720 !important;
        }

        .stButton > button[kind="primary"],
        .stDownloadButton > button[kind="primary"],
        .stLinkButton > a[kind="primary"] {
            background: var(--accent-dark) !important;
            border-color: var(--accent-dark) !important;
            color: #fffaf2 !important;
        }

        .stButton > button[kind="primary"]:hover,
        .stDownloadButton > button[kind="primary"]:hover,
        .stLinkButton > a[kind="primary"]:hover {
            background: var(--accent-hover) !important;
            border-color: var(--accent-hover) !important;
            color: #fffaf2 !important;
        }

        .stTextInput input,
        .stSelectbox div[data-baseweb="select"] > div,
        .stFileUploader section {
            border-radius: 8px !important;
            border-color: #d8c2ff !important;
            background-color: #fffdf8 !important;
        }

        div[data-testid="stMetric"] {
            background: #fffdf8;
            border: 1px solid #e4d5ff;
            border-radius: 8px;
            padding: 0.85rem 0.95rem;
            box-shadow: 0 8px 22px rgba(86, 42, 137, 0.08);
        }

        div[data-testid="stAlert"] {
            border-radius: 8px;
        }

        .stAlert {
            border-radius: 8px;
        }

        @media (max-width: 760px) {
            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }

            .app-hero {
                padding: 1.25rem;
            }

            .hero-facts {
                grid-template-columns: 1fr;
            }

            .section-heading {
                display: block;
            }

            .section-status {
                display: inline-block;
                margin-top: 0.75rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_app_header():
    st.markdown(
        """
        <div class="app-hero">
            <div class="app-eyebrow">Partner catalog operations</div>
            <h1 class="app-title">Zero-sales catalog review</h1>
            <div class="app-subtitle">
                Match catalog UPCs against Snowflake sales history and mark items with zero or missing sales.
            </div>
            <div class="hero-facts">
                <div class="fact-card">
                    <div class="fact-label">Sales window</div>
                    <div class="fact-value">Last 24 months</div>
                </div>
                <div class="fact-card">
                    <div class="fact-label">Catalog input</div>
                    <div class="fact-value">UPCs from column A</div>
                </div>
                <div class="fact-card">
                    <div class="fact-label">Workbook output</div>
                    <div class="fact-value">Zero-sales flags in column I</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(step, title, copy, status):
    st.markdown(
        f"""
        <div class="section-heading">
            <div class="section-title-group">
                <div class="step-index">{escape(step)}</div>
                <div>
                    <div class="section-title">{escape(title)}</div>
                    <div class="section-copy">{escape(copy)}</div>
                </div>
            </div>
            <div class="section-status">{escape(status)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


inject_styles()


class SnowflakeAuthState:
    def __init__(self):
        self.lock = threading.Lock()
        self.status = "idle"
        self.user = None
        self.auth_url = None
        self.conn = None
        self.error = None
        self.thread = None

    def close_connection(self):
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
        self.conn = None

    def reset(self):
        with self.lock:
            self.close_connection()
            self.status = "idle"
            self.user = None
            self.auth_url = None
            self.error = None
            self.thread = None


render_app_header()

with st.sidebar:
    st.header("Snowflake settings")
    st.caption(
        "Local browser SSO is for development on one computer. Shared users "
        "should open the deployed Streamlit app from Snowflake."
    )
    st.code(
        """# Optional for local development only:
[connections.snowflake]
account = "JD38204-MT76814"
authenticator = "externalbrowser"
login_timeout = 300
warehouse = "YOUR_WAREHOUSE"
database = "YOUR_DATABASE"
schema = "YOUR_SCHEMA"
role = "H_DATASCI"
""",
        language="toml",
    )

def get_local_snowflake_config():
    try:
        sf = st.secrets.get("connections", {}).get("snowflake", {})
    except Exception:
        return {}

    if hasattr(sf, "to_dict"):
        sf = sf.to_dict()
    else:
        sf = dict(sf)

    return {
        key: value
        for key, value in sf.items()
        if value and not str(value).startswith("YOUR_")
    }


def get_sso_base_config():
    config = get_local_snowflake_config()
    config.pop("user", None)
    config.pop("username", None)
    config.pop("password", None)
    config["authenticator"] = "externalbrowser"
    config.setdefault("login_timeout", 300)
    return config


def get_request_hostname():
    try:
        current_url = st.context.url
    except Exception:
        return None

    if not current_url:
        return None

    return urlparse(current_url).hostname


def is_local_browser_request():
    hostname = get_request_hostname()
    if not hostname:
        return True
    return hostname.lower() in LOCAL_HOSTNAMES


def get_streamlit_user_label():
    try:
        email = getattr(st.user, "email", None)
        if email:
            return email
        if hasattr(st.user, "get"):
            return st.user.get("email") or st.user.get("user_name")
    except Exception:
        return "current Streamlit user"
    return "current Streamlit user"


def get_streamlit_runtime_connection():
    try:
        conn = st.connection("snowflake")
    except Exception as exc:
        st.error("Snowflake is not connected for this Streamlit runtime.")
        st.info(
            "For shared use, deploy the app as Streamlit in Snowflake so users "
            "sign in through Snowsight. For local development, run the app on "
            "your own computer with `authenticator = \"externalbrowser\"`."
        )
        st.exception(exc)
        return None, None

    user_label = get_streamlit_user_label()
    st.success(f"Connected through the Streamlit Snowflake runtime as {user_label}.")
    return conn, user_label


def normalize_snowflake_user(value):
    return str(value or "").strip()


def get_session_auth_state(snowflake_user):
    session_user = normalize_snowflake_user(snowflake_user).lower()
    auth_state = st.session_state.get("snowflake_auth_state")
    auth_user = st.session_state.get("snowflake_auth_user")

    if auth_state is None or auth_user != session_user:
        if auth_state is not None:
            auth_state.reset()
        auth_state = SnowflakeAuthState()
        st.session_state["snowflake_auth_state"] = auth_state
        st.session_state["snowflake_auth_user"] = session_user

    return auth_state


def connect_with_captured_sso(config, auth_state):
    original_open = webbrowser.open
    original_open_new = webbrowser.open_new
    original_open_new_tab = webbrowser.open_new_tab

    def capture_auth_url(url, *args, **kwargs):
        with auth_state.lock:
            auth_state.auth_url = url
            auth_state.status = "waiting_for_sso"
        return True

    with WEBBROWSER_CAPTURE_LOCK:
        try:
            webbrowser.open = capture_auth_url
            webbrowser.open_new = capture_auth_url
            webbrowser.open_new_tab = capture_auth_url
            conn = snowflake.connector.connect(**config)
            with auth_state.lock:
                auth_state.conn = conn
                auth_state.status = "connected"
        except Exception as exc:
            with auth_state.lock:
                auth_state.error = exc
                auth_state.status = "error"
        finally:
            webbrowser.open = original_open
            webbrowser.open_new = original_open_new
            webbrowser.open_new_tab = original_open_new_tab


def start_externalbrowser_auth(config, auth_state):
    with auth_state.lock:
        if auth_state.status in {"starting", "waiting_for_sso"}:
            return
        auth_state.status = "starting"
        auth_state.user = config["user"]
        auth_state.auth_url = None
        auth_state.error = None
        auth_state.close_connection()

    thread = threading.Thread(
        target=connect_with_captured_sso,
        args=(config, auth_state),
        daemon=True,
    )
    with auth_state.lock:
        auth_state.thread = thread
    thread.start()


def get_auth_snapshot(auth_state):
    with auth_state.lock:
        return {
            "status": auth_state.status,
            "auth_url": auth_state.auth_url,
            "conn": auth_state.conn,
            "error": auth_state.error,
            "user": auth_state.user,
        }


def wait_for_auth_update(auth_state):
    for _ in range(30):
        snapshot = get_auth_snapshot(auth_state)
        if snapshot["auth_url"] or snapshot["conn"] is not None or snapshot["error"]:
            return snapshot
        time.sleep(0.1)
    return get_auth_snapshot(auth_state)


def render_snowflake_sign_in():
    config = get_sso_base_config()

    if not config.get("account"):
        return get_streamlit_runtime_connection()

    if not is_local_browser_request():
        request_hostname = get_request_hostname() or "this shared host"
        st.error("Snowflake browser SSO cannot complete from this shared Streamlit URL.")
        st.info(
            "The Snowflake `externalbrowser` login redirects back to `localhost` "
            "on the browser's computer. Because this app is being viewed from "
            f"`{request_hostname}`, that callback cannot reach the Streamlit "
            "Python process."
        )
        st.warning(
            "For multiple users, deploy this app in Streamlit in Snowflake and "
            "share it from Snowsight. For local testing, each user must run the "
            "app on their own computer."
        )
        return None, None

    st.caption(
        "Local development SSO only works when this browser and the Streamlit "
        "app are running on the same computer."
    )

    snowflake_user = st.text_input(
        "Snowflake email",
        key="snowflake_user",
        placeholder="name@company.com",
    )
    snowflake_user = normalize_snowflake_user(snowflake_user)

    if not snowflake_user:
        st.info("Enter your Snowflake email to load the business list.")
        return None, None

    config["user"] = snowflake_user
    auth_state = get_session_auth_state(snowflake_user)
    snapshot = get_auth_snapshot(auth_state)

    if snapshot["conn"] is not None:
        st.success(f"Signed into Snowflake as {snowflake_user}.")
        if st.button(
            "Sign out of Snowflake",
            icon=":material/logout:",
            use_container_width=True,
        ):
            auth_state.reset()
            get_cached_businesses.clear()
            st.rerun()
        return snapshot["conn"], snowflake_user

    if snapshot["status"] == "idle":
        st.info("Start Snowflake SSO to load the business list.")
        if st.button(
            "Start Snowflake SSO",
            type="primary",
            icon=":material/login:",
            use_container_width=True,
        ):
            start_externalbrowser_auth(config, auth_state)
            snapshot = wait_for_auth_update(auth_state)
        else:
            return None, snowflake_user
    elif snapshot["status"] in {"starting", "waiting_for_sso"}:
        snapshot = wait_for_auth_update(auth_state)

    if snapshot["conn"] is not None:
        st.success(f"Signed into Snowflake as {snowflake_user}.")
        return snapshot["conn"], snowflake_user

    if snapshot["status"] == "error":
        st.error("Snowflake sign-in did not complete.")
        st.exception(snapshot["error"])
        if st.button(
            "Start Snowflake sign-in again",
            icon=":material/refresh:",
            use_container_width=True,
        ):
            auth_state.reset()
            st.rerun()
        return None, snowflake_user

    st.warning("Snowflake SSO is waiting for you to finish sign-in.")
    if snapshot["auth_url"]:
        auth_url = snapshot["auth_url"]
        st.link_button(
            "Open Snowflake SSO",
            auth_url,
            type="primary",
            icon=":material/open_in_new:",
            use_container_width=True,
        )
        st.info(
            "After the Snowflake sign-in tab says login succeeded, return here "
            "and refresh the app. The business dropdown will load for your account."
        )
    else:
        st.info("Preparing the Snowflake SSO link. Refresh the app in a moment.")
    return None, snowflake_user


@st.cache_data(ttl=3600, show_spinner=False)
def get_cached_businesses(snowflake_user, _conn):
    return businesses.load_businesses(_conn)


def select_business(conn, snowflake_user):
    try:
        with st.spinner("Loading businesses from Snowflake..."):
            businesses = get_cached_businesses(snowflake_user.lower(), conn)
    except Exception as exc:
        st.error("Could not load businesses from Snowflake.")
        st.exception(exc)
        return None, None

    if not businesses:
        st.warning("No businesses were returned from Snowflake.")
        st.session_state.pop("selected_business_name", None)
        st.session_state.pop("selected_business_id", None)
        return None, None

    business_by_id = {business["id"]: business for business in businesses}
    selected_business_id = st.selectbox(
        "Search or select business",
        options=list(business_by_id),
        index=None,
        placeholder="Search for a business",
        format_func=lambda business_id: business_by_id[business_id]["label"],
    )

    if not selected_business_id:
        st.session_state.pop("selected_business_name", None)
        st.session_state.pop("selected_business_id", None)
        return None, None

    selected_business_name = business_by_id[selected_business_id]["name"]
    st.session_state["selected_business_name"] = selected_business_name
    st.session_state["selected_business_id"] = selected_business_id
    st.caption(f"Business ID: {selected_business_id}")
    return selected_business_name, selected_business_id


with st.container(border=True, key="snowflake_panel"):
    render_section_header(
        "01",
        "Snowflake connection",
        "Connect locally for testing, or use the Snowflake-hosted app for shared access.",
        "Connection check",
    )
    conn, snowflake_user = render_snowflake_sign_in()

selected_business_name, selected_business_id = None, None

with st.container(border=True, key="business_panel"):
    render_section_header(
        "02",
        "Business",
        "Search the Snowflake business list and lock in the business ID.",
        "Ready" if conn is not None else "Waiting for sign-in",
    )
    if conn is not None:
        selected_business_name, selected_business_id = select_business(conn, snowflake_user)
    else:
        st.info("Sign into Snowflake above to search for a business.")

with st.container(border=True, key="catalog_panel"):
    render_section_header(
        "03",
        "Catalog upload",
        "Upload the workbook and generate the zero-sales catalog update.",
        "Ready" if selected_business_id else "Waiting for business",
    )
    uploaded_catalog = st.file_uploader("Upload partner catalog (.xlsx)", type=["xlsx"])

    if uploaded_catalog is not None:
        st.caption(f"Selected file: {uploaded_catalog.name}")
    elif selected_business_id:
        st.caption("Choose a partner catalog workbook to continue.")

    process_clicked = st.button(
        "Process catalog",
        type="primary",
        icon=":material/play_arrow:",
        disabled=uploaded_catalog is None or selected_business_id is None,
        use_container_width=True,
    )

if process_clicked:
    try:
        with st.spinner("Querying Snowflake for the last 24 months of sales..."):
            # selected_business_id will be used to scope this query once the
            # Snowflake business filter is finalized.
            sales_lookup = load_sales_lookup(conn=conn)

        with st.spinner("Updating workbook..."):
            updated_file, summary = update_partner_catalog(
                workbook_file=uploaded_catalog,
                sales_lookup=sales_lookup,
            )

        st.success("Workbook processed successfully.")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("UPCs in file", summary["total_rows"])
        col2.metric("UPCs with zero sales", summary["zero_sales_rows"])
        col3.metric("UPCs found in Snowflake", summary["matched_rows"])
        col4.metric("UPCs missing in Snowflake", summary["missing_rows"])

        st.download_button(
            label="Download updated workbook",
            data=updated_file.getvalue(),
            file_name="partner_catalog_updated.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            icon=":material/download:",
            use_container_width=True,
        )

        if summary["missing_upcs"]:
            with st.expander("UPCs not found in Snowflake sales data"):
                st.write(pd.DataFrame({"UPC": summary["missing_upcs"]}))

    except Exception as e:
        st.error(f"Something went wrong: {e}")
