from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
import os
from apmc_helper import get_apmc_price

app = Flask(__name__)
app.secret_key = "farmtohome123"

PRODUCT_EMOJIS = {
    "tomato": "🍅", "potato": "🥔", "broccoli": "🥦", "mango": "🥭",
    "onion": "🧅", "carrot": "🥕", "banana": "🍌", "apple": "🍎",
    "rice": "🌾", "wheat": "🌾", "spinach": "🥬", "chilli": "🌶️",
    "chili": "🌶️", "cabbage": "🥬", "cucumber": "🥒", "corn": "🌽",
    "garlic": "🧄", "lemon": "🍋", "orange": "🍊", "grape": "🍇",
}
DEFAULT_EMOJI = "🌿"

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def product_photo_url(name):
    safe_name = name.lower().strip().replace(" ", "_")
    folder = os.path.join(app.root_path, "static", "images")
    for ext in ["jpg", "jpeg", "png", "webp"]:
        filepath = os.path.join(folder, f"{safe_name}.{ext}")
        if os.path.exists(filepath):
            return url_for('static', filename=f'images/{safe_name}.{ext}')
    return None

def product_emoji(name):
    name_lower = name.lower()
    for key, emoji in PRODUCT_EMOJIS.items():
        if key in name_lower:
            return emoji
    return DEFAULT_EMOJI

app.jinja_env.globals.update(product_photo_url=product_photo_url, product_emoji=product_emoji)

def get_db():
    return mysql.connector.connect(
        host="thomas.proxy.rlwy.net",
        port=11499,
        user="root",
        password="HYoUcyfJLGmfuvIrVmOcDRIILicXqNXi",
        database="railway"
    )

