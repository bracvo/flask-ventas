from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import os

app = Flask(__name__)
SALES_FILE = 'sales.xlsx'

def create_empty_file():
    """Create an empty Excel file with the correct columns if it doesn’t exist."""
    if not os.path.exists(SALES_FILE):
        df = pd.DataFrame(columns=['Date', 'Product', 'Quantity', 'Unit Price'])
        df.to_excel(SALES_FILE, index=False)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        date = request.form['fecha']
        product = request.form['producto']
        quantity = int(request.form['cantidad'])
        price = float(request.form['precio'])

        create_empty_file()
        df = pd.read_excel(SALES_FILE, engine='openpyxl')

        new_entry = pd.DataFrame([{
            'Date': date,
            'Product': product,
            'Quantity': quantity,
            'Unit Price': price
        }])

        df = pd.concat([df, new_entry], ignore_index=True)
        df.to_excel(SALES_FILE, index=False)

        return redirect(url_for('report'))

    return render_template('index.html')

@app.route('/reporte')
def report():
    create_empty_file()
    df = pd.read_excel(SALES_FILE, engine='openpyxl')

    if df.empty:
        return "No data available to display."

    # Ensure data types and calculate totals
    df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0)
    df['Unit Price'] = pd.to_numeric(df['Unit Price'], errors='coerce').fillna(0)

    df['Total Sale'] = df['Quantity'] * df['Unit Price']

    total_sales = float(df['Total Sale'].sum())
    best_selling_product = df.groupby('Product')['Quantity'].sum().idxmax()

    # Daily sales summary
    daily_sales = df.groupby('Date')['Total Sale'].sum().sort_index()

    # Detailed data per date
    sales_detail = (
        df.groupby(['Date', 'Product'])['Total Sale']
        .sum()
        .reset_index()
    )

    detail_per_date = {}
    for _, row in sales_detail.iterrows():
        date = str(row['Date'])
        product = str(row['Product'])
        amount = float(row['Total Sale'])
        detail_per_date.setdefault(date, []).append({'product': product, 'value': amount})

    dates = [str(f) for f in daily_sales.index.tolist()]
    totals = [float(x) for x in daily_sales.values.tolist()]

    return render_template(
        'reporte.html',
        total_sales=round(total_sales, 2),
        best_selling_product=best_selling_product,
        dates=dates,
        totals=totals,
        detail_per_date=detail_per_date
    )

if __name__ == '__main__':
    app.run()
