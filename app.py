from io import BytesIO
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

# -------------------------------------------------------------------
# Mamaearth-inspired Order & Sales Intelligence
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Mamaearth | Order & Sales Intelligence",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

GREEN = "#176B45"
DARK_GREEN = "#104B34"
MINT = "#EAF5EE"
PALE = "#F6FAF6"
YELLOW = "#F5C84C"
TEXT = "#20352A"
MUTED = "#66776C"
CHART_COLORS = ["#176B45", "#8DBF65", "#F5C84C", "#3C9670", "#B6D9A5", "#D9A62E"]

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] {{ font-family: 'DM Sans', sans-serif; color:{TEXT}; }}
    .stApp {{ background: linear-gradient(180deg, #F7FBF7 0%, #FFFFFF 42%); }}
    .block-container {{ padding-top: 1.25rem; padding-bottom: 2rem; max-width: 1500px; }}
    [data-testid="stHeader"] {{ background: rgba(255,255,255,0.88); }}
    [data-testid="stSidebar"] {{ background: linear-gradient(180deg, #EAF5EE 0%, #F7FAF3 100%); border-right:1px solid #D6E7D9; }}
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {{ color:{DARK_GREEN}; }}
    [data-testid="stMetric"] {{
        background:#FFFFFF; border:1px solid #DDEBE0; border-top:4px solid {GREEN};
        padding:16px 18px; border-radius:16px; box-shadow:0 5px 18px rgba(22,83,52,.06);
    }}
    [data-testid="stMetricLabel"] {{ color:{MUTED}; font-weight:600; }}
    [data-testid="stMetricValue"] {{ color:{DARK_GREEN}; font-weight:800; }}
    div.stButton > button, div.stDownloadButton > button {{
        border-radius:10px; border:1px solid {GREEN}; font-weight:700;
    }}
    div.stButton > button[kind="primary"], div.stDownloadButton > button[kind="primary"] {{
        background:{GREEN}; color:white;
    }}
    div.stButton > button:hover, div.stDownloadButton > button:hover {{
        border-color:{DARK_GREEN}; color:{DARK_GREEN};
    }}
    [data-testid="stMultiSelect"] [data-baseweb="tag"] {{
        background:{GREEN}; border:1px solid {DARK_GREEN}; border-radius:7px;
    }}
    [data-testid="stMultiSelect"] [data-baseweb="tag"] span {{ color:white !important; }}
    [data-baseweb="select"] > div {{ border-color:#B9D5C0; border-radius:9px; }}
    [data-testid="stTextInput"] input, [data-testid="stDateInput"] input {{
        border-radius:9px; border-color:#B9D5C0;
    }}
    [data-testid="stSlider"] [role="slider"] {{ background:{GREEN}; border-color:{GREEN}; }}
    [data-testid="stTabs"] button[aria-selected="true"] {{
        color:{GREEN}; border-bottom-color:{YELLOW}; font-weight:800;
    }}
    .hero {{
        background:linear-gradient(115deg, #104B34 0%, #176B45 58%, #4B9667 100%);
        padding:25px 30px; border-radius:20px; color:white; margin-bottom:18px;
        box-shadow:0 10px 26px rgba(16,75,52,.15);
    }}
    .hero h1 {{ color:white; font-size:30px; margin:0 0 5px 0; font-weight:800; }}
    .hero p {{ color:#E2F1E5; margin:0; font-size:14px; }}
    .section-kicker {{ color:{GREEN}; font-size:12px; font-weight:800; letter-spacing:1.3px; text-transform:uppercase; }}
    .filter-note {{ background:#DDEFE2; padding:10px 12px; border-radius:10px; color:{DARK_GREEN}; font-size:13px; }}
    div[data-testid="stExpander"] {{ border:1px solid #DDEBE0; border-radius:12px; background:#FFFFFF; }}
    [data-testid="stDataFrame"] {{ border:1px solid #DDEBE0; border-radius:12px; overflow:hidden; }}
    </style>
    """,
    unsafe_allow_html=True,
)

@st.cache_data(show_spinner=False, max_entries=2)
def get_excel_sheets(file_bytes: bytes):
    """Return workbook sheet names directly from the uploaded file."""
    try:
        book = pd.ExcelFile(BytesIO(file_bytes), engine="calamine")
    except Exception:
        book = pd.ExcelFile(BytesIO(file_bytes), engine="openpyxl")
    return book.sheet_names


@st.cache_data(show_spinner=False, max_entries=2)
def load_data(file_bytes: bytes, file_name: str, sheet_name: str = "") -> pd.DataFrame:
    """Read and normalize an uploaded CSV or Excel dump; no local data file required."""
    suffix = "." + file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    buffer = BytesIO(file_bytes)

    if suffix == ".csv" or suffix == "csv":
        try:
            data = pd.read_csv(buffer, low_memory=False, encoding="utf-8-sig")
        except UnicodeDecodeError:
            buffer.seek(0)
            data = pd.read_csv(buffer, low_memory=False, encoding="latin-1")
    else:
        try:
            data = pd.read_excel(buffer, sheet_name=sheet_name or 0, engine="calamine")
        except Exception:
            buffer.seek(0)
            data = pd.read_excel(buffer, sheet_name=sheet_name or 0, engine="openpyxl")

    data.columns = [str(c).strip() for c in data.columns]
    data = data.loc[:, ~data.columns.duplicated()].copy()

    for col in ("Order Date", "Invoice Date"):
        if col in data.columns:
            data[col] = pd.to_datetime(data[col], errors="coerce", dayfirst=True)

    numeric_cols = (
        "MRP", "Purchase Price", "Sell Rate", "Order Quantity",
        "Order Value", "Invoice Quantity",
    )
    for col in numeric_cols:
        if col in data.columns:
            # Handles common exported values such as "₹1,250" and "1,250".
            cleaned = data[col].astype("string").str.replace(",", "", regex=False)
            cleaned = cleaned.str.replace("₹", "", regex=False).str.strip()
            data[col] = pd.to_numeric(cleaned, errors="coerce")

    if {"Invoice Quantity", "Sell Rate"}.issubset(data.columns):
        data["Estimated Invoice Value"] = (
            data["Invoice Quantity"].fillna(0) * data["Sell Rate"].fillna(0)
        )
    if {"Order Quantity", "Invoice Quantity"}.issubset(data.columns):
        data["Quantity Gap"] = (
            data["Order Quantity"].fillna(0) - data["Invoice Quantity"].fillna(0)
        )

    for col in data.select_dtypes(include=["object", "string"]).columns:
        unique_count = data[col].nunique(dropna=True)
        if unique_count and unique_count <= min(20000, max(100, int(len(data) * .15))):
            # Normalize every category value to text first. This prevents mixed
            # values (e.g. 12345 and "AMSUB00004") from breaking PyArrow.
            data[col] = data[col].astype("string").astype("category")

    return data


def money(value):
    return "—" if pd.isna(value) else f"₹{value:,.0f}"


def distinct_values(series, limit=150):
    values = series.dropna().astype(str).unique()
    if len(values) > limit:
        return None
    return sorted(values.tolist(), key=str.casefold)


def apply_text_filter(frame, column, term):
    if term and term.strip():
        return frame[frame[column].astype("string").str.contains(
            term.strip(), case=False, na=False, regex=False
        )]
    return frame


def style_chart(fig):
    fig.update_layout(
        font=dict(family="DM Sans, sans-serif", color=TEXT),
        colorway=CHART_COLORS,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title=dict(font=dict(size=16, color=DARK_GREEN), x=0.02),
        margin=dict(l=12, r=12, t=55, b=12),
        legend_title_text="",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#E8F0E9", zeroline=False)
    fig.update_yaxes(showgrid=False, zeroline=False)
    return fig


st.markdown(
    '<div class="hero"><h1>🌿 Mamaearth Order & Sales Intelligence</h1>'
    '<p>Upload your latest order dump to explore sales, fulfilment and product performance.</p></div>',
    unsafe_allow_html=True,
)

# ------------------------------- DATA UPLOAD -------------------------------
with st.sidebar:
    st.markdown("## 🌿 Data upload")
    st.caption("Upload an order dump to refresh the dashboard.")
    uploaded_file = st.file_uploader(
        "Upload order dump",
        type=["xlsx", "xls", "xlsm", "csv"],
        help="Supported formats: Excel (.xlsx, .xls, .xlsm) and CSV.",
    )
    st.markdown("---")
    st.caption(
        "Expected data: Order Date, Order Number, Order Value, Order Quantity, "
        "Invoice Quantity, Brand Name, Category Name and sales hierarchy. "
        "Available columns are detected automatically."
    )

if uploaded_file is None:
    st.info("👈 Upload an Excel or CSV order dump from the sidebar to generate your dashboard.")
    st.stop()

file_bytes = uploaded_file.getvalue()
file_suffix = uploaded_file.name.rsplit(".", 1)[-1].lower()
selected_sheet = ""

if file_suffix != "csv":
    try:
        sheet_names = get_excel_sheets(file_bytes)
        if not sheet_names:
            st.error("No worksheets were found in this workbook.")
            st.stop()
        selected_sheet = st.selectbox("Select worksheet", sheet_names, index=0)
    except Exception as exc:
        st.error(f"Could not read this Excel workbook: {exc}")
        st.stop()

try:
    with st.spinner(f"Loading {uploaded_file.name} and preparing dashboard…"):
        df = load_data(file_bytes, uploaded_file.name, selected_sheet)
except Exception as exc:
    st.error(f"Unable to load this file. Check that it is a valid Excel or CSV dump. Details: {exc}")
    st.stop()

if df.empty:
    st.warning("The uploaded file contains no data rows.")
    st.stop()

st.markdown(
    f'<div class="filter-note">✓ <b>{uploaded_file.name}</b> loaded successfully '
    f'&nbsp;·&nbsp; <b>{len(df):,}</b> records &nbsp;·&nbsp; '
    f'<b>{len(df.columns):,}</b> columns</div>',
    unsafe_allow_html=True,
)

# ------------------------------- FILTERS -------------------------------
filtered = df.copy()
filter_count = 0
preferred = [
    "Zonal Sales Head Name", "RSM Name", "ASM Name", "SO Name",
    "Distributor Type", "Retailer Type", "Brand Name", "Category Name",
    "Sub Category Name", "Status", "Reason", "order type",
]
available_dims = [c for c in preferred if c in df.columns]
search_cols = [
    c for c in ["Distributor Name", "Retailer Name", "Product Name",
                "Order Number", "Invoice Number"] if c in df.columns
]
numeric_cols = [
    c for c in ["Order Value", "Order Quantity", "Invoice Quantity", "Sell Rate", "MRP"]
    if c in df.columns
]

# ------------------------------- TOP FILTERS -------------------------------
st.markdown('<div class="section-kicker">Business filters</div>', unsafe_allow_html=True)
st.caption("Use the filters below to refine every KPI, chart and table.")

filtered = df.copy()
filter_count = 0
filter_columns = st.columns(4)
filter_slot = 0

# Date filters
for col in ("Order Date", "Invoice Date"):
    if col in df.columns:
        dates = pd.to_datetime(df[col], errors="coerce").dropna()
        if not dates.empty:
            date_min, date_max = dates.min().date(), dates.max().date()
            with filter_columns[filter_slot % len(filter_columns)]:
                selected_range = st.date_input(
                    col, value=(date_min, date_max),
                    min_value=date_min, max_value=date_max, key=f"date_{col}",
                )
            filter_slot += 1
            if isinstance(selected_range, (tuple, list)) and len(selected_range) == 2:
                start_date, end_date = selected_range
                filtered = filtered[filtered[col].between(
                    pd.Timestamp(start_date),
                    pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
                )]
                filter_count += int(start_date != date_min or end_date != date_max)

# Business dropdowns only — quick-search text inputs have been removed.
if available_dims:
    for col in available_dims:
        values = distinct_values(df[col], limit=100000)
        if values is not None:
            with filter_columns[filter_slot % len(filter_columns)]:
                chosen_values = st.multiselect(
                    col, options=values, key=f"filter_{col}",
                    placeholder=f"All {col.lower()}",
                )
            filter_slot += 1
            if chosen_values:
                filtered = filtered[filtered[col].astype("string").isin(chosen_values)]
                filter_count += 1

# Numeric range filters
if numeric_cols:
    for col in numeric_cols:
        values = pd.to_numeric(df[col], errors="coerce").dropna()
        if values.empty or values.min() >= values.max():
            continue
        low, high = float(values.min()), float(values.max())
        with filter_columns[filter_slot % len(filter_columns)]:
            chosen_range = st.slider(
                col, min_value=low, max_value=high, value=(low, high),
                key=f"numeric_{col}",
            )
        filter_slot += 1
        filtered = filtered[pd.to_numeric(filtered[col], errors="coerce").between(
            chosen_range[0], chosen_range[1]
        )]
        filter_count += int(chosen_range != (low, high))

reset_col, _ = st.columns([1, 5])
with reset_col:
    if st.button("↻ Reset all filters", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key.startswith(("date_", "filter_", "numeric_")):
                del st.session_state[key]
        st.rerun()

# ------------------------------- KPI CARDS -------------------------------
st.markdown('<div class="section-kicker">Performance snapshot</div>', unsafe_allow_html=True)
st.caption(f"Showing **{len(filtered):,}** of **{len(df):,}** records · **{filter_count}** active filter(s)")

rows = len(filtered)
orders = filtered["Order Number"].nunique() if "Order Number" in filtered else rows
invoices = filtered["Invoice Number"].nunique() if "Invoice Number" in filtered else np.nan
order_value = filtered["Order Value"].sum(min_count=1) if "Order Value" in filtered else np.nan
order_qty = filtered["Order Quantity"].sum(min_count=1) if "Order Quantity" in filtered else np.nan
invoice_qty = filtered["Invoice Quantity"].sum(min_count=1) if "Invoice Quantity" in filtered else np.nan
invoice_value = filtered["Estimated Invoice Value"].sum(min_count=1) if "Estimated Invoice Value" in filtered else np.nan
fulfilment = invoice_qty / order_qty * 100 if pd.notna(order_qty) and order_qty else np.nan
avg_order = order_value / orders if pd.notna(order_value) and orders else np.nan

kpis = st.columns(4)
kpis[0].metric("Order value", money(order_value))
kpis[1].metric("Unique orders", f"{orders:,.0f}")
kpis[2].metric("Estimated invoice value", money(invoice_value))
kpis[3].metric("Quantity fulfilment", f"{fulfilment:,.1f}%" if pd.notna(fulfilment) else "—")

kpis2 = st.columns(4)
kpis2[0].metric("Order quantity", f"{order_qty:,.0f}" if pd.notna(order_qty) else "—")
kpis2[1].metric("Invoiced quantity", f"{invoice_qty:,.0f}" if pd.notna(invoice_qty) else "—")
kpis2[2].metric("Unique invoices", f"{invoices:,.0f}" if pd.notna(invoices) else "—")
kpis2[3].metric("Average order value", money(avg_order))

st.markdown("---")
overview, sales, products, details = st.tabs(
    ["📈 Overview", "🧑‍💼 Sales performance", "📦 Product analysis", "🧾 Data & export"]
)

with overview:
    left, right = st.columns(2)
    with left:
        if "Order Date" in filtered.columns and filtered["Order Date"].notna().any():
            metric_col = "Order Value" if "Order Value" in filtered else (
                "Order Quantity" if "Order Quantity" in filtered else None
            )
            if metric_col:
                temp = filtered.loc[filtered["Order Date"].notna(), ["Order Date", metric_col]].copy()
                temp["Month"] = temp["Order Date"].dt.to_period("M").dt.to_timestamp()
                trend = temp.groupby("Month", observed=True)[metric_col].sum().reset_index()
                fig = px.line(trend, x="Month", y=metric_col, markers=True,
                              title=f"Monthly {metric_col}")
                fig.update_traces(line=dict(width=3), marker=dict(size=7))
                st.plotly_chart(style_chart(fig), use_container_width=True)
            else:
                st.info("Add an Order Value or Order Quantity column to view the monthly trend.")
        else:
            st.info("No usable order-date values in the filtered records.")

    with right:
        mix_col = "Status" if "Status" in filtered else (
            "order type" if "order type" in filtered else None
        )
        if mix_col and not filtered.empty:
            mix = (filtered[mix_col].astype("string").fillna("Unknown")
                   .value_counts().rename_axis(mix_col).reset_index(name="Records"))
            fig = px.pie(mix, names=mix_col, values="Records", hole=.58, title=f"{mix_col} mix")
            fig.update_traces(textposition="inside", textinfo="percent")
            st.plotly_chart(style_chart(fig), use_container_width=True)
        else:
            st.info("No status or order type field is available for the mix chart.")

    left, right = st.columns(2)
    for slot, col in ((left, "Distributor Type"), (right, "Retailer Type")):
        with slot:
            if col in filtered.columns and "Order Value" in filtered.columns and not filtered.empty:
                grouped = (filtered.groupby(col, observed=True, dropna=False)["Order Value"]
                           .sum().nlargest(12).reset_index())
                fig = px.bar(grouped, x="Order Value", y=col, orientation="h",
                             title=f"Order value by {col}")
                fig.update_layout(yaxis=dict(autorange="reversed"))
                st.plotly_chart(style_chart(fig), use_container_width=True)

with sales:
    sales_dims = [c for c in [
        "Zonal Sales Head Name", "RSM Name", "ASM Name", "SO Name", "Distributor Name"
    ] if c in filtered.columns]
    if sales_dims and "Order Value" in filtered.columns and not filtered.empty:
        dim = st.selectbox("Analyse sales by", sales_dims, key="sales_dimension")
        agg = {"Order_Value": ("Order Value", "sum")}
        if "Order Number" in filtered.columns:
            agg["Orders"] = ("Order Number", "nunique")
        else:
            agg["Orders"] = ("Order Value", "size")
        grouped = (filtered.groupby(dim, observed=True, dropna=False).agg(**agg)
                   .reset_index().sort_values("Order_Value", ascending=False).head(25))
        fig = px.bar(grouped.sort_values("Order_Value"), x="Order_Value", y=dim,
                     orientation="h", title=f"Top 25 by {dim}")
        st.plotly_chart(style_chart(fig), use_container_width=True)
        st.dataframe(grouped, use_container_width=True, hide_index=True)
    else:
        st.info("Sales hierarchy and Order Value columns are required for this analysis.")

with products:
    product_dims = [c for c in [
        "Brand Name", "Category Name", "Sub Category Name", "Product Name"
    ] if c in filtered.columns]
    if product_dims and "Order Value" in filtered.columns and not filtered.empty:
        dim = st.selectbox("Analyse products by", product_dims, key="product_dimension")
        agg = {"Order_Value": ("Order Value", "sum")}
        if "Order Quantity" in filtered.columns:
            agg["Order_Quantity"] = ("Order Quantity", "sum")
        else:
            agg["Order_Quantity"] = ("Order Value", "size")
        grouped = (filtered.groupby(dim, observed=True, dropna=False).agg(**agg)
                   .reset_index().sort_values("Order_Value", ascending=False).head(30))
        left, right = st.columns(2)
        with left:
            fig = px.bar(grouped.head(15).sort_values("Order_Value"), x="Order_Value", y=dim,
                         orientation="h", title=f"Top 15 {dim}")
            st.plotly_chart(style_chart(fig), use_container_width=True)
        with right:
            treemap_data = grouped.copy()
            treemap_data[dim] = treemap_data[dim].astype("string").fillna("Unknown")
            fig = px.treemap(treemap_data, path=[dim], values="Order_Value",
                             title="Order value contribution", color="Order_Value",
                             color_continuous_scale=["#EAF5EE", "#8DBF65", "#176B45"])
            st.plotly_chart(style_chart(fig), use_container_width=True)
        st.dataframe(grouped, use_container_width=True, hide_index=True)
    else:
        st.info("Product dimensions and Order Value columns are required for this analysis.")

with details:
    st.subheader("Filtered records")
    st.caption("Preview is limited to 2,000 rows for responsiveness. CSV export includes all matching rows.")
    if filtered.empty:
        st.warning("No records match the current filters. Reset or broaden the filters to see data.")
    else:
        display_df = filtered.head(2000).copy()
        # Normalize object and categorical columns for consistent Arrow serialization.
        # Categorical columns can contain mixed numeric/string categories.
        for col in display_df.columns:
            if (display_df[col].dtype == "object"
                    or isinstance(display_df[col].dtype, pd.CategoricalDtype)):
                display_df[col] = display_df[col].astype("string")
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=440)

    csv_data = filtered.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Download filtered records (CSV)", csv_data,
        "filtered_order_report.csv", "text/csv", use_container_width=False,
        disabled=filtered.empty,
    )
    summary = pd.DataFrame([{
        "Filtered Records": rows,
        "Unique Orders": orders,
        "Unique Invoices": invoices,
        "Order Value": order_value,
        "Estimated Invoice Value": invoice_value,
        "Order Quantity": order_qty,
        "Invoice Quantity": invoice_qty,
        "Fulfilment %": fulfilment,
        "Average Order Value": avg_order,
    }])
    st.download_button(
        "⬇️ Download KPI summary (CSV)",
        summary.to_csv(index=False).encode("utf-8-sig"),
        "order_kpi_summary.csv", "text/csv",
    )

st.markdown("---")
st.caption(
    "Metric note: Estimated Invoice Value = Invoice Quantity × Sell Rate (proxy). "
    "Fulfilment = total Invoice Quantity ÷ total Order Quantity. "
    "Validate the proxy against your finance team's invoice-value definition."
)
