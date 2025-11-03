from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
from sqlalchemy import create_engine, Column, Integer, String, Numeric, ForeignKey, TIMESTAMP
from sqlalchemy.orm import declarative_base, relationship, Session
from datetime import datetime
import pandas as pd
from dateutil import parser
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
  <title>Management UI</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.1/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="p-4">
  <div class="container">
    <h2>Management UI</h2>
    <form method="post" action="/upload_products" enctype="multipart/form-data">
      <label>Upload products.csv</label>
      <input type="file" name="file" accept=".csv" required>
      <button class="btn btn-primary">Upload</button>
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

@app.route("/")
def index():
    return render_template_string(INDEX_HTML)

@app.route("/upload_products", methods=["POST"])
def upload_products():
    f = request.files.get("file")
    if not f:
        flash("No file uploaded")
        return redirect(url_for("index"))
    df = pd.read_csv(f)
    if "product_name" not in df.columns or "unit_price" not in df.columns:
        flash("CSV must have 'product_name' and 'unit_price'")
        return redirect(url_for("index"))
    with Session(engine) as session:
        for _, row in df.iterrows():
            name = str(row["product_name"])
            price = float(row["unit_price"])
            existing = session.query(Product).filter_by(product_name=name).first()
            if existing:
                existing.unit_price = price
                session.commit()
            else:
                session.add(Product(product_name=name, unit_price=price))
        session.commit()
    flash(f"Loaded {len(df)} products.")
    return redirect(url_for("index"))

@app.route("/recent")
def recent_purchase():
    with Session(engine) as session:
        p = session.query(Purchase).order_by(Purchase.timestamp.desc()).first()
        if not p:
            return jsonify({"message": "no purchases"}), 404
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
