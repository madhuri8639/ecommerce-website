from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = 'smartbuy_super_secret_key' # In production, use a secure random key

# Configuration for file uploads
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database connection function
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root', 
            password='root@123', 
            database='smartbuy_db'
        )
        return connection
    except Exception as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# Inject categories into all templates
@app.context_processor
def inject_categories():
    categories = ['Men', 'Women', 'Kids', 'Shoes', 'Accessories']
    return dict(categories=categories)

# --- HOME & SHOP ROUTES ---

@app.route('/')
def index():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        # Fetch featured products (limit to 4)
        cursor.execute("SELECT * FROM products ORDER BY created_at DESC LIMIT 4")
        featured_products = cursor.fetchall()
        conn.close()
    else:
        featured_products = []
    return render_template('index.html', featured_products=featured_products)

@app.route('/products')
def products():
    category = request.args.get('category')
    search = request.args.get('search')
    
    conn = get_db_connection()
    products = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM products WHERE 1=1"
        params = []
        
        if category:
            query += " AND category = %s"
            params.append(category)
        if search:
            query += " AND name LIKE %s"
            params.append(f"%{search}%")
            
        cursor.execute(query, tuple(params))
        products = cursor.fetchall()
        conn.close()
        
    return render_template('products.html', products=products, current_category=category)

