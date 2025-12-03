from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import pandas as pd
import os
from datetime import datetime, date
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Configuración
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-123')
SALES_FILE = 'sales.xlsx'
BACKUP_DIR = 'backups'
REQUIRED_COLUMNS = ['Date', 'Product', 'Quantity', 'Unit Price']

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Modelos de datos
@dataclass
class SaleRecord:
    """Clase para representar un registro de venta"""
    date: str
    product: str
    quantity: int
    unit_price: float
    
    def to_dict(self) -> Dict:
        """Convertir a diccionario"""
        return {
            'Date': self.date,
            'Product': self.product,
            'Quantity': self.quantity,
            'Unit Price': self.unit_price
        }
    
    @property
    def total(self) -> float:
        """Calcular el total de la venta"""
        return self.quantity * self.unit_price

class SalesDataManager:
    """Gestor de datos de ventas"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.ensure_file_exists()
    
    def ensure_file_exists(self) -> None:
        """Crear archivo si no existe"""
        if not os.path.exists(self.file_path):
            # Solo crear directorios si la ruta contiene subdirectorios
            dir_path = os.path.dirname(self.file_path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            
            df = pd.DataFrame(columns=REQUIRED_COLUMNS)
            df.to_excel(self.file_path, index=False)
            logger.info(f"Archivo creado: {self.file_path}")
    
    def read_data(self) -> pd.DataFrame:
        """Leer datos del archivo"""
        try:
            df = pd.read_excel(self.file_path, engine='openpyxl')
            # Validar columnas requeridas
            for col in REQUIRED_COLUMNS:
                if col not in df.columns:
                    raise ValueError(f"Columna faltante: {col}")
            return df
        except Exception as e:
            logger.error(f"Error leyendo archivo: {e}")
            return pd.DataFrame(columns=REQUIRED_COLUMNS)
    
    def add_sale(self, sale: SaleRecord) -> bool:
        """Agregar una nueva venta"""
        try:
            df = self.read_data()
            
            # Validar datos
            if not self._validate_sale_data(sale):
                return False
            
            # Agregar nuevo registro
            new_row = sale.to_dict()
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            
            # Guardar
            df.to_excel(self.file_path, index=False)
            
            # Crear backup periódico
            self._create_backup_if_needed()
            
            logger.info(f"Venta agregada: {sale.product} - Cantidad: {sale.quantity}")
            return True
            
        except Exception as e:
            logger.error(f"Error agregando venta: {e}")
            return False
    
    def _validate_sale_data(self, sale: SaleRecord) -> bool:
        """Validar datos de la venta"""
        try:
            # Validar fecha
            datetime.strptime(sale.date, '%Y-%m-%d')
            
            # Validar cantidades
            if sale.quantity <= 0:
                raise ValueError("La cantidad debe ser mayor a 0")
            
            if sale.unit_price <= 0:
                raise ValueError("El precio unitario debe ser mayor a 0")
            
            return True
            
        except ValueError as e:
            logger.warning(f"Datos inválidos: {e}")
            return False
    
    def _create_backup_if_needed(self) -> None:
        """Crear backup del archivo"""
        try:
            # Asegurar que existe el directorio de backups
            if not os.path.exists(BACKUP_DIR):
                os.makedirs(BACKUP_DIR, exist_ok=True)
                
            today = date.today().isoformat()
            backup_file = os.path.join(BACKUP_DIR, f"sales_backup_{today}.xlsx")
            
            # Crear backup solo una vez al día
            if not os.path.exists(backup_file):
                import shutil
                shutil.copy2(self.file_path, backup_file)
                logger.info(f"Backup creado: {backup_file}")
                
        except Exception as e:
            logger.error(f"Error creando backup: {e}")
    
    def get_sales_summary(self) -> Dict:
        """Obtener resumen de ventas"""
        df = self.read_data()
        
        if df.empty:
            return {
                'total_sales': 0,
                'best_selling_product': 'No hay datos',
                'daily_sales': {'dates': [], 'totals': []},
                'sales_by_product': [],
                'all_sales': [],
                'stats': {
                    'total_transactions': 0,
                    'avg_sale_value': 0,
                    'total_quantity': 0,
                    'unique_products': 0
                }
            }
        
        # Limpiar y preparar datos
        df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0)
        df['Unit Price'] = pd.to_numeric(df['Unit Price'], errors='coerce').fillna(0)
        df['Total Sale'] = df['Quantity'] * df['Unit Price']
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        
        # Calcular estadísticas
        total_sales = float(df['Total Sale'].sum())
        
        # Mejor producto vendido por cantidad
        product_sales = df.groupby('Product')['Quantity'].sum()
        best_selling_product = product_sales.idxmax() if not product_sales.empty else 'N/A'
        
        # Ventas diarias
        daily_sales = df.groupby(df['Date'].dt.date)['Total Sale'].sum().sort_index()
        
        # Ventas por producto
        sales_by_product = df.groupby('Product').agg({
            'Quantity': 'sum',
            'Total Sale': 'sum'
        }).reset_index()
        
        # Todas las ventas para la tabla detallada
        all_sales = []
        for _, row in df.iterrows():
            all_sales.append({
                'date': row['Date'].strftime('%Y-%m-%d') if hasattr(row['Date'], 'strftime') else str(row['Date']),
                'product': row['Product'],
                'quantity': int(row['Quantity']),
                'unit_price': float(row['Unit Price']),
                'total': float(row['Total Sale'])
            })
        
        # Estadísticas adicionales
        avg_sale_value = float(df['Total Sale'].mean()) if not df.empty else 0
        total_quantity = int(df['Quantity'].sum())
        
        return {
            'total_sales': round(total_sales, 2),
            'best_selling_product': best_selling_product,
            'daily_sales': {
                'dates': [d.isoformat() for d in daily_sales.index],
                'totals': [round(float(x), 2) for x in daily_sales.values]
            },
            'sales_by_product': [
                {
                    'product': row['Product'],
                    'quantity': int(row['Quantity']),
                    'total': round(float(row['Total Sale']), 2)
                }
                for _, row in sales_by_product.iterrows()
            ],
            'all_sales': all_sales,
            'stats': {
                'total_transactions': len(df),
                'avg_sale_value': round(avg_sale_value, 2),
                'total_quantity': total_quantity,
                'unique_products': df['Product'].nunique()
            }
        }

# Inicializar gestor de datos
sales_manager = SalesDataManager(SALES_FILE)

# Rutas
@app.route('/', methods=['GET', 'POST'])
def index():
    """Página principal para agregar ventas"""
    if request.method == 'POST':
        try:
            # Validar campos requeridos
            required_fields = ['fecha', 'producto', 'cantidad', 'precio']
            for field in required_fields:
                if not request.form.get(field):
                    flash(f'El campo {field} es requerido', 'error')
                    return render_template('index.html')
            
            # Crear objeto SaleRecord
            sale = SaleRecord(
                date=request.form['fecha'],
                product=request.form['producto'].strip(),
                quantity=int(request.form['cantidad']),
                unit_price=float(request.form['precio'])
            )
            
            # Agregar venta
            if sales_manager.add_sale(sale):
                flash('Venta agregada exitosamente', 'success')
                return redirect(url_for('report'))
            else:
                flash('Error al agregar la venta. Verifica los datos.', 'error')
                
        except ValueError as e:
            flash(f'Error en los datos: {str(e)}', 'error')
        except Exception as e:
            logger.error(f"Error procesando formulario: {e}")
            flash('Ocurrió un error inesperado', 'error')
    
    # Fecha por defecto para el formulario (hoy)
    default_date = date.today().isoformat()
    return render_template('index.html', default_date=default_date)

@app.route('/reporte')
def report():
    """Página de reportes"""
    try:
        summary = sales_manager.get_sales_summary()
        return render_template('reporte.html', **summary)
    except Exception as e:
        logger.error(f"Error generando reporte: {e}")
        flash('Error al generar el reporte', 'error')
        return redirect(url_for('index'))

@app.errorhandler(404)
def page_not_found(e):
    """Manejador de error 404"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    """Manejador de error 500"""
    logger.error(f"Error 500: {e}")
    return render_template('500.html'), 500

@app.context_processor
def utility_processor():
    """Procesador de contexto para funciones útiles en templates"""
    return {
        'current_year': datetime.now().year,
        'format_currency': lambda x: f"${x:,.2f}",
        'format_date': lambda d: d.strftime('%d/%m/%Y') if hasattr(d, 'strftime') else str(d),
        'zip': zip  # Agregar función zip para Jinja2
    }

if __name__ == '__main__':
    app.run(debug=True, port=5000)