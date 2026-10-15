
from app.database import SessionLocal
from app.models import User

USER_ID = 4
NEW_ROLE = "ORGANIZER"

db = SessionLocal()

try:
    user = db.query(User).filter(User.id == USER_ID).first()

    if user is None:
        print(f"User ID {USER_ID} not found.")
    else:
        print(f"Before: ID={user.id}, Username={user.username}, Role={user.role}")

        user.role = NEW_ROLE
        db.commit()
        db.refresh(user)

        print(f"After:  ID={user.id}, Username={user.username}, Role={user.role}")
        print("User role updated successfully.")

except Exception as error:
    db.rollback()
    print("Error updating user role:", error)

finally:
    db.close()
