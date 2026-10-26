from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    flash,
    redirect,
    url_for,
)

from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    current_user,
    login_required,
)

from models import (
    db,
    User,
    Product,
    CartItem,
    WishlistItem,
    Order,
    OrderItem,
    BrowsingHistory,
)

app = Flask(__name__)

app.config["SECRET_KEY"] = "change-this-to-a-random-secret-before-deployment"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///shopsmart.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

def get_personalized_recommendations(user_id, limit=8):
    """Generate personalized product recommendations."""

    category_scores = {}
    purchased_product_ids = set()
    viewed_product_ids = set()
    wishlisted_product_ids = set()

    # 1. Browsing history: +1 point per view
    browsing_history = (
        BrowsingHistory.query
        .filter_by(user_id=user_id)
        .order_by(BrowsingHistory.viewed_at.desc())
        .all()
    )

    for history in browsing_history:
        product = db.session.get(Product, history.product_id)

        if product:
            viewed_product_ids.add(product.id)
            category_scores[product.category] = (
                category_scores.get(product.category, 0) + 1
            )

    # 2. Wishlist: +3 points per saved product
    wishlist_items = WishlistItem.query.filter_by(
        user_id=user_id
    ).all()

    for item in wishlist_items:
        product = db.session.get(Product, item.product_id)

        if product:
            wishlisted_product_ids.add(product.id)
            category_scores[product.category] = (
                category_scores.get(product.category, 0) + 3
            )

    # 3. Purchase history: +5 points per purchased unit
    orders = Order.query.filter_by(user_id=user_id).all()

    for order in orders:
        for item in order.items:
            if item.product_id:
                purchased_product_ids.add(item.product_id)

                product = db.session.get(Product, item.product_id)

                if product:
                    category_scores[product.category] = (
                        category_scores.get(product.category, 0)
                        + 5 * item.quantity
                    )

    # 4. If no preferences exist, show highly rated products
    if not category_scores:
        return (
            Product.query
            .order_by(Product.rating.desc(), Product.id.desc())
            .limit(limit)
            .all()
        )

    # 5. Score and rank candidate products
    scored_products = []

    all_products = Product.query.all()

    for product in all_products:
        # Do not recommend products already purchased
        if product.id in purchased_product_ids:
            continue

        score = category_scores.get(product.category, 0)

        # Small rating bonus
        score += (product.rating or 0) * 0.1

        # Slightly lower priority for products already viewed
        if product.id in viewed_product_ids:
            score *= 0.7

        # Wishlist products receive a small extra boost
        if product.id in wishlisted_product_ids:
            score += 2

        if score > 0:
            scored_products.append((score, product))

    scored_products.sort(
        key=lambda item: (item[0], item[1].rating or 0),
        reverse=True
    )

    recommendations = []
    recommended_ids = set()

    for score, product in scored_products:
        if product.id not in recommended_ids:
            recommendations.append(product)
            recommended_ids.add(product.id)

        if len(recommendations) >= limit:
            break

    # 6. Fill any remaining slots with highly rated products
    if len(recommendations) < limit:
        fallback_products = (
            Product.query
            .order_by(Product.rating.desc(), Product.id.desc())
            .all()
        )

        for product in fallback_products:
            if (
                product.id not in recommended_ids
                and product.id not in purchased_product_ids
            ):
                recommendations.append(product)
                recommended_ids.add(product.id)

            if len(recommendations) >= limit:
                break

    return recommendations

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "home"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