# ── HOME PAGE ──────────────────────────────────────────────────
@app.route("/")
def home():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.*,
               u.name AS farmer_name,
               u.avg_rating AS farmer_rating,
               u.verification_status AS farmer_verified,
               COALESCE(p.latitude, u.latitude)   AS map_lat,
               COALESCE(p.longitude, u.longitude) AS map_lng
        FROM products p
        JOIN users u ON p.farmer_id = u.id
        WHERE u.verification_status = 'verified'
        ORDER BY p.created_at DESC
    """)
    products = cursor.fetchall()
    db.close()
    return render_template("home.html", products=products)

# ── REGISTER ──────────────────────────────────────────────────
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name      = request.form["name"]
        email     = request.form["email"]
        password  = request.form["password"]
        role      = request.form["role"]
        country   = request.form.get("country", "India")
        latitude  = request.form.get("latitude") or None
        longitude = request.form.get("longitude") or None

        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO users (name, email, password, role, country, latitude, longitude) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (name, email, password, role, country, latitude, longitude)
        )
        db.commit()
        db.close()
        flash("Account created! Please upload your documents for verification.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

# ── LOGIN ─────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form["email"]
        password = request.form["password"]

        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s AND password=%s", (email, password))
        user = cursor.fetchone()
        db.close()

        if user:
            session["user_id"]     = user["id"]
            session["user_name"]   = user["name"]
            session["user_role"]   = user["role"]
            session["user_status"] = user["verification_status"]
            flash(f"Welcome, {user['name']}!", "success")
            if user["role"] == "farmer":
                return redirect(url_for("farmer_dashboard"))
            else:
                return redirect(url_for("home"))
        else:
            flash("Wrong email or password.", "danger")
    return render_template("login.html")

# ── LOGOUT ────────────────────────────────────────────────────
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# ── FORGOT PASSWORD ──────────────────────────────────────────
@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        db.close()
        if user:
            session["reset_email"] = email
            return redirect(url_for("reset_password"))
        else:
            flash("No account found with that email.", "danger")
    return render_template("forgot_password.html")

# ── RESET PASSWORD ───────────────────────────────────────────
@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    email = session.get("reset_email")
    if not email:
        return redirect(url_for("forgot_password"))
    if request.method == "POST":
        new_password = request.form["password"]
        db = get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE users SET password=%s WHERE email=%s", (new_password, email))
        db.commit()
        db.close()
        session.pop("reset_email", None)
        flash("Password updated! Please login.", "success")
        return redirect(url_for("login"))
    return render_template("reset_password.html", email=email)

# ── UPLOAD DOCUMENTS ─────────────────────────────────────────
@app.route("/upload_documents", methods=["GET", "POST"])
def upload_documents():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.method == "POST":
        user_id = session["user_id"]
        role    = session["user_role"]
        db      = get_db()
        cursor  = db.cursor()

        # Determine which docs to expect
        if role == "farmer":
            doc_types = ["aadhaar", "land_record", "fssai"]
        else:
            doc_types = ["aadhaar", "address_proof"]

        for doc_type in doc_types:
            file = request.files.get(doc_type)
            if file and file.filename:
                safe_filename = f"{user_id}_{doc_type}_{file.filename}"
                file.save(os.path.join(UPLOAD_FOLDER, safe_filename))
                # Check if already uploaded, update or insert
                cursor.execute("SELECT id FROM documents WHERE user_id=%s AND doc_type=%s", (user_id, doc_type))
                existing = cursor.fetchone()
                if existing:
                    cursor.execute("UPDATE documents SET filename=%s, status='pending' WHERE user_id=%s AND doc_type=%s",
                                   (safe_filename, user_id, doc_type))
                else:
                    cursor.execute("INSERT INTO documents (user_id, doc_type, filename) VALUES (%s,%s,%s)",
                                   (user_id, doc_type, safe_filename))

        # Set verification status to pending
        cursor.execute("UPDATE users SET verification_status='pending' WHERE id=%s", (user_id,))
        db.commit()
        db.close()
        session["user_status"] = "pending"
        flash("Documents uploaded! Please wait for admin verification.", "success")
        if role == "farmer":
            return redirect(url_for("farmer_dashboard"))
        return redirect(url_for("home"))

    return render_template("upload_documents.html")

# ── FARMER DASHBOARD ──────────────────────────────────────────
@app.route("/farmer")
def farmer_dashboard():
    if session.get("user_role") != "farmer":
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE farmer_id=%s ORDER BY created_at DESC", (session["user_id"],))
    my_products = cursor.fetchall()
    cursor.execute("SELECT latitude, longitude, verification_status, phone FROM users WHERE id=%s", (session["user_id"],))
    profile = cursor.fetchone()

    # Get uploaded documents
    cursor.execute("SELECT * FROM documents WHERE user_id=%s", (session["user_id"],))
    my_docs = {d["doc_type"]: d for d in cursor.fetchall()}
    db.close()
    return render_template("farmer.html", products=my_products, profile=profile, my_docs=my_docs)

# ── UPDATE FARMER PHONE ───────────────────────────────────────
@app.route("/update_phone", methods=["POST"])
def update_phone():
    if session.get("user_role") != "farmer":
        return redirect(url_for("login"))
    phone = request.form.get("phone", "").strip()
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE users SET phone=%s WHERE id=%s", (phone, session["user_id"]))
    db.commit()
    db.close()
    flash("WhatsApp number updated!", "success")
    return redirect(url_for("farmer_dashboard"))

# ── UPDATE FARMER LOCATION ────────────────────────────────────
@app.route("/update_location", methods=["POST"])
def update_location():
    if session.get("user_role") != "farmer":
        return redirect(url_for("login"))
    latitude  = request.form.get("latitude")
    longitude = request.form.get("longitude")
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE users SET latitude=%s, longitude=%s WHERE id=%s",
                   (latitude, longitude, session["user_id"]))
    db.commit()
    db.close()
    flash("Farm location updated!", "success")
    return redirect(url_for("farmer_dashboard"))

# ── ADD PRODUCT ───────────────────────────────────────────────
@app.route("/add_product", methods=["POST"])
def add_product():
    if session.get("user_role") != "farmer":
        return redirect(url_for("login"))
    if session.get("user_status") != "verified":
        flash("Your account must be verified before listing products.", "danger")
        return redirect(url_for("farmer_dashboard"))

    name      = request.form["name"]
    price     = request.form["price"]
    quantity  = request.form["quantity"]
    location  = request.form["location"]
    category  = request.form["category"]
    latitude  = request.form.get("latitude") or None
    longitude = request.form.get("longitude") or None

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO products (farmer_id, name, price, quantity, location, category, latitude, longitude) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (session["user_id"], name, price, quantity, location, category, latitude, longitude)
    )
    db.commit()
    db.close()
    flash(f"{name} listed successfully!", "success")
    return redirect(url_for("farmer_dashboard"))

# ── DELETE PRODUCT ────────────────────────────────────────────
@app.route("/delete_product/<int:pid>")
def delete_product(pid):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM products WHERE id=%s AND farmer_id=%s", (pid, session["user_id"]))
    db.commit()
    db.close()
    flash("Listing removed.", "success")
    return redirect(url_for("farmer_dashboard"))

# ── ORDER ─────────────────────────────────────────────────────
@app.route("/order/<int:pid>", methods=["GET", "POST"])
def order(pid):
    if not session.get("user_id"):
        return redirect(url_for("login"))
    if session.get("user_status") != "verified":
        flash("Your account must be verified before placing orders.", "danger")
        return redirect(url_for("upload_documents"))

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.*, u.name as farmer_name, u.phone as farmer_phone,
               COALESCE(p.latitude, u.latitude)   AS map_lat,
               COALESCE(p.longitude, u.longitude) AS map_lng
        FROM products p JOIN users u ON p.farmer_id=u.id WHERE p.id=%s
    """, (pid,))
    product = cursor.fetchone()

    # Fetch APMC market price
    apmc = None
    if product and product.get("location"):
        apmc = get_apmc_price(product["name"], product["location"])

    if request.method == "POST":
        quantity = int(request.form["quantity"])
        total    = quantity * float(product["price"])
        cursor2  = db.cursor()
        cursor2.execute(
            "INSERT INTO orders (buyer_id, product_id, quantity, total_price) VALUES (%s,%s,%s,%s)",
            (session["user_id"], pid, quantity, total)
        )
        db.commit()
        db.close()
        flash(f"Order placed for {product['name']}!", "success")
        return redirect(url_for("my_orders"))

    db.close()
    return render_template("order.html", product=product, apmc=apmc)

