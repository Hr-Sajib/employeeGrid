from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.auth.deps import get_current_user, require_admin
from src.employee_data.controller import EmployeeController
from src.employee_data.dtos import EmployeeCreate, EmployeeResponse, EmployeeUpdate
from src.utils.db import get_db

employee_routes = APIRouter(prefix="/employees", tags=["employees"], dependencies=[Depends(get_current_user)])


@employee_routes.get("", response_model=list[EmployeeResponse])
def get_all(db: Session = Depends(get_db)):
    return EmployeeController.get_all(db)


@employee_routes.get("/name/{name}", response_model=list[EmployeeResponse])
def get_by_name(name: str, db: Session = Depends(get_db)):
    return EmployeeController.get_by_name(db, name)


@employee_routes.get("/{employee_id}", response_model=EmployeeResponse)
def get_by_id(employee_id: int, db: Session = Depends(get_db)):
    return EmployeeController.get_by_id(db, employee_id)


@employee_routes.post("", response_model=EmployeeResponse, status_code=201, dependencies=[Depends(require_admin)])
def create(data: EmployeeCreate, db: Session = Depends(get_db)):
    return EmployeeController.create(db, data)


@employee_routes.put("/{employee_id}", response_model=EmployeeResponse, dependencies=[Depends(require_admin)])
def update(employee_id: int, data: EmployeeUpdate, db: Session = Depends(get_db)):
    return EmployeeController.update(db, employee_id, data)


@employee_routes.delete("/{employee_id}", dependencies=[Depends(require_admin)])
def delete(employee_id: int, db: Session = Depends(get_db)):
    return EmployeeController.delete(db, employee_id)
