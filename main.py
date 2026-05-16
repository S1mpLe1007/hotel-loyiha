from flask import Flask, render_template, request, jsonify, session, redirect
from database import get_connection, init_db, check_user, register_user
import os

app = Flask(__name__)
app.secret_key = 'hotel_secret_key_2026'

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({"error": "Login qiling!", "redirect": "/login"}), 401
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({"error": "Login qiling!"}), 401
        if session.get('role') != 'admin':
            return jsonify({"error": "Ruxsat yo'q!"}), 403
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    if 'user' not in session:
        return redirect('/login')
    if session.get('role') == 'admin':
        return render_template('index.html', username=session['user'], role='admin')
    return render_template('client.html', username=session['user'], role='client')

@app.route('/login', methods=['GET'])
def login_page():
    if 'user' in session:
        return redirect('/')
    return render_template('login.html')

@app.route('/register', methods=['GET'])
def register_page():
    if 'user' in session:
        return redirect('/')
    return render_template('register.html')

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    full_name = data.get('full_name', '').strip()
    phone = data.get('phone', '').strip()

    if not username or not password or not full_name:
        return jsonify({"success": False, "message": "Barcha majburiy maydonlarni to'ldiring!"})
    if len(password) < 4:
        return jsonify({"success": False, "message": "Parol kamida 4 ta belgidan iborat bo'lishi kerak!"})

    ok, msg = register_user(username, password, full_name, phone)
    return jsonify({"success": ok, "message": msg})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({"success": False, "message": "Login va parolni kiriting!"})

    user = check_user(username, password)
    if user:
        session['user'] = username
        session['user_id'] = user['id']
        session['role'] = user['role']
        session['full_name'] = user['full_name'] or username
        return jsonify({"success": True, "role": user['role']})
    else:
        return jsonify({"success": False, "message": "Login yoki parol xato!"})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True})

@app.route('/api/hotels', methods=['GET'])
@login_required
def get_hotels():
    region = request.args.get('region', '')
    max_price = request.args.get('max_price', '')
    stars = request.args.get('stars', '')

    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM hotels WHERE 1=1"
    values = []

    if region:
        query += " AND region LIKE ?"
        values.append(f"%{region}%")
    if max_price:
        query += " AND price <= ?"
        values.append(int(max_price))
    if stars:
        query += " AND stars = ?"
        values.append(int(stars))

    cursor.execute(query, values)
    hotels = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(hotels)

@app.route('/api/hotels', methods=['POST'])
@admin_required
def add_hotel():
    data = request.json
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO hotels (name, region, price, stars, wifi, breakfast, parking, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data['name'], data['region'], int(data['price']),
        int(data['stars']),
        1 if data.get('wifi') else 0,
        1 if data.get('breakfast') else 0,
        1 if data.get('parking') else 0,
        data.get('description', '')
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return jsonify({"success": True, "id": new_id})

@app.route('/api/hotels/<int:hotel_id>', methods=['PUT'])
@admin_required
def update_hotel(hotel_id):
    data = request.json
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE hotels SET name=?, region=?, price=?, stars=?, wifi=?, breakfast=?, parking=?, description=?
        WHERE id=?
    """, (
        data['name'], data['region'], int(data['price']),
        int(data['stars']),
        1 if data.get('wifi') else 0,
        1 if data.get('breakfast') else 0,
        1 if data.get('parking') else 0,
        data.get('description', ''),
        hotel_id
    ))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/hotels/<int:hotel_id>', methods=['DELETE'])
@admin_required
def delete_hotel(hotel_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM hotels WHERE id=?", (hotel_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total, AVG(price) as avg_price FROM hotels")
    row = dict(cursor.fetchone())
    cursor.execute("SELECT COUNT(*) as cnt FROM hotels WHERE wifi=1")
    row['wifi_count'] = cursor.fetchone()['cnt']
    cursor.execute("SELECT MAX(stars) as max_stars FROM hotels")
    row['max_stars'] = cursor.fetchone()['max_stars']
    if session.get('role') == 'admin':
        cursor.execute("SELECT COUNT(*) as cnt FROM bookings")
        row['bookings_count'] = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE role='client'")
        row['clients_count'] = cursor.fetchone()['cnt']
    conn.close()
    return jsonify(row)

# ===== BOOKINGS =====
@app.route('/api/bookings', methods=['POST'])
@login_required
def create_booking():
    data = request.json
    hotel_id = data.get('hotel_id')
    check_in = data.get('check_in')
    check_out = data.get('check_out')
    guests = int(data.get('guests', 1))
    note = data.get('note', '')

    if not hotel_id or not check_in or not check_out:
        return jsonify({"success": False, "message": "Barcha maydonlarni to'ldiring!"})

    conn = get_connection()
    cursor = conn.cursor()

    # Get hotel price
    cursor.execute("SELECT price FROM hotels WHERE id=?", (hotel_id,))
    hotel = cursor.fetchone()
    if not hotel:
        conn.close()
        return jsonify({"success": False, "message": "Mehmonxona topilmadi!"})

    from datetime import datetime
    try:
        d1 = datetime.strptime(check_in, "%Y-%m-%d")
        d2 = datetime.strptime(check_out, "%Y-%m-%d")
        nights = (d2 - d1).days
        if nights <= 0:
            conn.close()
            return jsonify({"success": False, "message": "Chiqish sanasi kirish sanasidan keyin bo'lishi kerak!"})
    except:
        conn.close()
        return jsonify({"success": False, "message": "Sana formati noto'g'ri!"})

    total_price = hotel['price'] * nights

    cursor.execute("""
        INSERT INTO bookings (hotel_id, user_id, check_in, check_out, guests, total_price, note)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (hotel_id, session['user_id'], check_in, check_out, guests, total_price, note))
    conn.commit()
    booking_id = cursor.lastrowid
    conn.close()

    return jsonify({"success": True, "booking_id": booking_id, "total_price": total_price, "nights": nights})

@app.route('/api/bookings/my', methods=['GET'])
@login_required
def my_bookings():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT b.*, h.name as hotel_name, h.region, h.stars, h.price as night_price
        FROM bookings b
        JOIN hotels h ON b.hotel_id = h.id
        WHERE b.user_id = ?
        ORDER BY b.created_at DESC
    """, (session['user_id'],))
    bookings = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(bookings)

@app.route('/api/bookings/all', methods=['GET'])
@admin_required
def all_bookings():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT b.*, h.name as hotel_name, h.region, u.username, u.full_name
        FROM bookings b
        JOIN hotels h ON b.hotel_id = h.id
        JOIN users u ON b.user_id = u.id
        ORDER BY b.created_at DESC
    """)
    bookings = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(bookings)

@app.route('/api/bookings/<int:booking_id>/status', methods=['PUT'])
@admin_required
def update_booking_status(booking_id):
    data = request.json
    status = data.get('status')
    if status not in ('pending', 'confirmed', 'cancelled'):
        return jsonify({"success": False, "message": "Noto'g'ri status!"})
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE bookings SET status=? WHERE id=?", (status, booking_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/bookings/<int:booking_id>', methods=['DELETE'])
@login_required
def cancel_booking(booking_id):
    conn = get_connection()
    cursor = conn.cursor()
    if session.get('role') == 'admin':
        cursor.execute("DELETE FROM bookings WHERE id=?", (booking_id,))
    else:
        cursor.execute("DELETE FROM bookings WHERE id=? AND user_id=? AND status='pending'",
                       (booking_id, session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
