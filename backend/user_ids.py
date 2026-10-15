
from app.database import SessionLocal
from app.models import User


def check_user_ids():
    db = SessionLocal()

    try:
        users = db.query(User).order_by(User.id).all()

        if not users:
            print("No users found in this database.")
            return

        print("\n========== SmartEvent User Details ==========\n")

        for user in users:
            print(
                f"ID: {user.id} | "
                f"Username: {user.username} | "
                f"Email: {user.email} | "
                f"Role: {user.role}"
            )

        print("\n=============================================\n")
        print(f"Total users: {len(users)}")

    except Exception as error:
        print("Error retrieving user details:", error)

    finally:
        db.close()


if __name__ == "__main__":
    check_user_ids()
