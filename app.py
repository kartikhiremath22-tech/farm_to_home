from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector

app = Flask(__name__)
app.secret_key = "farmtohome123"

# ── Database connection ────────────────────────────────────────
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
       password="your_password",   # Change this
        database="farm_to_home"
    )

# ── HOME PAGE ──────────────────────────────────────────────────
@app.route("/")
def home():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products ORDER BY created_at DESC")
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

        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
            (name, email, password, role)
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
    db.close()
    return render_template("farmer.html", products=my_products)

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

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO products (farmer_id, name, price, quantity, location, category) VALUES (%s,%s,%s,%s,%s,%s)",
        (session["user_id"], name, price, quantity, location, category)
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
    cursor.execute("SELECT p.*, u.name as farmer_name FROM products p JOIN users u ON p.farmer_id=u.id WHERE p.id=%s", (pid,))
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
    app.run(debug=True)
