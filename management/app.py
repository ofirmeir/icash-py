from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
from sqlalchemy import create_engine, Column, Integer, String, Numeric, ForeignKey, TIMESTAMP
from sqlalchemy.orm import declarative_base, relationship, Session
import pandas as pd
from dateutil import parser
import os
import logging
import configparser
import sys

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://appuser:apassword@db:5432/appdb")
engine = create_engine(DATABASE_URL, echo=False, future=True)
Base = declarative_base()

# ----------------- LOGGER -----------------

def setup_logging(config_path: str = "log.cfg"):
    """
    Read `config_path` for section [logging] key `level` and configure
    root logger to output to console (stdout) at that level.
    """
    cfg = configparser.ConfigParser()
    level_name = "INFO"
    if os.path.exists(config_path):
        try:
            cfg.read(config_path)
            level_name = cfg.get("logging", "level", fallback=level_name).upper()
        except Exception:
            # fallback to default if parsing fails
            level_name = "INFO"
    else:
        # no config file, use default or env override
        level_name = os.getenv("LOG_LEVEL", level_name).upper()

    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    # clear existing handlers to avoid duplicates when reloading
    for h in list(root.handlers):
        root.removeHandler(h)

    root.setLevel(level)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    # reduce overly-verbose third-party loggers if desired
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(level)

    root.info("Logging initialized from %s with level %s", config_path, level_name)

# Call setup_logging early in startup (before creating engine/app)
setup_logging("log.cfg")


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
    items_list = Column(String, nullable=False)
    total_amount = Column(Numeric, nullable=False)

class PurchaseItem(Base):
    __tablename__ = "purchase_items"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    product = relationship("Product")
    total_purchases = Column(Integer, nullable=False)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, unique=True, nullable=False)
    total_purchases = relationship("TotalUserPurchases", back_populates="user", uselist=False)

class TotalUserPurchases(Base):
    __tablename__ = "user_total_purchases"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    user = relationship("User", back_populates="total_purchases")
    total_purchases = Column(Integer, nullable=True)

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

    <h4>📦 Upload Products</h4>
    <form method="post" action="/upload_products" enctype="multipart/form-data" class="mb-4">
      <input type="file" name="file" accept=".csv" required>
      <button class="btn btn-primary btn-sm">Upload products_list.csv</button>
    </form>

    <h4>🧾 Upload Purchases</h4>
    <form method="post" action="/upload_purchases" enctype="multipart/form-data" class="mb-4">
      <input type="file" name="file" accept=".csv" required>
      <button class="btn btn-success btn-sm">Upload purchases.csv</button>
    </form>
    <hr>
    <a href="/recent" class="btn btn-outline-secondary">View Most Recent Purchase</a>

    <!-- New buttons for the requested pages -->
    <div class="mt-3">
      <a href="/loyal_customers" class="btn btn-outline-primary me-2">Loyal Customers</a>
      <a href="/unique_customers" class="btn btn-outline-info me-2">Unique Customers</a>
      <a href="/best_sellers" class="btn btn-outline-warning">Best Sellers</a>
    </div>

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

# New simple pages for the three routes
LOYAL_HTML = """
<!doctype html>
<html>
<head>
  <title>Loyal Customers</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.1/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="p-4">
  <div class="container">
    <a href="/" class="btn btn-secondary">Return home</a>
    <h2>Loyal Customers</h2>
    <p>This page shows loyal customers (customers who had bought more than 3 times).</p>

    {% if loyal_customers_list %}
      <div class="table-responsive">
        <table class="table table-striped table-bordered">
          <thead>
            <tr>
              <th scope="col">id</th>
              <th scope="col">number of purchases</th>
            </tr>
          </thead>
          <tbody>
            {% for cid, num in loyal_customers_list %}
              <tr>
                <td>{{ cid }}</td>
                <td>{{ num }}</td>
              </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    {% else %}
      <div class="alert alert-info">No loyal customers found.</div>
    {% endif %}

  </div>
</body>
</html>
"""

UNIQUE_HTML = """
<!doctype html>
<html>
<head>
  <title>Unique Customers</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.1/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="p-4">
  <div class="container">
    <a href="/" class="btn btn-secondary">Return home</a>
    <h2>Unique Customers</h2>
    <p>The number of unique customers is: {{ unique_customers_count }}</p>
  </div>
</body>
</html>
"""

