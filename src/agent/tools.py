from fastapi import HTTPException
from langchain_core.tools import tool
from pydantic import ValidationError
from src.employee_data.controller import EmployeeController
from src.employee_data.dtos import EmployeeCreate, EmployeeResponse, EmployeeUpdate
from src.utils.db import Session


def _dump(item):
    return EmployeeResponse.model_validate(item).model_dump()


def _call(fn, *args):
    with Session() as db:
        try:
            result = fn(db, *args)
            if isinstance(result, dict):
                return result
            return [_dump(r) for r in result] if isinstance(result, list) else _dump(result)
        except HTTPException as e:
            return {"error": e.detail}
        except ValidationError as e:
            return {"error": str(e)}


@tool
def get_employee_by_id(employee_id: int) -> dict:
    """Get one employee (name, monthly salary, KPI score 0-100, total absence) by numeric employee_id."""
    return _call(EmployeeController.get_by_id, employee_id)


@tool
def get_all_employees() -> list:
    """List all employees."""
    return _call(EmployeeController.get_all)


@tool
def get_employees_by_name(name: str) -> list:
    """Find employees whose name contains the given text (case-insensitive). May return several."""
    return _call(EmployeeController.get_by_name, name)


@tool
def create_employee(employee_name: str, monthly_salary: float, kpi_score: int, total_absence: int = 0) -> dict:
    """Create a new employee. kpi_score must be 0-100."""
    return _call(
        EmployeeController.create,
        EmployeeCreate(employee_name=employee_name, monthly_salary=monthly_salary, kpi_score=kpi_score, total_absence=total_absence),
    )


@tool
def update_employee(
    employee_id: int,
    employee_name: str | None = None,
    monthly_salary: float | None = None,
    kpi_score: int | None = None,
    total_absence: int | None = None,
) -> dict:
    """Update only the given fields of an employee. kpi_score must be 0-100."""
    fields = {k: v for k, v in locals().items() if k != "employee_id" and v is not None}
    return _call(EmployeeController.update, employee_id, EmployeeUpdate(**fields))


@tool
def delete_employee(employee_id: int) -> dict:
    """Permanently delete an employee by employee_id."""
    return _call(EmployeeController.delete, employee_id)


ALL_TOOLS = [get_employee_by_id, get_all_employees, get_employees_by_name, create_employee, update_employee, delete_employee]

ENABLED_TOOLS = ALL_TOOLS
