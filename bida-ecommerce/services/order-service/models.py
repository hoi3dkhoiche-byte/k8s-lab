from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from db import Base

class OrderStatus(str, enum.Enum):
    pending = pending
    confirmed = confirmed
    paid = paid
    shipped = shipped
    delivered = delivered
    cancelled = cancelled

class Order(Base):
    __tablename__ = orders

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.pending)
    total_amount = Column(Numeric(12, 2), nullable=False)
    shipping_address = Column(Text, nullable=False)
    shipping_name = Column(String(100), nullable=False)
    shipping_phone = Column(String(20), nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship(OrderItem, back_populates=order, cascade=all, delete-orphan)
    payments = relationship(Payment, back_populates=order)

class OrderItem(Base):
    __tablename__ = order_items

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey(orders.id), nullable=False)
    product_id = Column(String(100), nullable=False)
    product_name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)

    order = relationship(Order, back_populates=items)

class Payment(Base):
    __tablename__ = payments

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey(orders.id), nullable=False)
    method = Column(String(50), nullable=False)
    status = Column(String(20), default=pending)
    amount = Column(Numeric(12, 2), nullable=False)
    transaction_id = Column(String(100), nullable=True)
    paid_at = Column(DateTime, nullable=True)

    order = relationship(Order, back_populates=payments)

class Inventory(Base):
    __tablename__ = inventory

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String(100), unique=True, index=True, nullable=False)
    quantity = Column(Integer, default=0)
    reserved = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
