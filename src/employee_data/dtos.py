from pydantic import BaseModel, ConfigDict, Field


class EmployeeCreate(BaseModel):
    employee_name: str
    monthly_salary: float = Field(ge=0)
    kpi_score: int = Field(ge=0, le=100)
    total_absence: int = Field(default=0, ge=0)


class EmployeeUpdate(BaseModel):
    employee_name: str | None = None
    monthly_salary: float | None = Field(default=None, ge=0)
    kpi_score: int | None = Field(default=None, ge=0, le=100)
    total_absence: int | None = Field(default=None, ge=0)


class EmployeeResponse(EmployeeCreate):
    model_config = ConfigDict(from_attributes=True)

    employee_id: int
