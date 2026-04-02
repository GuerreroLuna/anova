import sqlite3
import pandas as pd
import streamlit as st
from datetime import date

print("--- 🟢 LEYENDO EL ARCHIVO DASHBOARD.PY (VERSIÓN INVENTARIO COMPLETO) ---") 

# ==========================================
# 1. CONFIGURACIÓN DE LA BASE DE DATOS
# ==========================================
def init_db():
    conn = sqlite3.connect('mini_bd.db')
    c = conn.cursor()
    
    # 1. Tabla de ventas (Historial)
    c.execute('''
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto TEXT,
            cantidad INTEGER,
            precio REAL,
            fecha DATE
        )
    ''')
    
    # 2. Nueva tabla de Inventario (Stock actual)
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventario (
            producto TEXT PRIMARY KEY,
            stock INTEGER,
            precio REAL
        )
    ''')
    
    # Inventar y poblar más inventario si la tabla está vacía
    c.execute('SELECT COUNT(*) FROM inventario')
    if c.fetchone()[0] == 0:
        productos_iniciales = [
            ('Laptop Gamer', 15, 1200.00),
            ('Mouse Inalámbrico', 100, 25.50),
            ('Teclado Mecánico', 80, 45.00),
            ('Monitor 24"', 30, 300.00),
            ('Audífonos Bluetooth', 60, 80.00),
            ('Silla Ergonómica', 20, 150.00),
            ('Escritorio de Madera', 15, 200.00),
            ('Webcam 1080p', 40, 60.00),
            ('Disco Duro 1TB', 55, 100.00),
            ('Cable HDMI 2m', 200, 15.00)
        ]
        # INSERT OR IGNORE evita duplicados si corres el script varias veces
        c.executemany('INSERT OR IGNORE INTO inventario (producto, stock, precio) VALUES (?, ?, ?)', productos_iniciales)
        conn.commit()
        
    conn.close()

# Funciones de lectura
def get_ventas():
    conn = sqlite3.connect('mini_bd.db')
    df = pd.read_sql_query("SELECT * FROM ventas", conn)
    conn.close()
    return df

def get_inventario():
    conn = sqlite3.connect('mini_bd.db')
    df = pd.read_sql_query("SELECT * FROM inventario", conn)
    conn.close()
    return df

# Funciones de escritura (Lógica de inventario)
def procesar_venta(producto, cantidad, precio, fecha):
    conn = sqlite3.connect('mini_bd.db')
    c = conn.cursor()
    # 1. Descontar del inventario
    c.execute('UPDATE inventario SET stock = stock - ? WHERE producto = ?', (cantidad, producto))
    # 2. Registrar en historial de ventas
    c.execute('INSERT INTO ventas (producto, cantidad, precio, fecha) VALUES (?, ?, ?, ?)', (producto, cantidad, precio, str(fecha)))
    conn.commit()
    conn.close()

def agregar_inventario(producto, cantidad, precio):
    conn = sqlite3.connect('mini_bd.db')
    c = conn.cursor()
    # Verificar si el producto ya existe en inventario
    c.execute('SELECT stock FROM inventario WHERE producto = ?', (producto,))
    resultado = c.fetchone()
    
    if resultado:
        # Sumar stock al existente y actualizar precio
        c.execute('UPDATE inventario SET stock = stock + ?, precio = ? WHERE producto = ?', (cantidad, precio, producto))
    else:
        # Crear producto nuevo
        c.execute('INSERT INTO inventario (producto, stock, precio) VALUES (?, ?, ?)', (producto, cantidad, precio))
    
    conn.commit()
    conn.close()

# ==========================================
# 2. MODALES (VENTANAS EMERGENTES)
# ==========================================

@st.dialog("🛒 Registrar Venta (Descuenta Stock)")
def modal_registrar_venta(df_inventario):
    st.write("Selecciona un producto para vender.")
    
    # Filtrar solo productos que tengan stock mayor a 0
    productos_disp = df_inventario[df_inventario['stock'] > 0]['producto'].tolist()
    
    if not productos_disp:
        st.warning("⚠️ No hay productos con stock disponible para vender.")
        return

    # Usamos los widgets sueltos (sin st.form) para que se actualicen dinámicamente
    producto = st.selectbox("Seleccionar Producto", productos_disp)
    
    # Buscar el stock y precio del producto seleccionado en tiempo real
    stock_actual = df_inventario[df_inventario['producto'] == producto]['stock'].values[0]
    precio_sugerido = float(df_inventario[df_inventario['producto'] == producto]['precio'].values[0])
    
    st.info(f"📦 Stock disponible: *{stock_actual} unidades*")
    
    # El max_value bloquea que vendan más de lo que hay
    cantidad = st.number_input("Cantidad a vender", min_value=1, max_value=int(stock_actual), step=1, value=1)
    precio = st.number_input("Precio de Venta Unitario ($)", min_value=0.01, step=0.5, value=precio_sugerido)
    fecha = st.date_input("Fecha de Venta", value=date.today())
    
    if st.button("Confirmar Venta", type="primary"):
        procesar_venta(producto, cantidad, precio, fecha)
        st.success("¡Venta registrada y stock descontado exitosamente!")
        st.rerun()

@st.dialog("📦 Agregar Inventario (Suma Stock)")
def modal_agregar_inventario(df_inventario):
    st.write("Agrega stock a un producto existente o registra uno nuevo.")
    
    opcion = st.radio("¿Qué deseas hacer?", ["Surtir producto existente", "Crear nuevo producto"])
    
    if opcion == "Surtir producto existente":
        if not df_inventario.empty:
            producto = st.selectbox("Seleccionar Producto", df_inventario['producto'].tolist())
            precio_sugerido = float(df_inventario[df_inventario['producto'] == producto]['precio'].values[0])
        else:
            st.warning("No hay productos. Elige la opción de crear nuevo.")
            return
    else:
        producto = st.text_input("Nombre del Nuevo Producto")
        precio_sugerido = 10.0
        
    cantidad = st.number_input("Cantidad a ingresar al stock", min_value=1, step=1, value=10)
    precio = st.number_input("Costo/Precio Unitario ($)", min_value=0.01, step=0.5, value=precio_sugerido)
    
    if st.button("Guardar en Inventario", type="primary"):
        if producto and producto.strip():
            agregar_inventario(producto.strip(), cantidad, precio)
            st.success(f"¡Se agregaron {cantidad} unidades a {producto}!")
            st.rerun()
        else:
            st.error("⚠️ El nombre del producto es obligatorio.")

# ==========================================
# 3. CONFIGURACIÓN DEL DASHBOARD
# ==========================================
def main():
    st.set_page_config(page_title="Gestión de Inventario", layout="wide")
    st.title("📦 Sistema de Inventario y Ventas")

    init_db()

    # Cargar datos
    df_ventas = get_ventas()
    df_inventario = get_inventario()
    
    if not df_ventas.empty:
        df_ventas['ingreso_total'] = df_ventas['cantidad'] * df_ventas['precio']

    # --- BARRA LATERAL (Botones de Modales) ---
    st.sidebar.header("⚙️ Operaciones")
    
    # Botón de venta (Descuenta)
    if st.sidebar.button("🛒 Registrar Venta", use_container_width=True, type="primary"):
        modal_registrar_venta(df_inventario)
        
    # Botón de entrada (Suma)
    if st.sidebar.button("📦 Entrada de Inventario", use_container_width=True):
        modal_agregar_inventario(df_inventario)

    st.sidebar.markdown("---")
    st.sidebar.info("💡 Usa el botón azul para registrar una venta y descontar mercancía. Usa el botón blanco cuando te llegue nuevo pedido de proveedores.")

    # --- PESTAÑAS (TABS) ---
    tab_inventario, tab_ventas = st.tabs(["📦 Estado del Inventario", "📊 Historial de Ventas"])

    # --- PESTAÑA 1: INVENTARIO ---
    with tab_inventario:
        col_inv1, col_inv2 = st.columns(2)
        with col_inv1:
            st.metric("Total de Productos Diferentes", f"{len(df_inventario)}")
        with col_inv2:
            st.metric("Valor Total del Stock Actual", f"${(df_inventario['stock'] * df_inventario['precio']).sum():,.2f}")
            
        st.markdown("---")
        col_tabla_inv, col_grafico_inv = st.columns(2)
        
        with col_tabla_inv:
            st.subheader("📋 Stock Disponible")
            st.dataframe(df_inventario, use_container_width=True, hide_index=True)
            
        with col_grafico_inv:
            st.subheader("📉 Unidades en Bodega")
            if not df_inventario.empty:
                st.bar_chart(data=df_inventario, x='producto', y='stock', use_container_width=True)

    # --- PESTAÑA 2: VENTAS ---
    with tab_ventas:
        if not df_ventas.empty:
            col1, col2, col3 = st.columns(3)
            col1.metric("Ingresos Históricos", f"${df_ventas['ingreso_total'].sum():,.2f}")
            col2.metric("Unidades Vendidas", f"{df_ventas['cantidad'].sum()}")
            col3.metric("Transacciones", f"{len(df_ventas)}")

            st.markdown("---")
            col_tabla, col_grafico = st.columns(2)
            
            with col_tabla:
                st.subheader("📋 Registro de Movimientos")
                st.dataframe(df_ventas, use_container_width=True, hide_index=True)
                
            with col_grafico:
                st.subheader("📈 Ingresos Generados por Producto")
                ventas_por_producto = df_ventas.groupby('producto')['ingreso_total'].sum().reset_index()
                st.bar_chart(data=ventas_por_producto, x='producto', y='ingreso_total', use_container_width=True)
        else:
            st.info("Aún no hay ventas registradas. ¡Haz tu primera venta desde la barra lateral!")

if __name__ == "__main__":
    main()