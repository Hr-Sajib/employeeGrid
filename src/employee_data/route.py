from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.employee_data.controller import EmployeeController
from src.employee_data.dtos import EmployeeCreate, EmployeeResponse, EmployeeUpdate
from src.utils.db import get_db

employee_routes = APIRouter(prefix="/employees", tags=["employees"])


@employee_routes.get("", response_model=list[EmployeeResponse])
def get_all(db: Session = Depends(get_db)):
    return EmployeeController.get_all(db)


@employee_routes.get("/name/{name}", response_model=list[EmployeeResponse])
def get_by_name(name: str, db: Session = Depends(get_db)):
    return EmployeeController.get_by_name(db, name)


@employee_routes.get("/{employee_id}", response_model=EmployeeResponse)
def get_by_id(employee_id: int, db: Session = Depends(get_db)):
    return EmployeeController.get_by_id(db, employee_id)


@employee_routes.post("", response_model=EmployeeResponse, status_code=201)
def create(data: EmployeeCreate, db: Session = Depends(get_db)):
    return EmployeeController.create(db, data)


@employee_routes.put("/{employee_id}", response_model=EmployeeResponse)
def update(employee_id: int, data: EmployeeUpdate, db: Session = Depends(get_db)):
    return EmployeeController.update(db, employee_id, data)


@employee_routes.delete("/{employee_id}")
def delete(employee_id: int, db: Session = Depends(get_db)):
    return EmployeeController.delete(db, employee_id)
