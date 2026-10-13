"""Create an account:  python -m src.auth.create_user --email you@company.com --name "Your Name" --role admin"""
import argparse
import getpass
from src.auth.controller import AuthController
from src.utils.db import Base, Session, engine

parser = argparse.ArgumentParser()
parser.add_argument("--email", required=True)
parser.add_argument("--name", required=True)
parser.add_argument("--role", choices=["admin", "viewer"], default="viewer")
parser.add_argument("--password", help="leave out to be asked (safer: it stays out of your shell history)")
args = parser.parse_args()

Base.metadata.create_all(engine)
password = args.password or getpass.getpass("Password: ")
if len(password) < 8:
    raise SystemExit("Use a password of at least 8 characters")

with Session() as db:
    user = AuthController.create_user(db, args.email, args.name, password, args.role)
    print(f"created {user.role} account for {user.email}")
