from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from .db import SessionLocal
from .models import Product, Purchase, User, Store, PurchaseItem, TotalUserPurchases
from dateutil import parser
import uuid
import json
from datetime import datetime
import logging

bp = Blueprint("main", __name__)

@bp.route("/")
def index():
    # fetch products and stores from the database and render the template
    with SessionLocal() as session:
        products = session.query(Product).all()
        stores = session.query(Store).all()

    return render_template("index.html", products=products, stores=stores)

@bp.route("/create", methods=["POST"])
def create_purchase():
    logger = logging.getLogger("app.create_purchase")
    logger.info("Creating new purchase from form data")
    # read store_id from the form (mapped to Purchase.supermarket_id)
    store_id = request.form.get("store_id")
    user_id = request.form.get("user_id")
    items_raw = request.form.get("items_list")
    # parse and validate items_list server-side to prevent tampering
    try:
        items = json.loads(items_raw or "[]")
    except Exception:
        flash("Invalid items_list format")
        return redirect(url_for("index"))

    if not isinstance(items, list) or len(items) == 0:
        flash("Please add at least one product before submitting")
        return redirect(url_for("index"))

    # collect product ids and check duplicates
    product_ids = []
    try:
        for it in items:
            logger.debug("checking the validity of item entry: %s", it)
            # expect each item to be a mapping with product_id
            pid = it.get("product_id") if isinstance(it, dict) else None
            if pid is None:
                raise ValueError("missing product_id")
            # normalize to int (Product.id is integer)
            pid_int = int(pid)
            product_ids.append(pid_int)
    except Exception:
        flash("Invalid items entries; expected product_id values")
        return redirect(url_for("index"))

    if len(set(product_ids)) != len(product_ids):
        logger.warning("duplicate product_ids")
        flash("Duplicate products found in items list")
        return redirect(url_for("index"))

    with SessionLocal() as session:
        # fetch products and ensure all exist
        db_products = session.query(Product).filter(Product.id.in_(product_ids)).all()
        if len(db_products) != len(product_ids):
            logger.warning("One or more selected products were not found in the database")
            flash("One or more selected products were not found in the database")
            return redirect(url_for("index"))

        # build price lookup and recompute server-side total (one unit per product)
        price_by_id = {p.id: float(p.unit_price) for p in db_products}
        server_total = sum(price_by_id[pid] for pid in product_ids)

        # canonicalize items list to include name and price from DB
        canonical_items = []
        for pid in product_ids:
            p = next((x for x in db_products if x.id == pid), None)
            canonical_items.append(p.product_name)
        items_list = ",".join(canonical_items)

        # parse timestamp from form or fallback to current UTC datetime
        ts_raw = request.form.get("timestamp")
        if ts_raw:
            try:
                ts = parser.isoparse(ts_raw)
            except Exception:
                ts = datetime.utcnow()
        else:
            ts = datetime.now()

        # create purchase with server-calculated total to prevent client tampering
        purchase = Purchase(
            supermarket_id=store_id,
            timestamp=ts,
            user_id=user_id,
            items_list=items_list,
            total_amount=server_total
        )
        session.add(purchase)
        session.commit()
        # handle user creation if not exists
        user = session.query(User).filter_by(user_id=user_id).first()
        if not user:
            logger.debug("Creating new user %s", user_id)
            new_user = User(user_id=user_id)
            session.add(new_user)
        else:
            logger.debug("User %s exists, no need to create", user_id)
            user_purchases = session.query(TotalUserPurchases).filter_by(user_id=user_id).first()
            if not user_purchases:
                logger.debug("Creating TotalUserPurchases record for user %s", user_id)
                new_total = TotalUserPurchases(user_id=user_id, total_purchases=1)
                session.add(new_total)
            else:
                logger.debug("Updating TotalUserPurchases for user %s", user_id)
                user_purchases.total_purchases += 1
        session.commit()
        # handle purchaseItems
        for pid in product_ids:
            product_db_record = session.query(Product).filter_by(id=pid).first()
            if not product_db_record:
                logger.debug("Product %s doesn't exist in the database", pid)
                session.rollback()
                flash(f"Product with ID {pid} does not exist")
                return redirect(url_for("index"))
            # Handle PurchaseItem
            purchase_item = session.query(PurchaseItem).filter_by(product_id=product_db_record.id).first()
            if not purchase_item:
                logger.debug("PurchaseItem for '%s' doesn't exist in the database", product_db_record.product_name)
                new_item = PurchaseItem(product_id=product_db_record.id, total_purchases=1)
                session.add(new_item)
            else:
                purchase_item.total_purchases += 1
                session.add(purchase_item)
        session.commit()
        flash("Purchase created")

    return redirect(url_for("main.index"))


@bp.route("/create_user", methods=["POST"])
def create_user():
    """Create a new user with a unique UUID and return it as JSON.
    The UUID is ensured not to already exist in the users table.
    """
    with SessionLocal() as session:
        # try a few times to avoid extremely rare collisions
        for _ in range(10):
            new_uuid = str(uuid.uuid4())
            exists = session.query(User).filter_by(user_id=new_uuid).first()
            if not exists:
                user = User(user_id=new_uuid)
                session.add(user)
                session.commit()
                return jsonify({"user_id": new_uuid})

    return jsonify({"error": "could not generate unique user id"}), 500
