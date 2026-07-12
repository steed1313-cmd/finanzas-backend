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

    monthly_data = relationship("MonthlyData", back_populates="owner")


class MonthlyData(Base):
    __tablename__ = "monthly_data"

    id = Column(Integer, primary_key=True, index=True)
    month_key = Column(String, index=True)  # e.g., "Julio-2026"
    data = Column(Text)  # Store JSON string of the month's data
    user_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="monthly_data")
