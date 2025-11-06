from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from .db import SessionLocal
from .models import Product, Purchase, PurchaseItem, User, TotalUserPurchases
from .logging_config import setup_logging
from dateutil import parser
import logging

bp = Blueprint("main", __name__)

@bp.route("/")
def index():
    return render_template("index.html")

@bp.route("/create", methods=["POST"])
def create_purchase():
    supermarket_id = request.form["supermarket_id"]
    user_id = request.form["user_id"]
    # start a new db session and add a new purchase using the form fields
    with SessionLocal() as session:
        purchase = Purchase(
            supermarket_id=supermarket_id,
            timestamp=parser.isoparse(request.form["timestamp"]),
            user_id=user_id,
            items_list=request.form["items_list"],
            total_amount=float(request.form["total_amount"])
        )
        session.add(purchase)
        session.commit()
        flash(f"Purchase created with ID {purchase.id}")
    # items_input = request.form["items"]
    #
    # try:
    #     items = parse_items(items_input)
    # except ValueError as e:
    #     flash(str(e))
    #     return redirect(url_for("index"))

    # with Session(engine) as session:
    #     purchase = Purchase(
    #         supermarket_id=supermarket_id,
    #         timestamp=datetime.utcnow(),
    #         user_id=user_id,
    #         total_amount=0
    #     )
    #     session.add(purchase)
    #     session.flush()  # get purchase.id
    #
    #     total = 0
    #     for it in items:
    #         product = session.query(Product).filter_by(product_name=it["product_name"]).first()
    #         if not product:
    #             flash(f"Product '{it['product_name']}' not found in DB.")
    #             session.rollback()
    #             return redirect(url_for("index"))
    #         line_total = float(product.unit_price) * it["quantity"]
    #         total += line_total
    #         session.add(PurchaseItem(
    #             purchase_id=purchase.id,
    #             product_id=product.id,
    #             quantity=it["quantity"],
    #             line_total=line_total
    #         ))
    #
    #     purchase.total_amount = round(total, 2)
    #     session.commit()
    #     flash(f"Purchase saved. Total = {purchase.total_amount}")
    return redirect(url_for("index"))

