from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
from sqlalchemy import create_engine, Column, Integer, String, Numeric, ForeignKey, TIMESTAMP
from sqlalchemy.orm import declarative_base, relationship, Session
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://appuser:apassword@db:5432/appdb")
engine = create_engine(DATABASE_URL, echo=False, future=True)
Base = declarative_base()

# ----------------- MODELS -----------------
class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    product_name = Column(String, unique=True, nullable=False)
    unit_price = Column(Numeric, nullable=False)

class Purchase(Base):
    __tablename__ = "purchases"
    id = Column(Integer, primary_key=True)
    supermarket_id = Column(String, nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    user_id = Column(String, nullable=False)
    total_amount = Column(Numeric, nullable=False)
    items = relationship("PurchaseItem", back_populates="purchase", cascade="all, delete-orphan")

class PurchaseItem(Base):
    __tablename__ = "purchase_items"
    id = Column(Integer, primary_key=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id", ondelete="CASCADE"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, nullable=False)
    line_total = Column(Numeric, nullable=False)
    purchase = relationship("Purchase", back_populates="items")
    product = relationship("Product")

Base.metadata.create_all(engine)

# ----------------- APP -----------------
app = Flask(__name__)
app.secret_key = "dev-secret"

INDEX_HTML = """
<!doctype html>
<html>
<head>
  <title>Cash Register</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.1/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="p-4">
  <div class="container">
    <h2>Cash Register</h2>
    <form method="post" action="/create">
      <div class="mb-3"><label>Supermarket ID</label><input class="form-control" name="supermarket_id" required></div>
      <div class="mb-3"><label>User ID</label><input class="form-control" name="user_id" required></div>
      <div class="mb-3"><label>Items (product_name:qty, comma-separated)</label><input class="form-control" name="items" placeholder="apple:2,banana:3" required></div>
      <button class="btn btn-primary">Record Purchase</button>
    </form>
    <hr>
    <a href="/recent" class="btn btn-outline-secondary">View Most Recent Purchase</a>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <div class="mt-3">
          {% for m in messages %}
            <div class="alert alert-info">{{m}}</div>
          {% endfor %}
        </div>
      {% endif %}
    {% endwith %}
  </div>
</body>
</html>
"""

def parse_items(items_str):
    pairs = [p.strip() for p in items_str.split(",") if p.strip()]
    result = []
    for p in pairs:
        if ":" not in p:
            raise ValueError("each item must be product_name:quantity")
        name, qty = p.split(":", 1)
        result.append({"product_name": name.strip(), "quantity": int(qty)})
    return result

@app.route("/")
def index():
    return render_template_string(INDEX_HTML)

@app.route("/create", methods=["POST"])
def create_purchase():
    supermarket_id = request.form["supermarket_id"]
    user_id = request.form["user_id"]
    items_input = request.form["items"]

    try:
        items = parse_items(items_input)
    except ValueError as e:
        flash(str(e))
        return redirect(url_for("index"))

    with Session(engine) as session:
        purchase = Purchase(
            supermarket_id=supermarket_id,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            total_amount=0
        )
        session.add(purchase)
        session.flush()  # get purchase.id

        total = 0
        for it in items:
            product = session.query(Product).filter_by(product_name=it["product_name"]).first()
            if not product:
                flash(f"Product '{it['product_name']}' not found in DB.")
                session.rollback()
                return redirect(url_for("index"))
            line_total = float(product.unit_price) * it["quantity"]
            total += line_total
            session.add(PurchaseItem(
                purchase_id=purchase.id,
                product_id=product.id,
                quantity=it["quantity"],
                line_total=line_total
            ))

        purchase.total_amount = round(total, 2)
        session.commit()
        flash(f"Purchase saved. Total = {purchase.total_amount}")
    return redirect(url_for("index"))

@app.route("/recent")
def recent_purchase():
    with Session(engine) as session:
        p = session.query(Purchase).order_by(Purchase.timestamp.desc()).first()
        if not p:
            return jsonify({"message": "no purchases yet"}), 404
        data = {
            "id": p.id,
            "supermarket_id": p.supermarket_id,
            "timestamp": p.timestamp.isoformat(),
            "user_id": p.user_id,
            "total_amount": str(p.total_amount),
            "items": [
                {
                    "product_name": item.product.product_name,
                    "unit_price": str(item.product.unit_price),
                    "quantity": item.quantity,
                    "line_total": str(item.line_total)
                } for item in p.items
            ]
        }
        return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
