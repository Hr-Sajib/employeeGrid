from fastapi import HTTPException
from sqlalchemy.orm import Session
from src.employee_data.dtos import EmployeeCreate, EmployeeUpdate
from src.employee_data.model import Employee


class EmployeeController:
    @staticmethod
    def get_all(db: Session) -> list[Employee]:
        return db.query(Employee).order_by(Employee.employee_id).all()

    @staticmethod
    def get_by_id(db: Session, employee_id: int) -> Employee:
        employee = db.get(Employee, employee_id)
        if not employee:
            raise HTTPException(404, "Employee not found")
        return employee

    @staticmethod
    def get_by_name(db: Session, name: str) -> list[Employee]:
        return (
            db.query(Employee)
            .filter(Employee.employee_name.ilike(f"%{name}%"))
            .order_by(Employee.employee_id)
            .all()
        )

    @staticmethod
    def create(db: Session, data: EmployeeCreate) -> Employee:
        employee = Employee(**data.model_dump())
        db.add(employee)
        db.commit()
        db.refresh(employee)
        return employee

    @staticmethod
    def update(db: Session, employee_id: int, data: EmployeeUpdate) -> Employee:
        employee = EmployeeController.get_by_id(db, employee_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(employee, field, value)
        db.commit()
        db.refresh(employee)
        return employee

    @staticmethod
    def delete(db: Session, employee_id: int) -> dict:
        employee = EmployeeController.get_by_id(db, employee_id)
        db.delete(employee)
        db.commit()
        return {"deleted": employee_id}
