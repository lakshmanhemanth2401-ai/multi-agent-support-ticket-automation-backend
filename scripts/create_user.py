import argparse
import getpass

from app.core.security import hash_password
from app.db.repositories.user_repository import UserRepository
from app.db.session import SessionLocal
from app.models.user import UserRole


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a support automation user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", choices=[role.value for role in UserRole], required=True)
    args = parser.parse_args()
    password = getpass.getpass("Password: ")
    if len(password) < 12:
        parser.error("password must contain at least 12 characters")
    with SessionLocal() as db:
        repository = UserRepository(db)
        if repository.get_by_email(args.email) is not None:
            parser.error("a user with that email already exists")
        repository.create(
            email=args.email,
            password_hash=hash_password(password),
            role=args.role,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
