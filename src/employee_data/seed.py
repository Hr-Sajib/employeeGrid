from src.employee_data.model import Employee
from src.utils.db import Base, Session, engine

EMPLOYEES = [
    ("Alice Johnson", 5200, 92, 2),
    ("Bob Smith", 4100, 78, 5),
    ("Carol Williams", 6300, 88, 1),
    ("David Brown", 3800, 65, 9),
    ("Emma Davis", 7100, 95, 0),
    ("Frank Miller", 4500, 71, 6),
    ("Grace Wilson", 5600, 84, 3),
    ("Henry Moore", 3500, 58, 12),
    ("Alice Taylor", 4900, 80, 4),
    ("Jack Anderson", 6800, 90, 2),
]

if __name__ == "__main__":
    Base.metadata.create_all(engine)
    with Session() as db:
        if db.query(Employee).count():
            print("table not empty, skipping seed")
        else:
            db.add_all(Employee(employee_name=n, monthly_salary=s, kpi_score=k, total_absence=a) for n, s, k, a in EMPLOYEES)
            db.commit()
            print("seeded", db.query(Employee).count())
