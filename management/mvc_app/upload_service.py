from dataclasses import dataclass
from typing import Optional, Set
import pandas as pd
from dateutil import parser
import logging

from .db import SessionLocal
from .models import Product, Purchase, PurchaseItem, User, Store


class UploadError(Exception):
    """Base class for upload-related errors"""


class FileMissingError(UploadError):
    pass


class CSVParseError(UploadError):
    pass


class MissingColumnsError(UploadError):
    def __init__(self, missing_columns):
        super().__init__(f"Missing columns: {', '.join(missing_columns)}")
        self.missing_columns = missing_columns


class ProcessingError(UploadError):
    pass


class ProductNotFoundError(ProcessingError):
    def __init__(self, product_name: str):
        super().__init__(f"Product not found: {product_name}")
        self.product_name = product_name


@dataclass
class UploadResult:
    success: bool
    inserted_count: int = 0
    message: Optional[str] = None


def read_csv_from_request(request, required_columns: Optional[Set[str]] = None) -> pd.DataFrame:
    logger = logging.getLogger("app.upload_service.read_csv")
    f = request.files.get("file")
    if not f:
        logger.warning("No file uploaded")
        raise FileMissingError("No file uploaded")

    try:
        # read as strings to avoid dtype surprises and preserve quoting
        df = pd.read_csv(f, dtype=str, keep_default_na=False)
    except Exception as exc:
        logger.exception("Failed to parse CSV: %s", exc)
        raise CSVParseError(str(exc)) from exc

    if required_columns:
        missing = set(required_columns) - set(df.columns)
        if missing:
            logger.warning("CSV missing required columns: %s", missing)
            raise MissingColumnsError(missing)

    return df


def process_products_upload_from_request(request) -> UploadResult:
    logger = logging.getLogger("app.upload_products")
    df = read_csv_from_request(request, required_columns={"product_name", "unit_price"})
    session = SessionLocal()
    try:
        logger.info("Uploading %d products", len(df))
        # single transaction for the whole file
        with session.begin():
            for _, row in df.iterrows():
                name = str(row["product_name"]).strip()
                try:
                    price = float(row["unit_price"])
                except Exception:
                    raise ProcessingError(f"Invalid unit_price for product '{name}'")
                existing = session.query(Product).filter_by(product_name=name).first()
                if existing:
                    logger.debug("Updating price for %s", name)
                    existing.unit_price = price
                else:
                    session.add(Product(product_name=name, unit_price=price))
        return UploadResult(success=True, inserted_count=len(df), message=f"Loaded {len(df)} products.")
    except UploadError:
        # re-raise known upload errors
        session.rollback()
        raise
    except Exception as exc:
        logger.exception("Error processing products upload: %s", exc)
        session.rollback()
        raise ProcessingError(str(exc)) from exc
    finally:
        session.close()


def process_purchases_upload_from_request(request) -> UploadResult:
    logger = logging.getLogger("app.upload_purchases")
    required = {"supermarket_id", "timestamp", "user_id", "items_list", "total_amount"}
    df = read_csv_from_request(request, required_columns=required)
    # parse timestamps once using pandas for better performance and clearer errors
    try:
        df["_parsed_timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    except Exception as exc:
        logger.exception("Failed to parse timestamp column: %s", exc)
        raise CSVParseError("Failed to parse timestamp column") from exc

    session = SessionLocal()
    inserted_count = 0
    try:
        logger.info("Uploading %d purchases", len(df))
        # use a single transaction for the whole file to keep DB consistent
        with session.begin():
            for idx, row in df.iterrows():
                supermarket_id = str(row["supermarket_id"]).strip()
                timestamp = row.get("_parsed_timestamp")
                if pd.isna(timestamp):
                    raise ProcessingError(f"Invalid timestamp at row {idx}")
                user_id = str(row["user_id"]).strip()
                items_list_str = str(row["items_list"])
                try:
                    total_amount = float(row["total_amount"])
                except Exception:
                    raise ProcessingError(f"Invalid total_amount at row {idx}")

                # Handle User: CSV contains the client-visible UUID (string). Find by User.uuid
                user = session.query(User).filter_by(uuid=user_id).first()
                if not user:
                    logger.debug("Creating new user with uuid %s", user_id)
                    new_user = User(uuid=user_id)
                    session.add(new_user)
                    session.flush()
                    user = new_user

                # Handle Store
                store = session.query(Store).filter_by(supermarket_id=supermarket_id).first()
                if not store:
                    logger.debug("Store %s doesn't exist in the database", supermarket_id)
                    new_store = Store(supermarket_id=supermarket_id)
                    session.add(new_store)
                    # flush so subsequent queries in this transaction will see the inserted store
                    session.flush()
                    store = new_store

                # Create Purchase
                purchase = Purchase(
                    supermarket_id=store.id,
                    timestamp=timestamp,
                    user_id=user.id,
                    total_amount=total_amount
                )
                session.add(purchase)
                session.flush()  # flush to get purchase.id for PurchaseItems
                inserted_count += 1

                # Handle Items
                items_list = [i.strip() for i in items_list_str.split(",") if i.strip()]
                for item_name in items_list:
                    product_db_record = session.query(Product).filter_by(product_name=item_name).first()
                    if not product_db_record:
                        logger.debug("Product not found %s", item_name)
                        raise ProductNotFoundError(item_name)

                    purchase_item = session.query(PurchaseItem).filter_by(
                        product_id=product_db_record.id,
                        user_id=user.id,
                        purchase_id=purchase.id,
                    ).first()
                    if not purchase_item:
                        logger.debug("Creating new PurchaseItem for product %s and user %s", item_name, user.id)
                        new_pi = PurchaseItem(
                            product_id=product_db_record.id,
                            user_id=user.id,
                            total_purchases=1,
                            purchase_id=purchase.id,
                        )
                        session.add(new_pi)
                        # ensure the new PurchaseItem is visible to subsequent queries in this transaction
                        session.flush()
                    else:
                        purchase_item.total_purchases += 1
                # commit is handled by the transaction context manager (with session.begin())
        return UploadResult(success=True, inserted_count=inserted_count, message=f"Loaded {inserted_count} purchases successfully.")
    except UploadError:
        session.rollback()
        raise
    except Exception as exc:
        logger.exception("Error processing purchases upload: %s", exc)
        session.rollback()
        raise ProcessingError(str(exc)) from exc
    finally:
        session.close()




