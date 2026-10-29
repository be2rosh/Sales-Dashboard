import streamlit as st
import pandas as pd
import numpy as np
import plotly as px
import plotly.graph_objects as go
from datetime import date, timedelta

st.set_page_config(page_title="Sales Intelligence Dashboard", page_icon="📊", layout="wide")

# ---------- Theme / helpers ----------
st.markdown("""
<style>
    .block-container {padding-top: 1.1rem; padding-bottom: 2rem;}
    div[data-testid="stMetric"] {background: rgba(120,120,120,0.07); border: 1px solid rgba(120,120,120,0.15); padding: 14px 16px; border-radius: 12px;}
    div[data-testid="stMetricLabel"] {font-size: .92rem;}
    .small-note {color: #777; font-size: .85rem;}
</style>
""", unsafe_allow_html=True)

st.title("📊 Sales Intelligence Dashboard")
st.caption("Interactive KPI monitoring, performance analysis, and decision support")

# ---------- Demo data ----------
@st.cache_data
def make_demo_data(n=1800, seed=17):
    rng = np.random.default_rng(seed)
    end = pd.Timestamp.today().normalize()
    start = end - pd.Timedelta(days=364)
    dates = start + pd.to_timedelta(rng.integers(0, 365, size=n), unit="D")
    regions = rng.choice(["North", "South", "East", "West", "Central"], n, p=[.24,.22,.17,.20,.17])
    categories = rng.choice(["Technology", "Furniture", "Office Supplies", "Services"], n, p=[.30,.24,.31,.15])
    segments = rng.choice(["SMB", "Mid-Market", "Enterprise", "Consumer"], n, p=[.28,.25,.20,.27])
    reps = rng.choice(["Aarav", "Diya", "Kabir", "Meera", "Ishaan", "Ananya", "Vihaan", "Sara"], n)
    products_by_cat = {
        "Technology": ["Laptop", "Monitor", "Networking Kit", "Tablet", "Accessories"],
        "Furniture": ["Office Chair", "Desk", "Storage Cabinet", "Meeting Table"],
        "Office Supplies": ["Paper", "Ink & Toner", "Stationery Kit", "Printer"],
        "Services": ["Implementation", "Support Plan", "Training", "Consulting"]
    }
    products = [rng.choice(products_by_cat[c]) for c in categories]
    price_ranges = {"Technology": (350, 1800), "Furniture": (80, 900), "Office Supplies": (8, 240), "Services": (150, 2500)}
    unit_prices = np.array([rng.uniform(*price_ranges[c]) for c in categories]).round(2)
    quantity = rng.integers(1, 13, n)
    discount = rng.choice([0, .03, .05, .08, .10, .15, .20], n, p=[.25,.10,.18,.16,.14,.11,.06])
    sales = (unit_prices * quantity * (1-discount)).round(2)
    cost_rate = rng.uniform(.52, .82, n)
    cost = (unit_prices * quantity * cost_rate).round(2)
    profit = (sales-cost).round(2)
    order_ids = [f"ORD-{i:05d}" for i in range(1, n+1)]
    customers = [f"Customer {i:03d}" for i in rng.integers(1, 251, n)]
    df = pd.DataFrame({
        "Order Date": dates, "Order ID": order_ids, "Customer": customers,
        "Region": regions, "Sales Rep": reps, "Segment": segments,
        "Category": categories, "Product": products, "Quantity": quantity,
        "Unit Price": unit_prices, "Discount": discount, "Sales": sales,
        "Cost": cost, "Profit": profit
    })
    return df.sort_values("Order Date")