BEST_HTML = """
<!doctype html>
<html>
<head>
  <title>Best Sellers</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.1/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="p-4">
  <div class="container">
    <a href="/" class="btn btn-secondary">Return home</a>
    <h2>Best Sellers</h2>
    <p>This page shows the 3 best selling products (or more, if the same amount of items was sold of them).</p>
    {% if top_sellers %}
      <div class="table-responsive">
        <table class="table table-striped table-bordered">
          <thead>
            <tr>
              <th scope="col">id</th>
              <th scope="col">number of purchases</th>
            </tr>
          </thead>
          <tbody>
            {% for product_name, num in top_sellers %}
              <tr>
                <td>{{ product_name }}</td>
                <td>{{ num }}</td>
              </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    {% else %}
      <div class="alert alert-info">No loyal customers found.</div>
    {% endif %}
  </div>
</body>
</html>
"""

# ----------------- HELPERS -----------------



# ----------------- ROUTES -----------------
@app.route("/")
def index():
    return render_template_string(INDEX_HTML)

@app.route("/upload_products", methods=["POST"])
def upload_products():
    logger = logging.getLogger("app.upload_products")
    f = request.files.get("file")
    if not f:
        flash("No file uploaded")
        logger.warning("No file uploaded")
        return redirect(url_for("index"))
    df = pd.read_csv(f)
    if "product_name" not in df.columns or "unit_price" not in df.columns:
        flash("CSV must have 'product_name' and 'unit_price'")
        logger.warning("CSV missing required columns")
        return redirect(url_for("index"))
    with Session(engine) as session:
        logger.info(f"Uploading {len(df)} products")
        for _, row in df.iterrows():
            name = str(row["product_name"])
            price = float(row["unit_price"])
            existing = session.query(Product).filter_by(product_name=name).first()
            if existing:
                logger.debug("The product '%s' exists in the Database, updating price to %s", name, price)
                existing.unit_price = price
                session.commit()
            else:
                logger.debug("The product '%s' doesn't exist in the Database, creating it", name)
                session.add(Product(product_name=name, unit_price=price))
        session.commit()
    flash(f"Loaded {len(df)} products.")
    return redirect(url_for("index"))


@app.route("/upload_purchases", methods=["POST"])
def upload_purchases():
    logger = logging.getLogger("app.upload_purchases")
    f = request.files.get("file")
    if not f:
        flash("No file uploaded")
        logger.warning("No file uploaded")
        return redirect(url_for("index"))

    df = pd.read_csv(f)
    expected_cols = {"supermarket_id", "timestamp", "user_id", "items_list", "total_amount"}
    if not expected_cols.issubset(df.columns):
        flash(f"CSV must have columns: {', '.join(expected_cols)}")
        logger.warning("CSV missing required columns")
        return redirect(url_for("index"))

    inserted_count = 0
    # go over rows and insert purchases
    with Session(engine) as session:
        logger.info("Uploading %d purchases", len(df))
        for _, row in df.iterrows():
            supermarket_id = str(row["supermarket_id"])
            timestamp = parser.parse(str(row["timestamp"]))
            user_id = str(row["user_id"])
            items_list_str = str(row["items_list"])
            total_amount = float(row["total_amount"])

            # store user if not exists
            user = session.query(User).filter_by(user_id=user_id).first()
            if not user: # the user had not existed before in the database, create it
                logger.debug("The user '%s' doesn't exist in the Database, creating it", user_id)
                new_user_db_record = User(user_id=user_id)
                new_user_total_purchase_db_record = TotalUserPurchases(user_id=user_id, total_purchases=1)
                session.add(new_user_db_record)
                session.add(new_user_total_purchase_db_record)
                session.commit()
                session.flush()
            else: # the user exist in the database, update it
                logger.debug("The user '%s' exists in the Database, updating total purchases", user_id)
                existing_user_total_purchase_db_record = session.query(TotalUserPurchases).filter_by(user_id=user_id).first()
                existing_user_total_purchase_db_record.total_purchases += 1
                session.commit()

            # handle items list
            items_list = items_list_str.split(",")
            for item_name in items_list:
                item_name = item_name.strip()
                product_db_record = session.query(Product).filter_by(product_name=item_name).first()
                if not product_db_record:
                    flash(f"Product '{item_name}' not found in DB.")
                    logger.warning("Product '%s' doesn't exist in the Database", item_name)
                    session.rollback()
                    return redirect(url_for("index"))
                else: # the product exist in the database, update PurchaseItem table
                    logger.debug("The product '%s' exists in the Database, updating PurchaseItem table", item_name)
                    purchase_item = session.query(PurchaseItem).filter_by(product_id=product_db_record.id).first()
                    if not purchase_item:
                        logger.debug("The PurchaseItem for product '%s' doesn't exist in the Database, creating it", item_name)
                        new_purchase_item_db_record = PurchaseItem(product_id=product_db_record.id, total_purchases=1)
                        session.add(new_purchase_item_db_record)
                        session.commit()
                    else:
                        logger.debug("The PurchaseItem for product '%s' exists in the Database, updating total purchases", item_name)
                        purchase_item.total_purchases += 1
                        session.commit()

            # try to insert purchase record
            logger.debug("Inserting a new purchase for user '%s' at '%s' at '%s'", user_id, supermarket_id, timestamp.isoformat())
            purchase = Purchase(
                supermarket_id=supermarket_id,
                timestamp=timestamp,
                user_id=user_id,
                items_list=items_list_str,
                total_amount=total_amount
            )
            session.add(purchase)
            inserted_count += 1
            session.flush()

    session.commit()

    flash(f"Loaded {inserted_count} purchases successfully.")
    logger.info(f"Loaded {inserted_count} purchases successfully.")
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

