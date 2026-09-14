"""Create the first administrator locally without placing a password in shell history."""

import argparse
from getpass import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User, UserRole


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an SCosmetics administrator")
    parser.add_argument("--email", required=True)
    parser.add_argument("--first-name", required=True)
    parser.add_argument("--last-name", required=True)
    parser.add_argument("--phone", required=True)
    args = parser.parse_args()
    email = args.email.strip().lower()
    if "@" not in email:
        parser.error("Enter a valid email address")
    password = getpass("New admin password (8+ characters): ")
    confirmation = getpass("Confirm password: ")
    if len(password) < 8 or password != confirmation:
        parser.error("Passwords must match and contain at least 8 characters")
    with SessionLocal() as session:
        if session.scalar(select(User.id).where(User.email == email)) is not None:
            parser.error("This email already belongs to an account; no role was changed")
        session.add(User(
            first_name=args.first_name.strip(),
            last_name=args.last_name.strip(),
            email=email,
            phone=args.phone.strip(),
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
        ))
        session.commit()
    print("Administrator created. The password was not printed or saved in the command.")


if __name__ == "__main__":
    main()
