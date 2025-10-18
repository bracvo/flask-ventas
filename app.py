from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import os

app = Flask(__name__)
ARCHIVO_VENTAS = 'ventas.xlsx'

def crear_archivo_vacio():
    if not os.path.exists(ARCHIVO_VENTAS):
        df = pd.DataFrame(columns=['Fecha', 'Producto', 'Cantidad', 'Precio Unitario'])
        df.to_excel(ARCHIVO_VENTAS, index=False)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        fecha = request.form['fecha']
        producto = request.form['producto']
        cantidad = int(request.form['cantidad'])
        precio = float(request.form['precio'])

        crear_archivo_vacio()
        df = pd.read_excel(ARCHIVO_VENTAS, engine='openpyxl')

        nuevo = pd.DataFrame([{
            'Fecha': fecha,
            'Producto': producto,
            'Cantidad': cantidad,
            'Precio Unitario': precio
        }])

        df = pd.concat([df, nuevo], ignore_index=True)
        df.to_excel(ARCHIVO_VENTAS, index=False)

        return redirect(url_for('reporte'))

    return render_template('index.html')

@app.route('/reporte')
def reporte():
    crear_archivo_vacio()
    df = pd.read_excel(ARCHIVO_VENTAS, engine='openpyxl')

    if df.empty:
        return "No hay datos para mostrar"

    # Asegurar tipos y columnas
    df['Cantidad'] = pd.to_numeric(df['Cantidad'], errors='coerce').fillna(0)
    df['Precio Unitario'] = pd.to_numeric(df['Precio Unitario'], errors='coerce').fillna(0)

    df['Total Venta'] = df['Cantidad'] * df['Precio Unitario']

    total_vendido = float(df['Total Venta'].sum())
    producto_mas_vendido = df.groupby('Producto')['Cantidad'].sum().idxmax()

    # Ventas diarias: suma por fecha
    ventas_diarias = df.groupby('Fecha')['Total Venta'].sum().sort_index()

    # Crear detalle por fecha: lista de productos y montos para cada fecha
    ventas_detalle = (
        df.groupby(['Fecha', 'Producto'])['Total Venta']
        .sum()
        .reset_index()
    )

    detalle_por_fecha = {}
    for _, row in ventas_detalle.iterrows():
        fecha = str(row['Fecha'])
        prod = str(row['Producto'])
        monto = float(row['Total Venta'])
        detalle_por_fecha.setdefault(fecha, []).append({'product': prod, 'value': monto})

    fechas = [str(f) for f in ventas_diarias.index.tolist()]
    totales = [float(x) for x in ventas_diarias.values.tolist()]

    return render_template(
        'reporte.html',
        total_vendido=round(total_vendido, 2),
        producto_mas_vendido=producto_mas_vendido,
        fechas=fechas,
        totales=totales,
        detalle_por_fecha=detalle_por_fecha
    )

if __name__ == '__main__':
    app.run()

