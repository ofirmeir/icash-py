from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy import func, desc

from .db import SessionLocal
from .models import Product, PurchaseItem, User

from .upload_service import (
    process_products_upload_from_request,
    process_purchases_upload_from_request,
    FileMissingError,
    CSVParseError,
    MissingColumnsError,
    ProductNotFoundError,
    ProcessingError,
)
import logging

bp = Blueprint("main", __name__)

@bp.route("/")
def index():
    return render_template("index.html")

@bp.route("/upload_products", methods=["POST"])
def upload_products():
    logger = logging.getLogger("app.upload_products")
    try:
        result = process_products_upload_from_request(request)
        flash(result.message or f"Loaded {result.inserted_count} products.")
        return redirect(url_for("main.index"))
    except FileMissingError as e:
        logger.warning(str(e))
        flash(str(e))
        return redirect(url_for("main.index"))
    except MissingColumnsError as e:
        logger.warning(str(e))
        flash(f"CSV must have 'product_name' and 'unit_price'")
        return redirect(url_for("main.index"))
    except (CSVParseError, ProcessingError) as e:
        logger.error("Failed to process products upload: %s", e)
        flash("Failed to process uploaded products file")
        return redirect(url_for("main.index"))

@bp.route("/upload_purchases", methods=["POST"])
def upload_purchases():
    logger = logging.getLogger("app.upload_purchases")
    try:
        result = process_purchases_upload_from_request(request)
        flash(result.message or f"Loaded {result.inserted_count} purchases successfully.")
        logger.info("Loaded %d purchases successfully.", result.inserted_count)
        return redirect(url_for("main.index"))
    except FileMissingError as e:
        logger.warning(str(e))
        flash(str(e))
        return redirect(url_for("main.index"))
    except MissingColumnsError as e:
        logger.warning(str(e))
        flash(f"CSV must have columns: supermarket_id, timestamp, user_id, items_list, total_amount")
        return redirect(url_for("main.index"))
    except ProductNotFoundError as e:
        logger.warning("Product referenced in purchases file not found: %s", e.product_name)
        flash(f"Product referenced in purchases file not found: {e.product_name}")
        return redirect(url_for("main.index"))
    except (CSVParseError, ProcessingError) as e:
        logger.error("Failed to process purchases upload: %s", e)
        flash("Failed to process uploaded purchases file")
        return redirect(url_for("main.index"))

@bp.route('/loyal_customers')
def loyal_customers():
    session = SessionLocal()
    try:
        threshold = 3
        # Sum PurchaseItem.total_purchases per user and filter by threshold
        q = (
            session.query(
                User.uuid.label("uuid"),
                func.coalesce(func.sum(PurchaseItem.total_purchases), 0).label("total_purchases")
            )
            .join(PurchaseItem, PurchaseItem.user_id == User.id)
            .group_by(User.id)
            .having(func.sum(PurchaseItem.total_purchases) > threshold)
            .order_by(desc("total_purchases"))
        )
        results = q.all()
        # results is list of (uuid, total_purchases)
        logging.getLogger("app.loyal_customers").info("Number of loyal customers: %d", len(results))
        return render_template('loyal_customers.html', loyal_customers_list=results)
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
        # Aggregate purchase counts per product (count rows in purchase_items)
        q = (
            session.query(
                Product.product_name.label("product_name"),
                func.count(PurchaseItem.id).label("purchases"),
            )
            .join(PurchaseItem, PurchaseItem.product_id == Product.id)
            .group_by(Product.id)
            .order_by(desc("purchases"))
        )

        rows = q.all()
        top_amounts = set()
        top_sellers = []
        # Iterate ordered rows and keep at most three distinct purchase counts
        for row in rows:
            purchases = int(row.purchases)
            product_name = row.product_name
            if purchases in top_amounts:
                top_sellers.append((product_name, purchases))
                continue
            if len(top_amounts) < 3:
                top_amounts.add(purchases)
                top_sellers.append((product_name, purchases))
                continue
            # already have three distinct top amounts, stop
            break
        logging.getLogger("app.best_sellers").info("Top selling products retrieved")
        return render_template('best_sellers.html', top_sellers=top_sellers)
    finally:
        session.close()

