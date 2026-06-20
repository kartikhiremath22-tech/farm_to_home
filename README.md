# 🌿 Farm to Home

A direct farmer-to-buyer marketplace built with Python Flask + MySQL.
No brokers. Fair prices. Fresh produce.

## 🚀 Live Demo
**Try it now:** https://farm-to-home-i77m.onrender.com

> Note: This is hosted on a free server, so it may take ~50 seconds to load on the first visit if it's been inactive. After that it runs normally.

**Test accounts:**
| Role | Email | Password |
|------|-------|----------|
| Farmer | raju@farm.com | raju123 |
| Buyer | ankit@buy.com | ankit123 |

Or click **Register** to create your own account!

## 🛠️ Tech Used
- Python (Flask)
- MySQL (hosted on Railway)
- HTML + CSS
- Deployed on Render

## ▶️ Run It Locally

### Step 1 — Install Python libraries
```
pip install flask mysql-connector-python
```

### Step 2 — Setup MySQL database
```
mysql -u root -p < database.sql
```

### Step 3 — Update your MySQL password in app.py
Open `app.py` and change this line:
```python
password="your_password"   # Change this to your MySQL password
```

### Step 4 — Run the app
```
python app.py
```

### Step 5 — Open in browser
```
http://localhost:5000
```

## 📁 Project Structure
```
farm_to_home/
├── app.py              # Main Flask app
├── database.sql        # MySQL setup
├── requirements.txt    # Python libraries
├── templates/
│   ├── base.html       # Common navbar/footer
│   ├── home.html       # Product listing page
│   ├── login.html      # Login page
│   ├── register.html   # Register page
│   ├── farmer.html     # Farmer dashboard
│   ├── order.html      # Place order page
│   └── orders.html     # View my orders
└── static/
    └── css/
        └── style.css   # All styling
```

## 👤 Test Accounts (from database.sql)
| Name | Email | Password | Role |
|------|-------|----------|------|
| Raju Kumar | raju@farm.com | raju123 | Farmer |
| Priya Devi | priya@farm.com | priya123 | Farmer |
| Ankit Sharma | ankit@buy.com | ankit123 | Buyer |

## 💡 Features
- Farmer can register, login, add/remove crop listings
- Buyer can register, login, browse products, place orders
- Farmer can view incoming orders and update status (Pending → Confirmed → Delivered)
- No broker in between — direct connection!

---
Made by Kartik Hiremath | B.Tech AI & Data Science, Parul University