# --- AUTH ROUTES ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        hashed_password = generate_password_hash(password)
        
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", 
                               (username, email, hashed_password))
                conn.commit()
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('login'))
            except mysql.connector.IntegrityError:
                flash('Username or Email already exists.', 'danger')
            finally:
                conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role', 'user') # 'user' or 'admin'
        
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            if role == 'admin':
                cursor.execute("SELECT * FROM admin WHERE username = %s", (username,))
                admin_user = cursor.fetchone()
                
                # Check password
                # Since admin is seeded with bcrypt, we use check_password_hash or plain string comparison if not hashed
                if admin_user:
                    is_valid = False
                    try:
                        is_valid = check_password_hash(admin_user['password'], password)
                    except ValueError:
                        # if hashing mechanism mismatch or invalid hash
                        pass
                    if not is_valid and admin_user['password'] == password:
                         is_valid = True
                         
                    if is_valid:
                        session['admin_id'] = admin_user['id']
                        session['username'] = admin_user['username']
                        session['role'] = 'admin'
                        flash('Admin Login successful!', 'success')
                        return redirect(url_for('admin_dashboard'))
                    else:
                        flash('Invalid admin credentials.', 'danger')
                else:
                    flash('Invalid admin credentials.', 'danger')
            else:
                cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
                if user and check_password_hash(user['password'], password):
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    session['role'] = 'user'
                    flash('Login successful!', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    flash('Invalid username or password.', 'danger')
            conn.close()
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# --- CART ROUTES ---

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'user_id' not in session:
        flash('Please login to add items to cart.', 'warning')
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        # Check if product exists in cart
        cursor.execute("SELECT * FROM cart WHERE user_id = %s AND product_id = %s", (user_id, product_id))
        item = cursor.fetchone()
        
        if item:
            cursor.execute("UPDATE cart SET quantity = quantity + 1 WHERE id = %s", (item['id'],))
        else:
            cursor.execute("INSERT INTO cart (user_id, product_id) VALUES (%s, %s)", (user_id, product_id))
        
        conn.commit()
        conn.close()
        flash('Product added to cart!', 'success')
        
    return redirect(request.referrer or url_for('products'))

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        flash('Please login to view your cart.', 'warning')
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    cart_items = []
    total = 0
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT cart.id as cart_id, products.name, products.price, products.image_url, cart.quantity, products.id as product_id
            FROM cart
            JOIN products ON cart.product_id = products.id
            WHERE cart.user_id = %s
        """, (user_id,))
        cart_items = cursor.fetchall()
        for item in cart_items:
            total += item['price'] * item['quantity']
        conn.close()
        
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/remove_from_cart/<int:cart_id>')
def remove_from_cart(cart_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cart WHERE id = %s AND user_id = %s", (cart_id, session['user_id']))
        conn.commit()
        conn.close()
        flash('Item removed from cart.', 'info')
        
    return redirect(url_for('cart'))

# --- CHECKOUT & DASHBOARD ---

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    conn = get_db_connection()
    total = 0
    
    if request.method == 'POST':
        if conn:
            cursor = conn.cursor(dictionary=True)
            # Get cart items
            cursor.execute("""
                SELECT products.price, cart.quantity, cart.product_id 
                FROM cart JOIN products ON cart.product_id = products.id 
                WHERE cart.user_id = %s
            """, (user_id,))
            cart_items = cursor.fetchall()
            
            if cart_items:
                for item in cart_items:
                    total += item['price'] * item['quantity']
                
                # Create order
                cursor.execute("INSERT INTO orders (user_id, customer_name, total_amount) VALUES (%s, %s, %s)", (user_id, session.get('username'), total))
                order_id = cursor.lastrowid
                
                # Insert order items and update stock
                for item in cart_items:
                    cursor.execute("INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (%s, %s, %s, %s)",
                                   (order_id, item['product_id'], item['quantity'], item['price']))
                    cursor.execute("UPDATE products SET stock = stock - %s WHERE id = %s", (item['quantity'], item['product_id']))
                
                # Clear cart
                cursor.execute("DELETE FROM cart WHERE user_id = %s", (user_id,))
                
                conn.commit()
                flash('Order placed successfully!', 'success')
                return redirect(url_for('view_invoice', order_id=order_id))
            conn.close()
            
    # GET method
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT sum(products.price * cart.quantity) as total FROM cart JOIN products ON cart.product_id = products.id WHERE cart.user_id = %s", (user_id,))
        res = cursor.fetchone()
        total = res['total'] if res['total'] else 0
        conn.close()
        
    return render_template('checkout.html', total=total)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('role') != 'user':
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    orders = []
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM orders WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
        orders = cursor.fetchall()
        conn.close()
        
    return render_template('dashboard.html', orders=orders)

# --- ADMIN ROUTES ---

@app.route('/admin')
def admin_dashboard():
    if 'admin_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    stats = {'users': 0, 'products': 0, 'orders': 0, 'sales': 0}
    products = []
    orders = []
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT COUNT(*) as c FROM users")
        stats['users'] = cursor.fetchone()['c']
        
        cursor.execute("SELECT COUNT(*) as c FROM products")
        stats['products'] = cursor.fetchone()['c']
        
        cursor.execute("SELECT COUNT(*) as c FROM orders")
        stats['orders'] = cursor.fetchone()['c']
        
        cursor.execute("SELECT SUM(total_amount) as s FROM orders")
        res = cursor.fetchone()['s']
        stats['sales'] = res if res else 0
        
        cursor.execute("SELECT * FROM products ORDER BY created_at DESC")
        products = cursor.fetchall()
        
        cursor.execute("""
            SELECT orders.id, orders.user_id, orders.customer_name, orders.total_amount, orders.status, orders.created_at 
            FROM orders 
            ORDER BY orders.created_at DESC
        """)
        orders = cursor.fetchall()
        
        conn.close()
        
    return render_template('admin.html', stats=stats, products=products, orders=orders)

@app.route('/admin/add_product', methods=['POST'])
def add_product():
    if 'admin_id' not in session:
        return redirect(url_for('login'))
        
    name = request.form.get('name')
    description = request.form.get('description')
    category = request.form.get('category')
    price = request.form.get('price')
    stock = request.form.get('stock')
    
    image = request.files.get('image')
    image_url = ''
    if image and image.filename != '':
        filename = secure_filename(image.filename)
        upload_path = os.path.join('static', 'images', 'uploads')
        os.makedirs(upload_path, exist_ok=True)
        image.save(os.path.join(upload_path, filename))
        image_url = f"/static/images/uploads/{filename}"
    else:
        # Check if URL was provided
        image_url = request.form.get('image_url', '')

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO products (name, description, category, price, stock, image_url)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            stock = stock + VALUES(stock),
            price = VALUES(price)
        """, (name, description, category, price, stock, image_url))
        conn.commit()
        conn.close()
        flash('Product added or stock updated successfully!', 'success')
        
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_product/<int:product_id>')
def delete_product(product_id):
    if 'admin_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
        conn.commit()
        conn.close()
        flash('Product deleted successfully!', 'info')
        
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/order/<int:order_id>/status/<string:status>')
def update_order_status(order_id, status):
    if 'admin_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    if status not in ['Pending', 'Processing', 'Shipped', 'Delivered']:
        flash('Invalid status.', 'danger')
        return redirect(url_for('admin_dashboard'))
        
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE orders SET status = %s WHERE id = %s", (status, order_id))
        conn.commit()
        conn.close()
        flash(f'Order #{order_id} status updated to {status}!', 'success')
        
    return redirect(url_for('admin_dashboard'))

@app.route('/order/<int:order_id>/invoice')
def view_invoice(order_id):
    if 'user_id' not in session and 'admin_id' not in session:
        flash('Please login to view this invoice.', 'warning')
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    order = None
    items = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
        order = cursor.fetchone()
        
        if order:
            if session.get('role') != 'admin' and session.get('user_id') != order['user_id']:
                flash('Access denied.', 'danger')
                conn.close()
                return redirect(url_for('index'))
                
            cursor.execute("""
                SELECT order_items.quantity, order_items.price, products.name 
                FROM order_items 
                JOIN products ON order_items.product_id = products.id 
                WHERE order_items.order_id = %s
            """, (order_id,))
            items = cursor.fetchall()
        conn.close()
        
    if not order:
        flash('Order not found.', 'danger')
        return redirect(url_for('index'))
        
    return render_template('invoice.html', order=order, items=items)

# --- STATIC PAGES ---
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
