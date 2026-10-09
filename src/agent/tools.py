from fastapi import HTTPException
from langchain_core.tools import tool
from src.employee_data.controller import EmployeeController
from src.employee_data.dtos import EmployeeResponse
from src.utils.db import Session


def _dump(item):
    return EmployeeResponse.model_validate(item).model_dump()


def _call(fn, *args):
    with Session() as db:
        try:
            result = fn(db, *args)
            return [_dump(r) for r in result] if isinstance(result, list) else _dump(result)
        except HTTPException as e:
            return {"error": e.detail}


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


TOOLS = [get_employee_by_id, get_all_employees, get_employees_by_name]
