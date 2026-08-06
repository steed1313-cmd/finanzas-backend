from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="USER")
    forex_enabled = Column(Integer, default=0)
    
    # Subscription fields
    expiration_date = Column(String, nullable=True)  # Store ISO date string
    last_payment_date = Column(String, nullable=True) # When they last paid
    subscription_type = Column(String, default="GRATUITO")  # "GRATUITO", "MENSUAL", "VITALICIO"
    is_suspended = Column(Integer, default=0) # 0 = False, 1 = True (SQLite boolean representation)

    monthly_data = relationship("MonthlyData", back_populates="owner")


class MonthlyData(Base):
    __tablename__ = "monthly_data"

    id = Column(Integer, primary_key=True, index=True)
    month_key = Column(String, index=True)  # e.g., "Julio-2026"
    data = Column(Text)  # Store JSON string of the month's data
    user_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="monthly_data")
