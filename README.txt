ORDER & SALES INTELLIGENCE DASHBOARD

Files:
- app.py: interactive Streamlit dashboard
- requirements.txt: Python dependencies

Setup:
1. Put app.py, requirements.txt, and your original "Order Report.xlsx" in the same folder.
2. Install Python 3.10+.
3. Open a terminal in that folder and run:
   python -m pip install -r requirements.txt
   streamlit run app.py
4. Open the local URL shown in the terminal (normally http://localhost:8501).

Features:
- Dynamic sidebar filters for order/invoice dates, sales hierarchy, distributors,
  retailer type, brand, product, category, status, order type, reason, and other
  categorical columns.
- Numeric range filters and text search.
- KPIs: order value, unique orders, estimated invoice value, fulfilment,
  order quantity, invoiced quantity, unique invoices, average order value.
- Monthly trend, status mix, distributor/retailer type analysis, sales hierarchy
  ranking, product/category ranking and treemap.
- CSV export for all filtered records and KPI summary.

Important:
- The workbook is large (roughly 730k records). Initial Excel import may take a
  few minutes and needs sufficient RAM.
- Estimated Invoice Value is calculated as Invoice Quantity × Sell Rate because
  the source workbook does not expose a dedicated invoice-value column.
- The app expects the original Excel workbook beside app.py.
