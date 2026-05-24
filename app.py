#!/usr/bin/env python3
import sqlite3
import hashlib
import secrets
from datetime import datetime, date
from flask import Flask, render_template_string, request, session, redirect, url_for, flash, jsonify
from functools import wraps
from contextlib import contextmanager

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# ==================== DATABASE SETUP ====================

def init_database():
    conn = sqlite3.connect('family_intranet.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT CHECK(role IN ('admin', 'father', 'mother')) NOT NULL,
            email TEXT,
            points INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Status updates
    c.execute('''
        CREATE TABLE IF NOT EXISTS status_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            status TEXT,
            location TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Shopping items
    c.execute('''
        CREATE TABLE IF NOT EXISTS shopping_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'General',
            quantity INTEGER DEFAULT 1,
            unit TEXT,
            added_by INTEGER,
            completed_by INTEGER,
            is_completed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (added_by) REFERENCES users(id)
        )
    ''')
    
    # Meal options
    c.execute('''
        CREATE TABLE IF NOT EXISTS meal_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            emoji TEXT,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Dinner votes
    c.execute('''
        CREATE TABLE IF NOT EXISTS dinner_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            meal_id INTEGER,
            vote_date DATE DEFAULT CURRENT_DATE,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (meal_id) REFERENCES meal_options(id),
            UNIQUE(user_id, vote_date)
        )
    ''')
    
    # Chores
    c.execute('''
        CREATE TABLE IF NOT EXISTS chores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            assigned_to INTEGER,
            assigned_by INTEGER,
            due_date DATE,
            priority TEXT,
            points INTEGER DEFAULT 10,
            is_completed BOOLEAN DEFAULT 0,
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (assigned_to) REFERENCES users(id),
            FOREIGN KEY (assigned_by) REFERENCES users(id)
        )
    ''')
    
    # Announcements
    c.execute('''
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            posted_by INTEGER,
            is_pinned BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (posted_by) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    
    # Insert default data
    insert_default_users(conn)
    insert_default_meals(conn)
    insert_default_announcements(conn)
    conn.close()

def insert_default_users(conn):
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    if c.fetchone()[0] == 0:
        users = [
            ('son_admin', hashlib.sha256('admin123'.encode()).hexdigest(), 'Admin (Son)', 'admin', 'son@family.com', 100),
            ('father', hashlib.sha256('father123'.encode()).hexdigest(), 'Father (Father)', 'father', 'father@family.com', 50),
            ('mother', hashlib.sha256('mother123'.encode()).hexdigest(), 'Mother (Mother)', 'mother', 'mother@family.com', 50)
        ]
        for u in users:
            c.execute('INSERT INTO users (username, password_hash, full_name, role, email, points) VALUES (?,?,?,?,?,?)', u)
    conn.commit()

def insert_default_meals(conn):
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM meal_options')
    if c.fetchone()[0] == 0:
        meals = [('Pizza', '🍕'), ('Biriyani', '🍛'), ('Pasta', '🍝'), ('Salad', '🥗'), ('Fish Curry', '🐟'), ('Chicken Roast', '🍗')]
        for m, e in meals:
            c.execute('INSERT INTO meal_options (name, emoji) VALUES (?,?)', (m, e))
    conn.commit()

def insert_default_announcements(conn):
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM announcements')
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO announcements (title, content, posted_by, is_pinned) VALUES (?,?,?,?)', 
                  ('Welcome!', 'Family Hub is ready. Use the admin panel to manage users.', 1, 1))
    conn.commit()

@contextmanager
def get_db():
    conn = sqlite3.connect('family_intranet.db')
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except:
        conn.rollback()
        raise
    finally:
        conn.close()

# ==================== AUTH DECORATORS ====================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

# ==================== ROUTES ====================

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()
        with get_db() as conn:
            c = conn.cursor()
            c.execute('SELECT id, full_name, role FROM users WHERE username=? AND password_hash=? AND is_active=1', (username, password))
            user = c.fetchone()
            if user:
                session['user_id'] = user['id']
                session['full_name'] = user['full_name']
                session['role'] = user['role']
                flash(f'Welcome {user["full_name"]}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid credentials', 'error')
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    with get_db() as conn:
        c = conn.cursor()
        # Family status
        c.execute('SELECT u.full_name, u.role, u.points, s.status, s.location FROM users u LEFT JOIN (SELECT user_id, status, location FROM status_updates ORDER BY timestamp DESC LIMIT 1) s ON u.id=s.user_id WHERE u.is_active=1')
        family_status = c.fetchall()
        # Announcements
        c.execute('SELECT a.*, u.full_name as posted_by FROM announcements a JOIN users u ON a.posted_by=u.id ORDER BY a.is_pinned DESC, a.created_at DESC LIMIT 5')
        announcements = c.fetchall()
        # Chores
        c.execute('SELECT c.*, u.full_name as assigned_to FROM chores c JOIN users u ON c.assigned_to=u.id WHERE c.is_completed=0 ORDER BY c.due_date ASC LIMIT 10')
        chores = c.fetchall()
        # Shopping count
        c.execute('SELECT COUNT(*) as cnt FROM shopping_items WHERE is_completed=0')
        shopping_count = c.fetchone()['cnt']
        # Votes today
        c.execute('SELECT COUNT(DISTINCT user_id) as cnt FROM dinner_votes WHERE vote_date = DATE("now")')
        votes_today = c.fetchone()['cnt']
    return render_template_string(DASHBOARD_TEMPLATE, family_status=family_status, announcements=announcements, chores=chores, shopping_count=shopping_count, votes_today=votes_today, role=session['role'], username=session['full_name'])

@app.route('/shopping')
@login_required
def shopping():
    with get_db() as conn:
        c = conn.cursor()
        c.execute('SELECT s.*, u.full_name as added_by FROM shopping_items s LEFT JOIN users u ON s.added_by=u.id WHERE s.is_completed=0 ORDER BY s.created_at')
        items = c.fetchall()
        c.execute('SELECT s.*, u.full_name as completed_by FROM shopping_items s LEFT JOIN users u ON s.completed_by=u.id WHERE s.is_completed=1 ORDER BY s.completed_at DESC LIMIT 20')
        completed = c.fetchall()
    return render_template_string(SHOPPING_TEMPLATE, items=items, completed=completed)

@app.route('/api/shopping/add', methods=['POST'])
@login_required
def add_shopping_item():
    data = request.get_json()
    with get_db() as conn:
        c = conn.cursor()
        c.execute('INSERT INTO shopping_items (name, category, quantity, unit, added_by) VALUES (?,?,?,?,?)',
                  (data['name'], data.get('category', 'General'), data.get('quantity', 1), data.get('unit', ''), session['user_id']))
    return jsonify({'success': True})

@app.route('/api/shopping/complete/<int:item_id>', methods=['POST'])
@login_required
def complete_shopping_item(item_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('UPDATE shopping_items SET is_completed=1, completed_by=?, completed_at=CURRENT_TIMESTAMP WHERE id=?', (session['user_id'], item_id))
    return jsonify({'success': True})

@app.route('/api/shopping/delete/<int:item_id>', methods=['DELETE'])
@login_required
def delete_shopping_item(item_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM shopping_items WHERE id=?', (item_id,))
    return jsonify({'success': True})

@app.route('/dinner')
@login_required
def dinner():
    with get_db() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM meal_options WHERE is_active=1')
        meals = c.fetchall()
        c.execute('SELECT m.id, m.name, m.emoji, COUNT(dv.id) as votes FROM meal_options m LEFT JOIN dinner_votes dv ON m.id=dv.meal_id AND dv.vote_date=DATE("now") GROUP BY m.id')
        results = c.fetchall()
        c.execute('SELECT meal_id FROM dinner_votes WHERE user_id=? AND vote_date=DATE("now")', (session['user_id'],))
        user_vote = c.fetchone()
    return render_template_string(DINNER_TEMPLATE, meals=meals, results=results, user_vote=user_vote)

@app.route('/api/dinner/vote', methods=['POST'])
@login_required
def vote_dinner():
    data = request.get_json()
    with get_db() as conn:
        c = conn.cursor()
        c.execute('SELECT id FROM dinner_votes WHERE user_id=? AND vote_date=DATE("now")', (session['user_id'],))
        if c.fetchone():
            return jsonify({'success': False, 'error': 'Already voted'})
        c.execute('INSERT INTO dinner_votes (user_id, meal_id) VALUES (?,?)', (session['user_id'], data['meal_id']))
    return jsonify({'success': True})

@app.route('/chores')
@login_required
def chores_page():
    with get_db() as conn:
        c = conn.cursor()
        c.execute('SELECT id, full_name FROM users WHERE is_active=1')
        members = c.fetchall()
        c.execute('SELECT c.*, u.full_name as assigned_to_name, a.full_name as assigned_by_name FROM chores c JOIN users u ON c.assigned_to=u.id JOIN users a ON c.assigned_by=a.id WHERE c.is_completed=0 ORDER BY c.due_date ASC')
        active = c.fetchall()
        c.execute('SELECT c.*, u.full_name as assigned_to_name FROM chores c JOIN users u ON c.assigned_to=u.id WHERE c.is_completed=1 ORDER BY c.completed_at DESC LIMIT 20')
        completed = c.fetchall()
    return render_template_string(CHORES_TEMPLATE, members=members, active=active, completed=completed, role=session['role'])

@app.route('/api/chores/add', methods=['POST'])
@login_required
def add_chore():
    if session['role'] not in ['admin', 'father']:
        return jsonify({'success': False, 'error': 'Permission denied'})
    data = request.get_json()
    with get_db() as conn:
        c = conn.cursor()
        c.execute('INSERT INTO chores (title, assigned_to, assigned_by, due_date, priority, points) VALUES (?,?,?,?,?,?)',
                  (data['title'], data['assigned_to'], session['user_id'], data.get('due_date'), data.get('priority', 'medium'), data.get('points', 10)))
    return jsonify({'success': True})

@app.route('/api/chores/complete/<int:chore_id>', methods=['POST'])
@login_required
def complete_chore(chore_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('SELECT points, assigned_to FROM chores WHERE id=?', (chore_id,))
        chore = c.fetchone()
        if chore and (chore['assigned_to'] == session['user_id'] or session['role'] == 'admin'):
            c.execute('UPDATE chores SET is_completed=1, completed_at=CURRENT_TIMESTAMP WHERE id=?', (chore_id,))
            c.execute('UPDATE users SET points = points + ? WHERE id=?', (chore['points'], chore['assigned_to']))
            return jsonify({'success': True, 'points': chore['points']})
    return jsonify({'success': False})

@app.route('/admin')
@admin_required
def admin_panel():
    with get_db() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM users ORDER BY role, full_name')
        users = c.fetchall()
        c.execute('SELECT COUNT(*) as cnt FROM users WHERE is_active=1')
        active_users = c.fetchone()['cnt']
        c.execute('SELECT COUNT(*) as cnt FROM chores WHERE is_completed=0')
        pending_chores = c.fetchone()['cnt']
        c.execute('SELECT SUM(points) as total FROM users')
        total_points = c.fetchone()['total'] or 0
        c.execute('SELECT COUNT(*) as cnt FROM shopping_items WHERE is_completed=0')
        shopping_items = c.fetchone()['cnt']
        c.execute('SELECT COUNT(DISTINCT user_id) as cnt FROM dinner_votes WHERE vote_date=DATE("now")')
        votes_today = c.fetchone()['cnt']
    return render_template_string(ADMIN_TEMPLATE, users=users, active_users=active_users, pending_chores=pending_chores, total_points=total_points, shopping_items=shopping_items, votes_today=votes_today)

@app.route('/api/admin/user/add', methods=['POST'])
@admin_required
def add_user():
    data = request.get_json()
    password_hash = hashlib.sha256(data['password'].encode()).hexdigest()
    with get_db() as conn:
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users (username, password_hash, full_name, role, email) VALUES (?,?,?,?,?)',
                      (data['username'], password_hash, data['full_name'], data['role'], data.get('email', '')))
            return jsonify({'success': True})
        except sqlite3.IntegrityError:
            return jsonify({'success': False, 'error': 'Username exists'})

@app.route('/api/admin/user/toggle/<int:user_id>', methods=['POST'])
@admin_required
def toggle_user(user_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('UPDATE users SET is_active = NOT is_active WHERE id=?', (user_id,))
    return jsonify({'success': True})

@app.route('/api/admin/user/reset-points/<int:user_id>', methods=['POST'])
@admin_required
def reset_points(user_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute('UPDATE users SET points=0 WHERE id=?', (user_id,))
    return jsonify({'success': True})

# ==================== TEMPLATES ====================

LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head><title>Family Hub Login</title><style>
body{font-family:Arial;background:linear-gradient(135deg,#667eea,#764ba2);display:flex;justify-content:center;align-items:center;height:100vh;margin:0}
.login-box{background:white;padding:40px;border-radius:20px;width:350px;box-shadow:0 20px 60px rgba(0,0,0,0.3)}
h1{text-align:center;color:#333}
input{width:100%;padding:12px;margin:10px 0;border:2px solid #ddd;border-radius:8px}
button{width:100%;padding:12px;background:#667eea;color:white;border:none;border-radius:8px;cursor:pointer}
.flash{padding:10px;margin-bottom:10px;border-radius:8px}
.success{background:#d4edda;color:#155724}
.error{background:#f8d7da;color:#721c24}
.info{margin-top:20px;padding:15px;background:#f0f0f0;border-radius:8px;font-size:12px}
</style></head>
<body>
<div class="login-box">
<h1>🏠 Family Hub</h1>
{% with messages = get_flashed_messages(with_categories=true) %}
  {% for cat,msg in messages %}<div class="flash {{ cat }}">{{ msg }}</div>{% endfor %}
{% endwith %}
<form method="POST">
<input type="text" name="username" placeholder="Username" required>
<input type="password" name="password" placeholder="Password" required>
<button type="submit">Login</button>
</form>
<div class="info">
<strong>Demo Accounts:</strong><br>
Admin (Son): son_admin / admin123<br>
Father: harikrishnan / father123<br>
Mother: sreeja / mother123
</div>
</div>
</body>
</html>
'''

DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head><title>Dashboard</title><style>
body{font-family:Segoe UI;background:#f5f7fa;padding:20px}
.header{background:white;border-radius:15px;padding:20px;margin-bottom:20px;display:flex;justify-content:space-between;align-items:center}
.nav-links{display:flex;gap:10px;flex-wrap:wrap}
.nav-link{background:#667eea;color:white;padding:8px 15px;border-radius:8px;text-decoration:none}
.logout-btn{background:#ef4444;padding:8px 20px;border-radius:8px;color:white;text-decoration:none}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(350px,1fr));gap:20px}
.card{background:white;border-radius:15px;padding:20px;box-shadow:0 2px 10px rgba(0,0,0,0.1)}
.card h2{border-bottom:2px solid #f0f0f0;padding-bottom:10px;margin-bottom:15px}
.status-item{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #eee}
.announcement{background:#fef3c7;padding:12px;border-radius:10px;margin-bottom:10px}
.chore-item{padding:10px;background:#f9f9f9;border-radius:8px;margin-bottom:8px}
</style></head>
<body>
<div class="header">
<h1>🏠 Family Hub Dashboard</h1>
<div>
<span style="margin-right:15px">Welcome, {{ username }} ({{ role }})</span>
<a href="{{ url_for('logout') }}" class="logout-btn">Logout</a>
</div>
</div>
<div class="nav-links">
<a href="{{ url_for('dashboard') }}" class="nav-link">Dashboard</a>
<a href="{{ url_for('shopping') }}" class="nav-link">🛒 Shopping</a>
<a href="{{ url_for('dinner') }}" class="nav-link">🍽️ Dinner</a>
<a href="{{ url_for('chores_page') }}" class="nav-link">✅ Chores</a>
{% if role == 'admin' %}<a href="{{ url_for('admin_panel') }}" class="nav-link">⚙️ Admin</a>{% endif %}
</div>
<div class="grid">
<div class="card"><h2>📍 Family Status</h2>
{% for m in family_status %}<div class="status-item"><strong>{{ m.full_name }}</strong><span>{{ m.status or 'No update' }} {{ m.location or '' }} (⭐ {{ m.points }} pts)</span></div>{% endfor %}
</div>
<div class="card"><h2>📢 Announcements</h2>
{% for a in announcements %}<div class="announcement"><strong>{{ a.title }}</strong><br>{{ a.content }}<br><small>by {{ a.posted }}</small></div>{% else %}<p>No announcements</p>{% endfor %}
</div>
<div class="card"><h2>✅ Pending Chores</h2>
{% for c in chores %}<div class="chore-item"><strong>{{ c.title }}</strong><br>Assigned to: {{ c.assigned_to }}{% if c.due_date %} | Due: {{ c.due_date }}{% endif %}</div>{% else %}<p>No pending chores! 🎉</p>{% endfor %}
</div>
<div class="card"><h2>📊 Stats</h2>
<div class="status-item"><span>🛒 Shopping items:</span><strong>{{ shopping_count }}</strong></div>
<div class="status-item"><span>🍽️ Votes today:</span><strong>{{ votes_today }}</strong></div>
</div>
</div>
</body>
</html>
'''

SHOPPING_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head><title>Shopping</title><style>
body{font-family:Segoe UI;background:#f5f7fa;padding:20px}
.card{background:white;border-radius:15px;padding:20px;margin-bottom:20px}
.add-form{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:20px}
.add-form input,.add-form button{padding:10px;border-radius:8px;border:1px solid #ddd}
.add-form button{background:#10b981;color:white;border:none;cursor:pointer}
.shopping-item{display:flex;justify-content:space-between;padding:12px;background:#f9f9f9;border-radius:8px;margin-bottom:10px}
.complete-btn{background:#10b981;color:white;border:none;padding:5px 15px;border-radius:6px;cursor:pointer}
.delete-btn{background:#ef4444;color:white;border:none;padding:5px 15px;border-radius:6px;cursor:pointer}
.nav-link{background:#667eea;color:white;padding:8px 15px;border-radius:8px;text-decoration:none;display:inline-block;margin-bottom:20px}
</style></head>
<body>
<a href="{{ url_for('dashboard') }}" class="nav-link">← Back to Dashboard</a>
<div class="card"><h2>Add Item</h2>
<div class="add-form"><input type="text" id="name" placeholder="Item name"><input type="text" id="category" placeholder="Category"><input type="number" id="qty" placeholder="Qty" value="1"><button onclick="addItem()">Add</button></div>
</div>
<div class="card"><h2>Active Items</h2>
<div id="active">{% for i in items %}<div class="shopping-item"><span>{{ i.name }} ({{ i.quantity }} {{ i.unit }}) - added by {{ i.added_by }}</span><div><button class="complete-btn" onclick="complete({{ i.id }})">Complete</button> <button class="delete-btn" onclick="del({{ i.id }})">Delete</button></div></div>{% else %}<p>No items</p>{% endfor %}</div>
</div>
<div class="card"><h2>Completed</h2>
{% for i in completed %}<div class="shopping-item" style="opacity:0.7"><span>✓ {{ i.name }} (completed by {{ i.completed_by }})</span></div>{% endfor %}
</div>
<script>
async function addItem(){const name=document.getElementById('name').value;if(!name)return;await fetch('/api/shopping/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,category:document.getElementById('category').value,quantity:document.getElementById('qty').value})});location.reload()}
async function complete(id){await fetch(`/api/shopping/complete/${id}`,{method:'POST'});location.reload()}
async function del(id){if(confirm('Delete?')){await fetch(`/api/shopping/delete/${id}`,{method:'DELETE'});location.reload()}}
</script>
</body>
</html>
'''

DINNER_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head><title>Dinner Voting</title><style>
body{font-family:Segoe UI;background:#f5f7fa;padding:20px}
.card{background:white;border-radius:15px;padding:20px}
.vote-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:15px;margin-top:20px}
.vote-card{background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:20px;border-radius:15px;text-align:center;cursor:pointer}
.vote-card:hover{transform:translateY(-3px)}
.emoji{font-size:48px}
.votes{font-size:24px;font-weight:bold}
.nav-link{background:#667eea;color:white;padding:8px 15px;border-radius:8px;text-decoration:none;display:inline-block;margin-bottom:20px}
</style></head>
<body>
<a href="{{ url_for('dashboard') }}" class="nav-link">← Back</a>
<div class="card"><h2>🍽️ Vote for Tonight's Dinner</h2>
{% if user_vote %}<p style="color:green">✅ You already voted today!</p>{% endif %}
<div class="vote-grid">
{% for m in results %}<div class="vote-card" onclick="{% if not user_vote %}vote({{ m.id }}){% endif %}"><div class="emoji">{{ m.emoji }}</div><div>{{ m.name }}</div><div class="votes">{{ m.votes }} vote(s)</div></div>{% endfor %}
</div>
</div>
<script>
async function vote(mealId){const res=await fetch('/api/dinner/vote',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({meal_id:mealId})});const data=await res.json();if(data.success)location.reload();else alert(data.error)}
</script>
</body>
</html>
'''

CHORES_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head><title>Chores</title><style>
body{font-family:Segoe UI;background:#f5f7fa;padding:20px}
.card{background:white;border-radius:15px;padding:20px;margin-bottom:20px}
.add-form{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:20px}
.add-form input,.add-form select,.add-form button{padding:10px;border-radius:8px;border:1px solid #ddd}
.add-form button{background:#10b981;color:white;border:none;cursor:pointer}
.chore-item{display:flex;justify-content:space-between;padding:12px;background:#f9f9f9;border-radius:8px;margin-bottom:10px}
.complete-btn{background:#10b981;color:white;border:none;padding:5px 15px;border-radius:6px;cursor:pointer}
.nav-link{background:#667eea;color:white;padding:8px 15px;border-radius:8px;text-decoration:none;display:inline-block;margin-bottom:20px}
</style></head>
<body>
<a href="{{ url_for('dashboard') }}" class="nav-link">← Back</a>
{% if role in ['admin','father'] %}
<div class="card"><h2>Assign Chore</h2>
<div class="add-form"><input type="text" id="title" placeholder="Chore title"><select id="assigned">{% for m in members %}<option value="{{ m.id }}">{{ m.full_name }}</option>{% endfor %}</select><input type="date" id="due"><select id="priority"><option>low</option><option>medium</option><option>high</option><option>urgent</option></select><input type="number" id="points" placeholder="Points" value="10"><button onclick="addChore()">Assign</button></div>
</div>
{% endif %}
<div class="card"><h2>Active Chores</h2>
{% for c in active %}<div class="chore-item"><div><strong>{{ c.title }}</strong><br>Assigned to: {{ c.assigned_to_name }} | Due: {{ c.due_date or 'No due' }} | Priority: {{ c.priority }} | Points: {{ c.points }}</div>{% if c.assigned_to == session.user_id or role=='admin' %}<button class="complete-btn" onclick="complete({{ c.id }})">Complete</button>{% endif %}</div>{% else %}<p>No active chores</p>{% endfor %}
</div>
<div class="card"><h2>Completed Chores</h2>
{% for c in completed %}<div class="chore-item"><span>✓ {{ c.title }} (completed by {{ c.assigned_to_name }})</span></div>{% endfor %}
</div>
<script>
async function addChore(){const title=document.getElementById('title').value;if(!title)return;await fetch('/api/chores/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title,assigned_to:document.getElementById('assigned').value,due_date:document.getElementById('due').value,priority:document.getElementById('priority').value,points:document.getElementById('points').value})});location.reload()}
async function complete(id){const res=await fetch(`/api/chores/complete/${id}`,{method:'POST'});const data=await res.json();if(data.success){alert(`+${data.points} points!`);location.reload()}}
</script>
</body>
</html>
'''

ADMIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head><title>Admin Panel</title><style>
body{font-family:Segoe UI;background:#f5f7fa;padding:20px}
.card{background:white;border-radius:15px;padding:20px;margin-bottom:20px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:15px;margin-bottom:20px}
.stat{background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:20px;border-radius:15px;text-align:center}
.stat-number{font-size:36px;font-weight:bold}
table{width:100%;border-collapse:collapse}
th,td{padding:12px;text-align:left;border-bottom:1px solid #ddd}
.add-form{display:flex;gap:10px;flex-wrap:wrap;margin-top:20px}
.add-form input,.add-form select,.add-form button{padding:10px;border-radius:8px;border:1px solid #ddd}
.add-form button{background:#10b981;color:white;border:none;cursor:pointer}
.btn{padding:5px 10px;margin:0 2px;border:none;border-radius:5px;cursor:pointer}
.btn-danger{background:#ef4444;color:white}
.btn-warning{background:#f59e0b;color:white}
.nav-link{background:#667eea;color:white;padding:8px 15px;border-radius:8px;text-decoration:none;display:inline-block;margin-bottom:20px}
</style></head>
<body>
<a href="{{ url_for('dashboard') }}" class="nav-link">← Back to Dashboard</a>
<div class="stats"><div class="stat"><div class="stat-number">{{ active_users }}</div><div>Active Users</div></div><div class="stat"><div class="stat-number">{{ pending_chores }}</div><div>Pending Chores</div></div><div class="stat"><div class="stat-number">{{ total_points }}</div><div>Total Points</div></div><div class="stat"><div class="stat-number">{{ shopping_items }}</div><div>Shopping Items</div></div><div class="stat"><div class="stat-number">{{ votes_today }}</div><div>Votes Today</div></div></div>
<div class="card"><h2>User Management</h2>
<table><thead><tr><th>Name</th><th>Username</th><th>Role</th><th>Points</th><th>Status</th><th>Actions</th></tr></thead><tbody>
{% for u in users %}<tr><td>{{ u.full_name }}</td><td>{{ u.username }}</td><td>{{ u.role }}</td><td>{{ u.points }}</td><td>{% if u.is_active %}✅ Active{% else %}❌ Inactive{% endif %}</td><td><button class="btn btn-warning" onclick="toggle({{ u.id }})">Toggle</button><button class="btn btn-danger" onclick="resetPoints({{ u.id }})">Reset Points</button></td></tr>{% endfor %}
</tbody></table>
<h2>Add New User</h2>
<div class="add-form"><input type="text" id="fullName" placeholder="Full Name"><input type="text" id="username" placeholder="Username"><select id="role"><option>admin</option><option>father</option><option>mother</option></select><input type="password" id="password" placeholder="Password"><input type="email" id="email" placeholder="Email"><button onclick="addUser()">Add User</button></div>
</div>
<script>
async function toggle(id){await fetch(`/api/admin/user/toggle/${id}`,{method:'POST'});location.reload()}
async function resetPoints(id){if(confirm('Reset points?')){await fetch(`/api/admin/user/reset-points/${id}`,{method:'POST'});location.reload()}}
async function addUser(){const fullName=document.getElementById('fullName').value;const username=document.getElementById('username').value;const role=document.getElementById('role').value;const password=document.getElementById('password').value;const email=document.getElementById('email').value;if(!fullName||!username||!password){alert('Fill required fields');return}const res=await fetch('/api/admin/user/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({full_name:fullName,username,role,password,email})});const data=await res.json();if(data.success)location.reload();else alert(data.error)}
</script>
</body>
</html>
'''

if __name__ == '__main__':
    print("="*60)
    print("🏠 Starting Family Intranet (SQLite)")
    print("="*60)
    init_database()
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except:
        ip = "127.0.0.1"
    print(f"✅ Server running at: http://{ip}:8000")
    print("🔑 Logins: son_admin/admin123 | father/father123 | mother/mother123")
    app.run(host='0.0.0.0', port=8000, debug=True)
