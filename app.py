import os
import urllib.parse
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from PIL import Image

app = Flask(__name__)
app.secret_key = "addie_store_secret_key"

# Configure Upload Folder for Product Images
UPLOAD_FOLDER = os.path.join("static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Guard against read-only filesystems on Vercel
if not os.environ.get("VERCEL"):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

WHATSAPP_PHONE_NUMBER = "254756295128"

ORDERS = [
    {
        "id": 101,
        "customer_name": "John Doe",
        "phone": "254712345678",
        "address": "Nairobi, Kenya",
        "total": 42.63,
        "status": "Pending",
        "items": ["Zogaa Flame Sweater x1"],
        "created_at": "2026-08-05 14:30"
    }
]

PRODUCTS = [
    {
        "id": 1,
        "name": "Zogaa Flame Sweater",
        "category": "Men",
        "brand": "Nike",
        "price": 42.63,
        "sales": 2554,
        "rating": 4.3,
        "stock": 25,
        "images": [
            "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=600&q=80",
            "https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?auto=format&fit=crop&w=600&q=80"
        ],
        "description": "Flame graphic sweater made from premium cotton blend."
    },
    {
        "id": 2,
        "name": "Men Polo Shirt Brand Clothing",
        "category": "Men",
        "brand": "Puma",
        "price": 42.63,
        "sales": 2554,
        "rating": 4.3,
        "stock": 60,
        "images": [
            "https://images.unsplash.com/photo-1581655353564-df123a1eb820?auto=format&fit=crop&w=600&q=80"
        ],
        "description": "Classic fit men's polo shirt."
    }
]

# --- HELPER FUNCTIONS ---

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def save_and_resize_image(file):
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    
    img = Image.open(file)
    img = img.convert("RGB")
    
    target_size = (600, 600)
    img.thumbnail(target_size, Image.Resampling.LANCZOS)
    
    background = Image.new("RGB", target_size, (255, 255, 255))
    offset = ((target_size[0] - img.size[0]) // 2, (target_size[1] - img.size[1]) // 2)
    background.paste(img, offset)
    background.save(filepath, quality=90)
    
    return f"/static/uploads/{filename}"

@app.context_processor
def inject_cart_count():
    cart = session.get("cart", {})
    total_count = sum(item["quantity"] for item in cart.values())
    return dict(cart_count=total_count)

# --- PUBLIC / STOREFRONT ROUTES ---

@app.route("/")
def home():
    category = request.args.get("category", "All")
    brand = request.args.get("brand")
    search_query = request.args.get("q", "").strip().lower()
    
    available_products = [p for p in PRODUCTS if p["stock"] > 0]
    
    if search_query:
        available_products = [p for p in available_products if search_query in p["name"].lower() or search_query in p["brand"].lower()]
    if category != "All":
        available_products = [p for p in available_products if p["category"] == category]
    if brand:
        available_products = [p for p in available_products if p["brand"].lower() == brand.lower()]
        
    return render_template("home.html", products=available_products, current_category=category, current_brand=brand, search_query=search_query)

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("home"))
    return render_template("product.html", product=product)

@app.route("/categories")
def categories():
    all_categories = sorted(list(set(p["category"] for p in PRODUCTS if "category" in p)))
    all_brands = sorted(list(set(p["brand"] for p in PRODUCTS if "brand" in p)))
    return render_template("categories.html", categories=all_categories, brands=all_brands)

# --- CART & CHECKOUT ROUTES ---

@app.route("/cart")
def view_cart():
    cart = session.get("cart", {})
    cart_items = list(cart.values())
    total_price = sum(item["price"] * item["quantity"] for item in cart_items)
    return render_template("cart.html", cart_items=cart_items, total_price=total_price)

@app.route("/add-to-cart/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    product = next((p for p in PRODUCTS if p["id"] == product_id and p["stock"] > 0), None)
    if not product:
        flash("Product unavailable or out of stock.", "error")
        return redirect(request.referrer or url_for("home"))

    if "cart" not in session:
        session["cart"] = {}

    cart = session["cart"]
    str_id = str(product_id)

    current_qty = cart.get(str_id, {}).get("quantity", 0)
    if current_qty + 1 > product["stock"]:
        flash("Cannot add more items than available in stock.", "error")
        return redirect(request.referrer or url_for("home"))

    cart_img = product.get("images", [product.get("image", "")])[0]

    if str_id in cart:
        cart[str_id]["quantity"] += 1
    else:
        cart[str_id] = {
            "id": product["id"],
            "name": product["name"],
            "price": product["price"],
            "image": cart_img,
            "quantity": 1
        }

    session.modified = True
    flash(f"Added {product['name']} to cart!", "success")
    return redirect(request.referrer or url_for("home"))

@app.route("/remove-from-cart/<int:product_id>", methods=["POST"])
def remove_from_cart(product_id):
    cart = session.get("cart", {})
    str_id = str(product_id)
    if str_id in cart:
        del cart[str_id]
        session.modified = True
        flash("Item removed from cart.", "info")
    return redirect(url_for("view_cart"))

@app.route("/checkout")
def checkout():
    cart = session.get("cart", {})
    if not cart:
        flash("Your cart is empty.", "info")
        return redirect(url_for("home"))
    
    cart_items = list(cart.values())
    total_price = sum(item["price"] * item["quantity"] for item in cart_items)
    return render_template("checkout.html", cart_items=cart_items, total_price=total_price)

@app.route("/checkout-cart-whatsapp", methods=["POST"])
def checkout_cart_whatsapp():
    cart = session.get("cart", {})
    if not cart:
        return redirect(url_for("home"))

    customer_name = request.form.get("customer_name")
    phone = request.form.get("phone")
    address = request.form.get("address")
    notes = request.form.get("notes", "None")

    order_lines = []
    total_price = 0.0

    for item_id, item in cart.items():
        prod = next((p for p in PRODUCTS if p["id"] == int(item_id)), None)
        if prod:
            qty = min(item["quantity"], prod["stock"])
            prod["stock"] -= qty
            subtotal = prod["price"] * qty
            total_price += subtotal
            order_lines.append(f"• {prod['name']} x{qty} - ${subtotal:.2f}")

    items_text = "\n".join(order_lines)

    # Save order with current date & timestamp
    new_order_id = max([o["id"] for o in ORDERS], default=100) + 1
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    ORDERS.append({
        "id": new_order_id,
        "customer_name": customer_name,
        "phone": phone,
        "address": address,
        "total": total_price,
        "status": "Pending",
        "items": order_lines,
        "created_at": current_time
    })

    order_text = (
        f"🛍️ *NEW CART ORDER - ADDIE STORE*\n\n"
        f"👤 *Customer:* {customer_name}\n"
        f"📞 *Phone:* {phone}\n"
        f"📍 *Address:* {address}\n\n"
        f"--- *ORDER ITEMS* ---\n"
        f"{items_text}\n\n"
        f"💵 *TOTAL:* ${total_price:.2f}\n"
        f"📝 *Notes:* {notes}\n\n"
        f"Please confirm my order and share payment instructions!"
    )

    session["cart"] = {}
    session.modified = True

    encoded_text = urllib.parse.quote(order_text)
    whatsapp_url = f"https://wa.me/{WHATSAPP_PHONE_NUMBER}?text={encoded_text}"
    return redirect(whatsapp_url)

# --- ADMIN ROUTES ---

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        # Adjust your actual admin credentials check
        if email == "admin@example.com" and password == "yourpassword":
            session["is_admin"] = True
            flash("Admin logged in successfully!", "success")
            return redirect(url_for("view_orders"))
        else:
            session["is_admin"] = False
            flash("Invalid Admin Email or Password!", "error")
            return redirect(url_for("signup"))

    return render_template("signup.html")

@app.route("/admin")
def admin_dashboard():
    if not session.get("is_admin"):
        return redirect(url_for("signup"))
    return render_template("admin_dashboard.html", products=PRODUCTS, orders=ORDERS)

@app.route("/admin/orders")
def view_orders():
    # Strict admin check
    if not session.get("is_admin"):
        flash("Please log in as an administrator to access this page.", "danger")
        return redirect(url_for("signup"))  # or your login route name

    status_filter = request.args.get("status", "All")
    
    if status_filter == "Pending":
        filtered_orders = [o for o in ORDERS if o.get("status") == "Pending"]
    elif status_filter == "Completed":
        filtered_orders = [o for o in ORDERS if o.get("status") == "Completed"]
    else:
        filtered_orders = ORDERS

    sorted_orders = sorted(filtered_orders, key=lambda x: x["id"], reverse=True)
    return render_template("orders.html", orders=sorted_orders, current_filter=status_filter)

@app.route("/admin/add-offline-order", methods=["POST"])
def add_offline_order():
    # Restrict action to admin only
    if not session.get("is_admin"):
        flash("Unauthorized action.", "danger")
        return redirect(url_for("admin_login"))

    customer_name = request.form.get("customer_name")
    phone = request.form.get("phone")
    address = request.form.get("address")
    items_input = request.form.get("items", "")
    total = float(request.form.get("total", 0.0))
    status = request.form.get("status", "Completed")

    # Match the field name 'image_files' from HTML template
    uploaded_images = []
    files = request.files.getlist("image_files")[:3]
    for file in files:
        if file and file.filename != "" and allowed_file(file.filename):
            uploaded_images.append(save_and_resize_image(file))

    new_order_id = max([o["id"] for o in ORDERS], default=100) + 1
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    ORDERS.append({
        "id": new_order_id,
        "customer_name": customer_name,
        "phone": phone,
        "address": address,
        "total": total,
        "status": status,
        "items": [items_input],
        "images": uploaded_images,
        "created_at": current_time
    })

    flash("Offline order logged successfully!", "success")
    return redirect(url_for("view_orders"))

@app.route("/admin/update-order-status/<int:order_id>", methods=["POST"])
def update_order_status(order_id):
    # Restrict action to admin only
    if not session.get("is_admin"):
        flash("Unauthorized action.", "danger")
        return redirect(url_for("admin_login"))

    new_status = request.form.get("status")
    order = next((o for o in ORDERS if o["id"] == order_id), None)
    
    if order:
        order["status"] = new_status
        flash(f"Order #{order_id} status updated to {new_status}.", "success")

    return redirect(request.referrer or url_for("view_orders"))

@app.route("/admin/delete-order/<int:order_id>", methods=["POST"])
def delete_order(order_id):
    # Restrict action to admin only
    if not session.get("is_admin"):
        flash("Unauthorized action.", "danger")
        return redirect(url_for("admin_login"))

    global ORDERS
    ORDERS = [o for o in ORDERS if o["id"] != order_id]
    flash(f"Order #{order_id} deleted successfully.", "info")
    return redirect(url_for("view_orders"))

@app.route("/admin/add-product", methods=["POST"])
def add_product():
    if not session.get("is_admin"):
        return redirect(url_for("signup"))

    name = request.form.get("name")
    category = request.form.get("category")
    brand = request.form.get("brand")
    price = float(request.form.get("price"))
    stock = int(request.form.get("stock"))
    description = request.form.get("description")
    
    uploaded_images = []
    files = request.files.getlist("image_files")
    
    for file in files:
        if file and file.filename != "" and allowed_file(file.filename):
            uploaded_images.append(save_and_resize_image(file))

    if not uploaded_images and "image_file" in request.files:
        file = request.files["image_file"]
        if file and file.filename != "" and allowed_file(file.filename):
            uploaded_images.append(save_and_resize_image(file))

    if not uploaded_images:
        uploaded_images = ["https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=600&q=80"]

    new_id = max([p["id"] for p in PRODUCTS], default=0) + 1
    new_item = {
        "id": new_id,
        "name": name,
        "category": category,
        "brand": brand,
        "price": price,
        "sales": 0,
        "rating": 5.0,
        "stock": stock,
        "images": uploaded_images,
        "description": description
    }
    
    PRODUCTS.append(new_item)
    flash("New Product Added Successfully!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/edit-product/<int:product_id>", methods=["GET", "POST"])
@app.route("/admin/edit_product/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    if not session.get("is_admin"):
        return redirect(url_for("signup"))
        
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        return "Product Not Found", 404

    if request.method == "POST":
        product["name"] = request.form.get("name")
        product["category"] = request.form.get("category")
        product["brand"] = request.form.get("brand")
        product["price"] = float(request.form.get("price"))
        product["stock"] = int(request.form.get("stock"))
        product["description"] = request.form.get("description")

        files = request.files.getlist("image_files")
        new_images = []
        for file in files:
            if file and file.filename != "" and allowed_file(file.filename):
                new_images.append(save_and_resize_image(file))
        
        if not new_images and "image_file" in request.files:
            file = request.files["image_file"]
            if file and file.filename != "" and allowed_file(file.filename):
                new_images.append(save_and_resize_image(file))

        if new_images:
            product["images"] = new_images

        flash("Product updated successfully!", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("edit_product.html", product=product)

@app.route("/admin/restock/<int:product_id>", methods=["POST"])
def restock_product(product_id):
    if not session.get("is_admin"):
        return redirect(url_for("signup"))

    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if product:
        add_stock = int(request.form.get("add_stock", 0))
        product["stock"] += add_stock
        flash(f"Added {add_stock} items to {product['name']} stock!", "success")

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/delete-product/<int:product_id>", methods=["POST"])
def delete_product(product_id):
    if not session.get("is_admin"):
        return redirect(url_for("signup"))

    global PRODUCTS
    PRODUCTS = [p for p in PRODUCTS if p["id"] != product_id]
    flash("Product deleted successfully!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/logout")
def logout():
    session.pop("is_admin", None)
    session.pop("user", None)
    flash("Logged out successfully.", "info")
    return redirect(url_for("signup"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)