@app.route("/loyal_customers")
def loyal_customers():
    """Render a simple Loyal Customers page with a Return home button."""
    number_of_purchases_threshold = 3
    # get a list of loyal customers containing id and number of purchases from the postgresql database
    with (Session(engine) as session):
        loyal_customers_list = session.query(User).join(TotalUserPurchases).filter(TotalUserPurchases.total_purchases >= number_of_purchases_threshold).order_by(TotalUserPurchases.total_purchases.desc()).all()
        logging.getLogger("app.loyal_customers").info("Number of loyal customers: %d", len(loyal_customers_list))
        # get only the user_id and total_purchases for each loyal customer
        loyal_customers_trimmed_list = [(customer.user_id, customer.total_purchases.total_purchases) for customer in loyal_customers_list]

    return render_template_string(LOYAL_HTML, loyal_customers_list=loyal_customers_trimmed_list)

@app.route("/unique_customers")
def unique_customers():
    """Render a simple Unique Customers page with a Return home button."""
    # get the number of unique customers from the postgresql database
    with Session(engine) as session:
        unique_customers_count = session.query(User).count()
        logging.getLogger("app.unique_customers").info("Number of unique customers: %d", unique_customers_count)

    return render_template_string(UNIQUE_HTML, unique_customers_count=unique_customers_count)

@app.route("/best_sellers")
def best_sellers():
    """Render a simple Best Sellers page with a Return home button."""
    with Session(engine) as session:
        logger = logging.getLogger("app.best_sellers")
        # get the top 3 best selling products from the postgresql database
        logger.debug("Retrieving top 3 best selling products")
        ordered_purchase_items = session.query(PurchaseItem).join(Product).order_by(PurchaseItem.total_purchases.desc()).all()
        top_sellers_numbers = []
        top_sellers = []
        for item in ordered_purchase_items:
            if len(set(top_sellers_numbers)) <= 3:
                checked_item_total_purchases = item.total_purchases
                checked_item_product_name = item.product.product_name
                if checked_item_total_purchases in top_sellers_numbers:
                    logger.debug("Adding a new top selling product '%s', with %d purchases", checked_item_product_name, checked_item_total_purchases)
                    top_sellers.append((checked_item_product_name,checked_item_total_purchases))
                    continue
                else:
                    if len(set(top_sellers_numbers)) < 3:
                        logger.debug("Adding a new top selling product '%s', with %d purchases", checked_item_product_name, checked_item_total_purchases)
                        top_sellers_numbers.append(checked_item_total_purchases)
                        top_sellers.append((checked_item_product_name,checked_item_total_purchases))
                    else: # len == 3: we already have 3 different numbers of top sellers, we won't add more
                        logger.debug("Top 3 best selling products retrieved")
                        break
            else:
                break
        logging.getLogger("app.best_sellers").info("Top selling products retrieved")

    return render_template_string(BEST_HTML, top_sellers=top_sellers)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