def normalize_columns(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    aliases = {
        "date":"Order Date", "order_date":"Order Date", "order date":"Order Date",
        "order_id":"Order ID", "order id":"Order ID", "customer":"Customer",
        "region":"Region", "sales rep":"Sales Rep", "sales_rep":"Sales Rep",
        "segment":"Segment", "category":"Category", "product":"Product",
        "quantity":"Quantity", "unit price":"Unit Price", "unit_price":"Unit Price",
        "discount":"Discount", "sales":"Sales", "revenue":"Sales",
        "cost":"Cost", "profit":"Profit"
    }
    rename = {}
    for c in df.columns:
        key = c.lower().replace("-", "_")
        if key in aliases: rename[c] = aliases[key]
    df = df.rename(columns=rename)
    required = ["Order Date", "Sales"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error("CSV is missing required columns: " + ", ".join(missing) + ". Include at least Order Date and Sales.")
        st.stop()
    df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")
    df["Sales"] = pd.to_numeric(df["Sales"], errors="coerce")
    for c in ["Cost", "Profit", "Quantity", "Unit Price", "Discount"]:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["Order Date", "Sales"])
    if "Order ID" not in df: df["Order ID"] = [f"ROW-{i+1:05d}" for i in range(len(df))]
    if "Customer" not in df: df["Customer"] = "Unknown"
    if "Region" not in df: df["Region"] = "Unassigned"
    if "Sales Rep" not in df: df["Sales Rep"] = "Unassigned"
    if "Segment" not in df: df["Segment"] = "Unassigned"
    if "Category" not in df: df["Category"] = "Unassigned"
    if "Product" not in df: df["Product"] = "Unassigned"
    if "Quantity" not in df: df["Quantity"] = 1
    if "Cost" not in df: df["Cost"] = np.nan
    if "Profit" not in df: df["Profit"] = df["Sales"] - df["Cost"]
    if "Discount" not in df: df["Discount"] = 0
    return df

# ---------- Sidebar: data and filters ----------
with st.sidebar:
    st.header("⚙️ Dashboard controls")
    uploaded = st.file_uploader("Upload sales CSV", type=["csv"], help="Use your own data. At minimum include Order Date and Sales/Revenue.")
    st.caption("No file? Demo data is loaded automatically.")
    st.divider()

if uploaded is not None:
    try:
        raw = pd.read_csv(uploaded)
        data = normalize_columns(raw)
        data_source = f"Uploaded file · {len(data):,} valid rows"
    except Exception as e:
        st.error(f"Could not read this CSV: {e}")
        st.stop()
else:
    data = make_demo_data()
    data_source = "Illustrative demo data · replace with your own CSV for real decisions"

with st.sidebar:
    st.markdown("### Filters")
    min_d = data["Order Date"].min().date()
    max_d = data["Order Date"].max().date()
    date_range = st.date_input("Order date range", value=(min_d, max_d), min_value=min_d, max_value=max_d)
    def options(col):
        return sorted(data[col].dropna().astype(str).unique().tolist())
    selected_regions = st.multiselect("Region", options("Region"), default=options("Region"))
    selected_categories = st.multiselect("Category", options("Category"), default=options("Category"))
    selected_segments = st.multiselect("Customer segment", options("Segment"), default=options("Segment"))
    selected_reps = st.multiselect("Sales rep", options("Sales Rep"), default=options("Sales Rep"))
    selected_products = st.multiselect("Product", options("Product"), default=options("Product"))
    st.divider()
    st.caption("All visuals and KPIs respond to these filters.")

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = date_range

mask = (
    data["Order Date"].dt.date.between(start_date, end_date)
    & data["Region"].astype(str).isin(selected_regions)
    & data["Category"].astype(str).isin(selected_categories)
    & data["Segment"].astype(str).isin(selected_segments)
    & data["Sales Rep"].astype(str).isin(selected_reps)
    & data["Product"].astype(str).isin(selected_products)
)
df = data.loc[mask].copy()
if df.empty:
    st.warning("No records match these filters. Adjust your selections.")
    st.stop()

# ---------- KPI calculations ----------
revenue = df["Sales"].sum()
orders = df["Order ID"].nunique()
customers = df["Customer"].nunique()
units = df["Quantity"].sum()
has_cost = df["Cost"].notna().any()
profit = df["Profit"].sum(min_count=1) if "Profit" in df else np.nan
margin = (profit / revenue * 100) if pd.notna(profit) and revenue else np.nan
aov = revenue / orders if orders else 0
discount_pct = (df["Discount"].fillna(0).mean() * 100) if "Discount" in df else np.nan

# Previous-period comparison of equal duration
period_days = max((end_date - start_date).days + 1, 1)
prev_end = pd.Timestamp(start_date) - pd.Timedelta(days=1)
prev_start = prev_end - pd.Timedelta(days=period_days-1)
prev = data[
    data["Order Date"].dt.date.between(prev_start.date(), prev_end.date())
    & data["Region"].astype(str).isin(selected_regions)
    & data["Category"].astype(str).isin(selected_categories)
    & data["Segment"].astype(str).isin(selected_segments)
    & data["Sales Rep"].astype(str).isin(selected_reps)
    & data["Product"].astype(str).isin(selected_products)
]
prev_revenue = prev["Sales"].sum()
rev_change = ((revenue-prev_revenue)/prev_revenue*100) if prev_revenue else np.nan
prev_orders = prev["Order ID"].nunique()
order_change = ((orders-prev_orders)/prev_orders*100) if prev_orders else np.nan
prev_profit = prev["Profit"].sum(min_count=1) if len(prev) and "Profit" in prev else np.nan
profit_change = ((profit-prev_profit)/abs(prev_profit)*100) if pd.notna(profit) and pd.notna(prev_profit) and prev_profit != 0 else np.nan

def delta_text(x):
    return f"{x:+.1f}% vs previous period" if pd.notna(x) else "No comparable prior period"

st.caption(f"**Data:** {data_source}  ·  **Filtered rows:** {len(df):,}")

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Revenue", f"₹{revenue:,.0f}", delta_text(rev_change))
k2.metric("Gross profit", f"₹{profit:,.0f}" if pd.notna(profit) else "N/A", delta_text(profit_change))
k3.metric("Profit margin", f"{margin:.1f}%" if pd.notna(margin) else "N/A")
k4.metric("Orders", f"{orders:,}", delta_text(order_change))
k5.metric("Avg. order value", f"₹{aov:,.0f}")
k6.metric("Customers", f"{customers:,}")

k7, k8, k9 = st.columns(3)
k7.metric("Units sold", f"{units:,.0f}")
k8.metric("Avg. discount", f"{discount_pct:.1f}%" if pd.notna(discount_pct) else "N/A")
k9.metric("Revenue per customer", f"₹{revenue/customers:,.0f}" if customers else "N/A")

st.divider()

# ---------- Tabs ----------
tab_overview, tab_products, tab_customers, tab_reps, tab_data = st.tabs(
    ["📈 Overview", "📦 Products & mix", "👥 Customers", "🎯 Sales team", "🧾 Data explorer"]
)

with tab_overview:
    left, right = st.columns([1.7, 1])
    trend = df.copy()
    trend["Period"] = trend["Order Date"].dt.to_period("M").dt.to_timestamp()
    monthly = trend.groupby("Period", as_index=False).agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"), Orders=("Order ID", "nunique"))
    with left:
        metric_choice = st.selectbox("Trend metric", ["Revenue", "Profit", "Orders"], key="trend_metric")
        fig = px.line(monthly, x="Period", y=metric_choice, markers=True, title=f"Monthly {metric_choice.lower()} trend")
        fig.update_layout(hovermode="x unified", margin=dict(l=10,r=10,t=55,b=10), xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        region = df.groupby("Region", as_index=False).agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"))
        fig = px.bar(region.sort_values("Revenue", ascending=True), x="Revenue", y="Region", orientation="h", title="Revenue by region", text_auto=".2s")
        fig.update_layout(margin=dict(l=10,r=10,t=55,b=10), yaxis_title="", xaxis_title="Revenue")
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        daily = df.assign(Date=df["Order Date"].dt.date).groupby("Date", as_index=False)["Sales"].sum()
        fig = px.area(daily, x="Date", y="Sales", title="Daily revenue")
        fig.update_layout(margin=dict(l=10,r=10,t=55,b=10), xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        segment = df.groupby("Segment", as_index=False).agg(Revenue=("Sales","sum"))
        fig = px.pie(segment, names="Segment", values="Revenue", hole=.55, title="Revenue by customer segment")
        fig.update_layout(margin=dict(l=10,r=10,t=55,b=10))
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Decision signals")
    signals = []
    if pd.notna(margin):
        if margin < 15: signals.append(("🔴", "Margin pressure", f"Profit margin is {margin:.1f}%. Review discounting, cost-to-serve, and low-margin products."))
        elif margin < 25: signals.append(("🟠", "Margin watch", f"Profit margin is {margin:.1f}%. Compare margin by category and sales rep before increasing discounts."))
        else: signals.append(("🟢", "Healthy aggregate margin", f"Profit margin is {margin:.1f}%. Check whether high-margin segments are getting enough sales coverage."))
    if pd.notna(rev_change):
        if rev_change < -5: signals.append(("🔴", "Revenue decline", f"Revenue is down {abs(rev_change):.1f}% versus the preceding equal-length period. Inspect region and product drivers."))
        elif rev_change > 5: signals.append(("🟢", "Revenue momentum", f"Revenue is up {rev_change:.1f}% versus the preceding equal-length period. Identify repeatable drivers."))
        else: signals.append(("🟡", "Revenue broadly stable", f"Revenue changed {rev_change:+.1f}% versus the preceding equal-length period. Focus on mix, margin, and pipeline quality."))
    if discount_pct > 10:
        signals.append(("🟠", "Discount review", f"Average discount is {discount_pct:.1f}%. Check if discounted deals deliver sufficient profit."))
    if not signals: signals.append(("ℹ️", "More data needed", "Add cost/profit fields to enable margin-based signals."))
    for icon, title, detail in signals:
        st.markdown(f"**{icon} {title}** — {detail}")

with tab_products:
    c1, c2 = st.columns(2)
    with c1:
        cat = df.groupby("Category", as_index=False).agg(Revenue=("Sales","sum"), Profit=("Profit","sum"), Units=("Quantity","sum"))
        fig = px.bar(cat.sort_values("Revenue", ascending=False), x="Category", y="Revenue", color="Profit", title="Category revenue and profit", text_auto=".2s")
        fig.update_layout(margin=dict(l=10,r=10,t=55,b=10), xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        prod = df.groupby("Product", as_index=False).agg(Revenue=("Sales","sum"), Profit=("Profit","sum"), Units=("Quantity","sum"), Orders=("Order ID","nunique"))
        prod = prod.sort_values("Revenue", ascending=False).head(12)
        fig = px.bar(prod.sort_values("Revenue"), x="Revenue", y="Product", orientation="h", color="Profit", title="Top 12 products by revenue", text_auto=".2s")
        fig.update_layout(margin=dict(l=10,r=10,t=55,b=10), yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
    st.subheader("Product performance table")
    prod_table = df.groupby(["Category","Product"], as_index=False).agg(Revenue=("Sales","sum"), Profit=("Profit","sum"), Units=("Quantity","sum"), Orders=("Order ID","nunique"))
    prod_table["Margin %"] = np.where(prod_table["Revenue"] != 0, prod_table["Profit"] / prod_table["Revenue"] * 100, np.nan)
    st.dataframe(prod_table.sort_values("Revenue", ascending=False).style.format({"Revenue":"₹{:,.0f}","Profit":"₹{:,.0f}","Units":"{:,.0f}","Margin %":"{:.1f}%"}), use_container_width=True, hide_index=True)

with tab_customers:
    customer = df.groupby("Customer", as_index=False).agg(Revenue=("Sales","sum"), Profit=("Profit","sum"), Orders=("Order ID","nunique"))
    customer["AOV"] = customer["Revenue"] / customer["Orders"].replace(0, np.nan)
    c1, c2 = st.columns(2)
    with c1:
        top_n = st.slider("Number of customers to show", 5, 25, 10, key="top_customers")
        top_c = customer.nlargest(top_n, "Revenue").sort_values("Revenue")
        fig = px.bar(top_c, x="Revenue", y="Customer", orientation="h", title=f"Top {top_n} customers by revenue", color="Profit", text_auto=".2s")
        fig.update_layout(margin=dict(l=10,r=10,t=55,b=10), yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.scatter(customer, x="Orders", y="Revenue", size="Profit", hover_name="Customer", title="Customer value vs order frequency", size_max=36)
        fig.update_layout(margin=dict(l=10,r=10,t=55,b=10))
        st.plotly_chart(fig, use_container_width=True)
    st.subheader("Customer concentration")
    total_cust_rev = customer["Revenue"].sum()
    top5_share = customer.nlargest(5, "Revenue")["Revenue"].sum() / total_cust_rev * 100 if total_cust_rev else 0
    st.metric("Top 5 customers' revenue share", f"{top5_share:.1f}%")
    st.dataframe(customer.sort_values("Revenue", ascending=False).style.format({"Revenue":"₹{:,.0f}","Profit":"₹{:,.0f}","AOV":"₹{:,.0f}"}), use_container_width=True, hide_index=True)

with tab_reps:
    rep = df.groupby("Sales Rep", as_index=False).agg(Revenue=("Sales","sum"), Profit=("Profit","sum"), Orders=("Order ID","nunique"), Customers=("Customer","nunique"))
    rep["Margin %"] = np.where(rep["Revenue"] != 0, rep["Profit"] / rep["Revenue"] * 100, np.nan)
    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(rep.sort_values("Revenue"), x="Revenue", y="Sales Rep", orientation="h", color="Margin %", title="Sales rep revenue and margin", text_auto=".2s")
        fig.update_layout(margin=dict(l=10,r=10,t=55,b=10), yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.scatter(rep, x="Orders", y="Revenue", size="Profit", color="Margin %", hover_name="Sales Rep", title="Rep productivity: orders vs revenue", size_max=38)
        fig.update_layout(margin=dict(l=10,r=10,t=55,b=10))
        st.plotly_chart(fig, use_container_width=True)
    st.dataframe(rep.sort_values("Revenue", ascending=False).style.format({"Revenue":"₹{:,.0f}","Profit":"₹{:,.0f}","Margin %":"{:.1f}%"}), use_container_width=True, hide_index=True)

with tab_data:
    st.subheader("Filtered transaction records")
    search = st.text_input("Search visible rows (order, customer, product, region, rep)")
    shown = df.copy()
    if search.strip():
        searchable = shown.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False))
        shown = shown[searchable.any(axis=1)]
    st.caption(f"{len(shown):,} rows shown")
    st.dataframe(shown.sort_values("Order Date", ascending=False), use_container_width=True, hide_index=True)
    csv = shown.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download filtered data as CSV", data=csv, file_name="filtered_sales_data.csv", mime="text/csv")
    st.download_button("⬇️ Download KPI summary as CSV",
        data=pd.DataFrame([{
            "Revenue": revenue, "Profit": profit, "Profit Margin %": margin, "Orders": orders,
            "Average Order Value": aov, "Customers": customers, "Units Sold": units,
            "Average Discount %": discount_pct, "Revenue Change % vs Prior Period": rev_change
        }]).to_csv(index=False).encode("utf-8"),
        file_name="sales_kpi_summary.csv", mime="text/csv")

st.divider()
st.markdown('<p class="small-note">Decision-support note: demo figures are synthetic and not business facts. Validate data definitions, currency, returns, taxes, and cost allocation before using this dashboard for operational or financial decisions.</p>', unsafe_allow_html=True)
