from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
import os

app = Flask(__name__)
app.secret_key = "farmtohome123"

# ── Product photo lookup ──────────────────────────────────────────
# Upload your own photos to static/images/ named like: tomato.jpg, potato.jpg
# If no photo is found for a product, a matching emoji is shown instead.
PRODUCT_EMOJIS = {
    "tomato": "🍅", "potato": "🥔", "broccoli": "🥦", "mango": "🥭",
    "onion": "🧅", "carrot": "🥕", "banana": "🍌", "apple": "🍎",
    "rice": "🌾", "wheat": "🌾", "spinach": "🥬", "chilli": "🌶️",
    "chili": "🌶️", "cabbage": "🥬", "cucumber": "🥒", "corn": "🌽",
    "garlic": "🧄", "lemon": "🍋", "orange": "🍊", "grape": "🍇",
}
DEFAULT_EMOJI = "🌿"

def product_photo_url(name):
    """If static/images/<name>.jpg (or .png/.jpeg/.webp) exists, return its URL. Else None."""
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

# ── Database connection ────────────────────────────────────────
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
    # Pull product's own coordinates if set, otherwise fall back to the farmer's profile location
    cursor.execute("""
        SELECT p.*,
               u.name AS farmer_name,
               COALESCE(p.latitude, u.latitude)   AS map_lat,
               COALESCE(p.longitude, u.longitude) AS map_lng
        FROM products p
        JOIN users u ON p.farmer_id = u.id
        ORDER BY p.created_at DESC
    """)
    products = cursor.fetchall()
    db.close()
    return render_template("home.html", products=products)

# ── REGISTER ──────────────────────────────────────────────────
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name     = request.form["name"]
        email    = request.form["email"]
        password = request.form["password"]
        role     = request.form["role"]   # farmer or buyer
        latitude  = request.form.get("latitude") or None
        longitude = request.form.get("longitude") or None

        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO users (name, email, password, role, latitude, longitude) VALUES (%s, %s, %s, %s, %s, %s)",
            (name, email, password, role, latitude, longitude)
        )
        db.commit()
        db.close()
        flash("Account created! Please login.", "success")
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
        cursor.execute(
            "SELECT * FROM users WHERE email=%s AND password=%s",
            (email, password)
        )
        user = cursor.fetchone()
        db.close()

        if user:
            session["user_id"]   = user["id"]
            session["user_name"] = user["name"]
            session["user_role"] = user["role"]
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

# ── FORGOT PASSWORD ─────────────────────────────────────────────
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
            # Move to step 2: let them set a new password
            session["reset_email"] = email
            return redirect(url_for("reset_password"))
        else:
            flash("No account found with that email.", "danger")

    return render_template("forgot_password.html")

# ── RESET PASSWORD ───────────────────────────────────────────────
@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    email = session.get("reset_email")
    if not email:
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        new_password = request.form["password"]

        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "UPDATE users SET password=%s WHERE email=%s",
            (new_password, email)
        )
        db.commit()
        db.close()

        session.pop("reset_email", None)
        flash("Password updated! Please login with your new password.", "success")
        return redirect(url_for("login"))

    return render_template("reset_password.html", email=email)

# ── FARMER DASHBOARD ──────────────────────────────────────────
@app.route("/farmer")
def farmer_dashboard():
    if session.get("user_role") != "farmer":
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM products WHERE farmer_id=%s ORDER BY created_at DESC",
        (session["user_id"],)
    )
    my_products = cursor.fetchall()

    cursor.execute("SELECT latitude, longitude FROM users WHERE id=%s", (session["user_id"],))
    profile = cursor.fetchone()
    db.close()
    return render_template("farmer.html", products=my_products, profile=profile)

# ── UPDATE FARMER PROFILE LOCATION ─────────────────────────────
@app.route("/update_location", methods=["POST"])
def update_location():
    if session.get("user_role") != "farmer":
        return redirect(url_for("login"))

    latitude  = request.form.get("latitude")
    longitude = request.form.get("longitude")

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE users SET latitude=%s, longitude=%s WHERE id=%s",
        (latitude, longitude, session["user_id"])
    )
    db.commit()
    db.close()
    flash("Farm location updated!", "success")
    return redirect(url_for("farmer_dashboard"))

# ── ADD PRODUCT (Farmer) ───────────────────────────────────────
@app.route("/add_product", methods=["POST"])
def add_product():
    if session.get("user_role") != "farmer":
        return redirect(url_for("login"))

    name     = request.form["name"]
    price    = request.form["price"]
    quantity = request.form["quantity"]
    location = request.form["location"]
    category = request.form["category"]
    latitude  = request.form.get("latitude") or None
    longitude = request.form.get("longitude") or None

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        """INSERT INTO products (farmer_id, name, price, quantity, location, category, latitude, longitude)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        (session["user_id"], name, price, quantity, location, category, latitude, longitude)
    )
    db.commit()
    db.close()
    flash(f"{name} listed successfully!", "success")
    return redirect(url_for("farmer_dashboard"))

# ── DELETE PRODUCT (Farmer) ────────────────────────────────────
@app.route("/delete_product/<int:pid>")
def delete_product(pid):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "DELETE FROM products WHERE id=%s AND farmer_id=%s",
        (pid, session["user_id"])
    )
    db.commit()
    db.close()
    flash("Listing removed.", "success")
    return redirect(url_for("farmer_dashboard"))

# ── PLACE ORDER (Buyer) ────────────────────────────────────────
@app.route("/order/<int:pid>", methods=["GET", "POST"])
def order(pid):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.*, u.name as farmer_name,
               COALESCE(p.latitude, u.latitude)   AS map_lat,
               COALESCE(p.longitude, u.longitude) AS map_lng
        FROM products p JOIN users u ON p.farmer_id=u.id WHERE p.id=%s
    """, (pid,))
    product = cursor.fetchone()

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
    return render_template("order.html", product=product)

# ── MY ORDERS (Buyer) ──────────────────────────────────────────
@app.route("/orders")
def my_orders():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT o.*, p.name as product_name, u.name as farmer_name
        FROM orders o
        JOIN products p ON o.product_id = p.id
        JOIN users u ON p.farmer_id = u.id
        WHERE o.buyer_id = %s
        ORDER BY o.created_at DESC
    """, (session["user_id"],))
    orders = cursor.fetchall()
    db.close()
    return render_template("orders.html", orders=orders)

# ── INCOMING ORDERS (Farmer) ───────────────────────────────────
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

# ── UPDATE ORDER STATUS (Farmer) ───────────────────────────────
@app.route("/update_order/<int:oid>/<status>")
def update_order(oid, status):
    if session.get("user_role") != "farmer":
        return redirect(url_for("login"))

    # Only allow valid status values
    if status not in ["pending", "confirmed", "delivered"]:
        return redirect(url_for("farmer_orders"))

    db = get_db()
    cursor = db.cursor()
    # Make sure the order belongs to one of this farmer's products
    cursor.execute("""
        UPDATE orders o
        JOIN products p ON o.product_id = p.id
        SET o.status = %s
        WHERE o.id = %s AND p.farmer_id = %s
    """, (status, oid, session["user_id"]))
    db.commit()
    db.close()
    flash(f"Order marked as {status}!", "success")
    return redirect(url_for("farmer_orders"))

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)