# ── MY ORDERS ─────────────────────────────────────────────────
@app.route("/orders")
def my_orders():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT o.id, o.buyer_id, o.product_id, o.quantity, o.total_price,
               o.status, o.created_at,
               p.name as product_name,
               u.name as farmer_name,
               u.id as farmer_id
        FROM orders o
        JOIN products p ON o.product_id = p.id
        JOIN users u ON p.farmer_id = u.id
        WHERE o.buyer_id = %s
        ORDER BY o.created_at DESC
    """, (session["user_id"],))
    orders = cursor.fetchall()

    # Check which orders already have a rating
    for o in orders:
        cursor2 = db.cursor(dictionary=True)
        cursor2.execute(
            "SELECT rating FROM ratings WHERE buyer_id=%s AND farmer_id=%s",
            (session["user_id"], o["farmer_id"])
        )
        existing = cursor2.fetchone()
        o["already_rated"] = bool(existing)
        o["my_rating"] = existing["rating"] if existing else None
        cursor2.close()
    db.close()
    return render_template("orders.html", orders=orders)

# ── RATE FARMER ───────────────────────────────────────────────
@app.route("/rate_farmer", methods=["POST"])
def rate_farmer():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    farmer_id = request.form.get("farmer_id")
    rating    = request.form.get("rating")
    review    = request.form.get("review", "")

    db = get_db()
    cursor = db.cursor()
    # Save rating
    cursor.execute(
        "INSERT INTO ratings (buyer_id, farmer_id, rating, review) VALUES (%s,%s,%s,%s)",
        (session["user_id"], farmer_id, rating, review)
    )
    # Update farmer's avg_rating
    cursor.execute("""
        UPDATE users SET avg_rating = (
            SELECT AVG(rating) FROM ratings WHERE farmer_id=%s
        ) WHERE id=%s
    """, (farmer_id, farmer_id))
    db.commit()
    db.close()
    flash("Thank you for your rating! ⭐", "success")
    return redirect(url_for("my_orders"))

# ── FARMER ORDERS ─────────────────────────────────────────────
@app.route("/farmer_orders")
def farmer_orders():
    if session.get("user_role") != "farmer":
        return redirect(url_for("login"))
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT o.*, p.name as product_name, u.name as buyer_name
        FROM orders o
        JOIN products p ON o.product_id = p.id
        JOIN users u ON o.buyer_id = u.id
        WHERE p.farmer_id = %s
        ORDER BY o.created_at DESC
    """, (session["user_id"],))
    orders = cursor.fetchall()
    db.close()
    return render_template("farmer_orders.html", orders=orders)