with app.app_context():
    db.create_all()

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Please complete all fields.", "warning")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "warning")
            return redirect(url_for("register"))

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash("An account with this email already exists.", "warning")
            return redirect(url_for("register"))

        user = User(name=name, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash("Account created successfully!", "success")
        return redirect(url_for("home"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash("Welcome back!", "success")
            return redirect(url_for("home"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have logged out successfully.", "success")
    return redirect(url_for("home"))

@app.route("/cart")
@login_required
def view_cart():
    items = CartItem.query.filter_by(
        user_id=current_user.id
    ).all()

    total = sum(
        item.product.price * item.quantity
        for item in items
    )

    return render_template(
        "cart.html",
        items=items,
        total=total
    )


@app.route("/cart/add/<int:product_id>", methods=["POST"])
@login_required
def add_to_cart(product_id):
    product = db.session.get(Product, product_id)

    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for("home"))

    if product.stock <= 0:
        flash("This product is currently out of stock.", "warning")
        return redirect(url_for("home"))

    item = CartItem.query.filter_by(
        user_id=current_user.id,
        product_id=product.id
    ).first()

    if item:
        if item.quantity >= product.stock:
            flash("No more stock available.", "warning")
        else:
            item.quantity += 1
            db.session.commit()
            flash("Cart quantity updated.", "success")
    else:
        item = CartItem(
            user_id=current_user.id,
            product_id=product.id,
            quantity=1
        )
        db.session.add(item)
        db.session.commit()
        flash("Product added to your cart.", "success")

    return redirect(url_for("view_cart"))


@app.route("/cart/update/<int:item_id>", methods=["POST"])
@login_required
def update_cart(item_id):
    item = CartItem.query.filter_by(
        id=item_id,
        user_id=current_user.id
    ).first_or_404()

    try:
        quantity = int(request.form.get("quantity", "1"))
    except (ValueError, TypeError):
        flash("Invalid quantity.", "danger")
        return redirect(url_for("view_cart"))

    if quantity < 1:
        flash("Quantity must be at least 1.", "warning")
    elif quantity > item.product.stock:
        flash("Requested quantity exceeds available stock.", "warning")
    else:
        item.quantity = quantity
        db.session.commit()
        flash("Cart updated.", "success")

    return redirect(url_for("view_cart"))


@app.route("/cart/remove/<int:item_id>", methods=["POST"])
@login_required
def remove_from_cart(item_id):
    item = CartItem.query.filter_by(
        id=item_id,
        user_id=current_user.id
    ).first_or_404()

    db.session.delete(item)
    db.session.commit()

    flash("Product removed from cart.", "success")
    return redirect(url_for("view_cart"))


@app.route("/wishlist/toggle/<int:product_id>", methods=["POST"])
@login_required
def toggle_wishlist(product_id):
    product = db.session.get(Product, product_id)

    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for("home"))

    item = WishlistItem.query.filter_by(
        user_id=current_user.id,
        product_id=product.id
    ).first()

    if item:
        db.session.delete(item)
        message = "Product removed from wishlist."
    else:
        item = WishlistItem(
            user_id=current_user.id,
            product_id=product.id
        )
        db.session.add(item)
        message = "Product saved to wishlist."

    db.session.commit()
    flash(message, "success")

    return redirect(request.referrer or url_for("home"))

@app.route("/wishlist")
@login_required
def view_wishlist():
    items = (
        WishlistItem.query
        .filter_by(user_id=current_user.id)
        .all()
    )

    return render_template(
        "wishlist.html",
        items=items
    )

@app.route("/checkout", methods=["POST"])
@login_required
def checkout():
    items = CartItem.query.filter_by(
        user_id=current_user.id
    ).all()

    if not items:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("view_cart"))

    # Validate stock before creating the order.
    for item in items:
        if item.quantity < 1 or item.quantity > item.product.stock:
            flash(
                f"Stock issue for {item.product.name}. Please update your cart.",
                "warning"
            )
            return redirect(url_for("view_cart"))

    try:
        total = sum(
            item.product.price * item.quantity
            for item in items
        )

        order = Order(
            user_id=current_user.id,
            total_amount=total,
            status="Placed"
        )

        db.session.add(order)
        db.session.flush()

        for item in items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                product_name=item.product.name,
                price=item.product.price,
                quantity=item.quantity
            )

            db.session.add(order_item)

            # Reduce available demo stock.
            item.product.stock -= item.quantity

            db.session.delete(item)

        db.session.commit()

        flash(f"Order #{order.id} placed successfully!", "success")
        return redirect(url_for("order_history"))

    except Exception:
        db.session.rollback()
        app.logger.exception("Checkout failed")
        flash("Could not place the order. Please try again.", "danger")
        return redirect(url_for("view_cart"))
@app.route("/orders")
@login_required
def order_history():
    orders = (
        Order.query
        .filter_by(user_id=current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )

    return render_template(
        "orders.html",
        orders=orders
    )

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    product = db.session.get(Product, product_id)

    if not product:
        flash("Product not found.", "warning")
        return redirect(url_for("home"))

    # Record product view for logged-in users.
    if current_user.is_authenticated:
        history = BrowsingHistory(
            user_id=current_user.id,
            product_id=product.id
        )

        db.session.add(history)
        db.session.commit()

    related_products = (
        Product.query
        .filter(
            Product.category == product.category,
            Product.id != product.id
        )
        .limit(4)
        .all()
    )

    return render_template(
        "product_detail.html",
        product=product,
        related_products=related_products
    )

@app.route("/")
def home():
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "All").strip()

    products_query = Product.query

    if category and category != "All":
        products_query = products_query.filter(
            Product.category == category
        )

    if query:
        search_term = f"%{query}%"
        products_query = products_query.filter(
            db.or_(
                Product.name.ilike(search_term),
                Product.category.ilike(search_term),
                Product.description.ilike(search_term),
                Product.brand.ilike(search_term),
            )
        )

    products = products_query.order_by(Product.id.desc()).all()

    categories = [
        row[0]
        for row in db.session.query(Product.category)
        .distinct()
        .order_by(Product.category)
        .all()
    ]

    categories = ["All"] + categories

    recently_viewed = []

    if current_user.is_authenticated:
        recent_history = (
            BrowsingHistory.query
            .filter_by(user_id=current_user.id)
            .order_by(BrowsingHistory.viewed_at.desc())
            .limit(20)
            .all()
        )

        seen_product_ids = set()

        for history in recent_history:
            if history.product_id not in seen_product_ids:
                product = db.session.get(Product, history.product_id)

                if product:
                    recently_viewed.append(product)
                    seen_product_ids.add(history.product_id)

                if len(recently_viewed) >= 8:
                    break
        # Personalized recommendations
    recommended_products = []

    if current_user.is_authenticated:
        recommended_products = get_personalized_recommendations(
            current_user.id,
            limit=8
        )

    return render_template(
        "index.html",
        products=products,
        categories=categories,
        selected_category=category,
        query=query,
        total_products=Product.query.count(),
        recently_viewed=recently_viewed,
        recommended_products=recommended_products,
    )

@app.route("/api/products")
def api_products():
    products = Product.query.order_by(Product.name).all()

    return jsonify([
        product.to_dict()
        for product in products
    ])


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "database": "connected",
        "product_count": Product.query.count(),
    })


if __name__ == "__main__":
    app.run(debug=True)