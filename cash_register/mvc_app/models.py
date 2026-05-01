from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, TIMESTAMP, text
from sqlalchemy.orm import relationship
from .db import Base
from shared.guid import GUID

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    product_name = Column(String, unique=True, nullable=False)
    unit_price = Column(Numeric, nullable=False)

class Purchase(Base):
    __tablename__ = "purchases"
    id = Column(Integer, primary_key=True)
    supermarket_id = Column(String, ForeignKey("stores.supermarket_id"), nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    items_list = Column(String, nullable=False)
    total_amount = Column(Numeric, nullable=False)

class PurchaseItem(Base):
    __tablename__ = "purchase_items"
    id = Column(Integer, primary_key=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    product = relationship("Product")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_purchases = Column(Integer, nullable=False, default=1)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    uuid = Column(GUID(), unique=True, nullable=False)
    total_purchases = relationship("TotalUserPurchases", back_populates="user", uselist=False)

class TotalUserPurchases(Base):
    __tablename__ = "user_total_purchases"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="total_purchases")
    total_purchases = Column(Integer, nullable=True)

class Store(Base):
    __tablename__ = "stores"
    id = Column(Integer, primary_key=True)
    supermarket_id = Column(String, unique=True, nullable=False)