# ── UPDATE ORDER STATUS ───────────────────────────────────────
@app.route("/update_order/<int:oid>/<status>")
def update_order(oid, status):
    if session.get("user_role") != "farmer":
        return redirect(url_for("login"))
    if status not in ["pending", "confirmed", "delivered"]:
        return redirect(url_for("farmer_orders"))
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        UPDATE orders o JOIN products p ON o.product_id = p.id
        SET o.status = %s WHERE o.id = %s AND p.farmer_id = %s
    """, (status, oid, session["user_id"]))
    db.commit()
    db.close()
    flash(f"Order marked as {status}!", "success")
    return redirect(url_for("farmer_orders"))

# ══════════════════════════════════════════════════════════════
# ADMIN ROUTES
# ══════════════════════════════════════════════════════════════

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email    = request.form["email"]
        password = request.form["password"]
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admins WHERE email=%s AND password=%s", (email, password))
        admin = cursor.fetchone()
        db.close()
        if admin:
            session["admin_id"]   = admin["id"]
            session["admin_name"] = admin["name"]
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Wrong admin credentials.", "danger")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_id", None)
    session.pop("admin_name", None)
    return redirect(url_for("admin_login"))

@app.route("/admin")
def admin_dashboard():
    if not session.get("admin_id"):
        return redirect(url_for("admin_login"))
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE verification_status='pending' ORDER BY created_at DESC")
    pending_users = cursor.fetchall()
    cursor.execute("SELECT * FROM users WHERE verification_status='verified' ORDER BY created_at DESC")
    verified_users = cursor.fetchall()
    cursor.execute("SELECT * FROM users WHERE verification_status='rejected' ORDER BY created_at DESC")
    rejected_users = cursor.fetchall()
    db.close()
    return render_template("admin_dashboard.html",
                           pending_users=pending_users,
                           verified_users=verified_users,
                           rejected_users=rejected_users)

@app.route("/admin/user/<int:uid>")
def admin_view_user(uid):
    if not session.get("admin_id"):
        return redirect(url_for("admin_login"))
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id=%s", (uid,))
    user = cursor.fetchone()
    cursor.execute("SELECT * FROM documents WHERE user_id=%s", (uid,))
    docs = cursor.fetchall()
    db.close()
    return render_template("admin_view_user.html", user=user, docs=docs)

@app.route("/admin/verify/<int:uid>/<action>")
def admin_verify(uid, action):
    if not session.get("admin_id"):
        return redirect(url_for("admin_login"))
    if action not in ["verified", "rejected"]:
        return redirect(url_for("admin_dashboard"))
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE users SET verification_status=%s WHERE id=%s", (action, uid))
    if action == "verified":
        cursor.execute("UPDATE documents SET status='approved' WHERE user_id=%s", (uid,))
    else:
        cursor.execute("UPDATE documents SET status='rejected' WHERE user_id=%s", (uid,))
    db.commit()
    db.close()
    flash(f"User {'verified ✅' if action == 'verified' else 'rejected ❌'}!", "success")
    return redirect(url_for("admin_dashboard"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)