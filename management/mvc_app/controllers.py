from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from .db import SessionLocal
from .models import Product, Purchase, PurchaseItem, User, TotalUserPurchases
from .logging_config import setup_logging
import pandas as pd
from dateutil import parser
import logging

bp = Blueprint("main", __name__)

@bp.route("/")
def index():
    return render_template("index.html")

@bp.route("/upload_products", methods=["POST"])
def upload_products():
    logger = logging.getLogger("app.upload_products")
    f = request.files.get("file")
    if not f:
        flash("No file uploaded")
        logger.warning("No file uploaded")
        return redirect(url_for("main.index"))
    df = pd.read_csv(f)
    if "product_name" not in df.columns or "unit_price" not in df.columns:
        flash("CSV must have 'product_name' and 'unit_price'")
        logger.warning("CSV missing required columns")
        return redirect(url_for("main.index"))
    session = SessionLocal()
    try:
        logger.info("Uploading %d products", len(df))
        for _, row in df.iterrows():
            name = str(row["product_name"]).strip()
            price = float(row["unit_price"])
            existing = session.query(Product).filter_by(product_name=name).first()
            if existing:
                logger.debug("Updating price for %s", name)
                existing.unit_price = price
            else:
                session.add(Product(product_name=name, unit_price=price))
        session.commit()
    finally:
        session.close()
    flash(f"Loaded {len(df)} products.")
    return redirect(url_for("main.index"))

@bp.route("/upload_purchases", methods=["POST"])
def upload_purchases():
    logger = logging.getLogger("app.upload_purchases")
    f = request.files.get("file")
    if not f:
        flash("No file uploaded")
        logger.warning("No file uploaded")
        return redirect(url_for("main.index"))
    df = pd.read_csv(f)
    expected_cols = {"supermarket_id", "timestamp", "user_id", "items_list", "total_amount"}
    if not expected_cols.issubset(df.columns):
        flash(f"CSV must have columns: {', '.join(expected_cols)}")
        logger.warning("CSV missing required columns")
        return redirect(url_for("main.index"))
    inserted_count = 0
    session = SessionLocal()
    try:
        logger.info("Uploading %d purchases", len(df))
        for _, row in df.iterrows():
            supermarket_id = str(row["supermarket_id"]).strip()
            timestamp = parser.parse(str(row["timestamp"]))
            user_id = str(row["user_id"]).strip()
            items_list_str = str(row["items_list"])
            total_amount = float(row["total_amount"])
            user = session.query(User).filter_by(user_id=user_id).first()
            if not user:
                new_user = User(user_id=user_id)
                new_total = TotalUserPurchases(user_id=user_id, total_purchases=1)
                session.add(new_user)
                session.add(new_total)
                session.commit()
            else:
                existing_total = session.query(TotalUserPurchases).filter_by(user_id=user_id).first()
                existing_total.total_purchases = (existing_total.total_purchases or 0) + 1
                session.commit()
            items_list = [i.strip() for i in items_list_str.split(",") if i.strip()]
            for item_name in items_list:
                product_db_record = session.query(Product).filter_by(product_name=item_name).first()
                if not product_db_record:
                    flash(f"Product '{item_name}' not found in DB.")
                    logger.warning("Product '%s' doesn't exist in the Database", item_name)
                    session.rollback()
                    return redirect(url_for("main.index"))
                purchase_item = session.query(PurchaseItem).filter_by(product_id=product_db_record.id).first()
                if not purchase_item:
                    new_pi = PurchaseItem(product_id=product_db_record.id, total_purchases=1)
                    session.add(new_pi)
                else:
                    purchase_item.total_purchases = (purchase_item.total_purchases or 0) + 1
                session.commit()
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
    finally:
        session.close()
    flash(f"Loaded {inserted_count} purchases successfully.")
    logger.info("Loaded %d purchases successfully.", inserted_count)
    return redirect(url_for("main.index"))

@bp.route('/loyal_customers')
def loyal_customers():
    session = SessionLocal()
    try:
        threshold = 3
        loyal = session.query(User).join(TotalUserPurchases).filter(TotalUserPurchases.total_purchases >= threshold).order_by(TotalUserPurchases.total_purchases.desc()).all()
        trimmed = [(c.user_id, c.total_purchases.total_purchases) for c in loyal]
        logging.getLogger("app.loyal_customers").info("Number of loyal customers: %d", len(trimmed))
        return render_template('loyal_customers.html', loyal_customers_list=trimmed)
    finally:
        session.close()

@bp.route('/unique_customers')
def unique_customers():
    session = SessionLocal()
    try:
        count = session.query(User).count()
        logging.getLogger("app.unique_customers").info("Number of unique customers: %d", count)
        return render_template('unique_customers.html', unique_customers_count=count)
    finally:
        session.close()

@bp.route('/best_sellers')
def best_sellers():
    session = SessionLocal()
    try:
        logger = logging.getLogger("app.best_sellers")
        items = session.query(PurchaseItem).join(Product).order_by(PurchaseItem.total_purchases.desc()).all()
        top_sellers_numbers = []
        top_sellers = []
        for item in items:
            if len(set(top_sellers_numbers)) <= 3:
                checked_item_total_purchases = item.total_purchases
                checked_item_product_name = item.product.product_name
                if checked_item_total_purchases in top_sellers_numbers:
                    top_sellers.append((checked_item_product_name, checked_item_total_purchases))
                    continue
                else:
                    if len(set(top_sellers_numbers)) < 3:
                        top_sellers_numbers.append(checked_item_total_purchases)
                        top_sellers.append((checked_item_product_name, checked_item_total_purchases))
                    else:
                        break
            else:
                break
        logging.getLogger("app.best_sellers").info("Top selling products retrieved")
        return render_template('best_sellers.html', top_sellers=top_sellers)
    finally:
        session.close()

