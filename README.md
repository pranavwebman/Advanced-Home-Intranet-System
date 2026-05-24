```markdown
# 🏠 Family Intranet – Home Management System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3-blue.svg)](https://sqlite.org/)

A complete home intranet system for families – **shopping lists, chore management, dinner voting, announcements**, and **role‑based access** (Admin / Father / Mother). Perfect for running on a Raspberry Pi, old laptop, or any Ubuntu system inside your home network.

<p align="center">
  <img src="https://via.placeholder.com/800x400?text=Family+Hub+Screenshot" alt="Dashboard Screenshot" width="80%">
</p>

---

## ✨ Features

| Module | Description |
|--------|-------------|
| 👑 **Role‑based Access** | `Admin` (full control), `Father` (can assign chores), `Mother` (view & participate) |
| 📍 **Family Status** | Track who is home, at work, school, etc. |
| 🛒 **Shopping List** | Add, complete, delete items – with categories and quantities |
| 🍽️ **Dinner Voting** | One vote per person per day – live results |
| ✅ **Chore Management** | Assign chores with due dates, priority, points – gamified |
| 📢 **Announcements** | Pin important messages to the dashboard |
| ⚙️ **Admin Panel** | Add/remove users, toggle active status, reset points, view system stats |
| 🔐 **Secure Login** | Passwords hashed with SHA‑256 |
| 🗄️ **SQLite Database** | No external database server – single file, zero config |
| 📱 **Responsive** | Works on phones, tablets, desktops |

---

## 🚀 Quick Start (Ubuntu / Debian / Raspberry Pi OS)

### 1. Install Python & Flask

```bash
sudo apt update
sudo apt install python3 python3-pip -y
pip3 install flask
```

### 2. Download the script

```bash
wget https://raw.githubusercontent.com/pranavwebman/family-intranet/main/family_intranet.py
# or create the file manually
```

### 3. Run the application

```bash
python3 family_intranet.py
```

You will see:

```
============================================================
🏠 Starting Family Intranet (SQLite)
============================================================
✅ Server running at: http://192.168.1.100:8000
🔑 Logins: son_admin/admin123 | father/father123 | father/mother123
```

### 4. Access from any device

- On the host machine: `http://localhost:8000`
- On any other device in the same WiFi: `http://<HOST_IP>:8000`

---

## 🔑 Default Users

| Role     | Username       | Password  |
|----------|----------------|-----------|
| **Admin (Son)**  | `son_admin`    | `admin123`|
| **Father**       | `father` | `father123`|
| **Mother**       | `mother`       | `mother123`|

> ⚠️ Change passwords immediately after first login via the Admin panel.

---

## 🖥️ Usage & Navigation

After logging in, the dashboard shows:

- Family status (who is where, points earned)
- Recent announcements
- Pending chores
- Quick stats

Use the top navigation bar:

- **🛒 Shopping** – manage your grocery list
- **🍽️ Dinner** – vote for today’s meal
- **✅ Chores** – view / complete assignments (Father & Admin can add chores)
- **⚙️ Admin** – only visible to Admin – manage users & system

---

## 🛠️ API Endpoints (for custom integrations)

All endpoints require an active session (login cookie). Use `fetch()` with credentials.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/shopping/add` | Add shopping item |
| POST | `/api/shopping/complete/<id>` | Mark item as done |
| DELETE | `/api/shopping/delete/<id>` | Remove item |
| POST | `/api/dinner/vote` | Vote for a meal (JSON: `{"meal_id": 1}`) |
| POST | `/api/chores/add` | Assign new chore (Father/Admin) |
| POST | `/api/chores/complete/<id>` | Complete a chore (earns points) |
| POST | `/api/admin/user/add` | Add new user (Admin) |
| POST | `/api/admin/user/toggle/<id>` | Activate/deactivate user (Admin) |
| POST | `/api/admin/user/reset-points/<id>` | Reset user points (Admin) |

---

## 📁 Database Schema (auto‑generated)

The file `family_intranet.db` is created automatically.

```sql
users(id, username, password_hash, full_name, role, email, points, is_active, ...)
shopping_items(id, name, category, quantity, unit, added_by, is_completed, ...)
meal_options(id, name, emoji, is_active)
dinner_votes(id, user_id, meal_id, vote_date)
chores(id, title, assigned_to, assigned_by, due_date, priority, points, is_completed)
announcements(id, title, content, posted_by, is_pinned, created_at)
```

---

## 🔧 Running as a Background Service (systemd)

Create a systemd unit so the intranet starts on boot:

```bash
sudo nano /etc/systemd/system/family-intranet.service
```

Paste:

```ini
[Unit]
Description=Family Intranet
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/your_username
ExecStart=/usr/bin/python3 /home/your_username/family_intranet.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable & start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable family-intranet
sudo systemctl start family-intranet
sudo systemctl status family-intranet
```

---

## 📸 Screenshots

*(Add your own screenshots here)*

| Dashboard | Shopping List | Dinner Voting |
|-----------|---------------|----------------|
| ![Dashboard](https://via.placeholder.com/300x200) | ![Shopping](https://via.placeholder.com/300x200) | ![Dinner](https://via.placeholder.com/300x200) |

---

## 🧪 Development & Customisation

### Change default ports
Edit the last line:
```python
app.run(host='0.0.0.0', port=8000, debug=True)
```

### Add new family members
Either through the Admin panel (web UI) or manually insert into `users` table.

### Add more meal options
Run SQL directly:
```bash
sqlite3 family_intranet.db
INSERT INTO meal_options (name, emoji) VALUES ('Burger', '🍔');
```

### Enable HTTPS (for extra security)
Use a reverse proxy like `nginx` or `caddy` with Let's Encrypt.

---

## 🤝 Contributing

Contributions are welcome!  
- Fork the repository  
- Create a feature branch  
- Submit a pull request  

Areas for improvement:
- Add calendar/events page
- Integrate with home assistant
- Email/sms reminders for chores
- Mobile push notifications

---

## 📜 License

MIT License – feel free to use, modify, and distribute.

---

## ❓ Troubleshooting

| Problem | Solution |
|---------|----------|
| `Address already in use` | Change port number in the script |
| Database locked | Stop the script, delete `family_intranet.db` (⚠️ data loss) or wait for lock to clear |
| Can't access from other devices | Check firewall: `sudo ufw allow 8000` |
| Forgot admin password | Use SQLite to reset: `UPDATE users SET password_hash = '...' WHERE role='admin';` (hash of new password) |

---

 
