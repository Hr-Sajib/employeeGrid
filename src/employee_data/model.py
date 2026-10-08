from sqlalchemy import CheckConstraint, Column, Float, Integer, String
from src.utils.db import Base


class Employee(Base):
    __tablename__ = "employee_data"
    __table_args__ = (CheckConstraint("kpi_score BETWEEN 0 AND 100"),)

    employee_id = Column(Integer, primary_key=True, autoincrement=True)
    employee_name = Column(String, nullable=False)
    monthly_salary = Column(Float, nullable=False)
    kpi_score = Column(Integer, nullable=False)
    total_absence = Column(Integer, nullable=False, default=0)
