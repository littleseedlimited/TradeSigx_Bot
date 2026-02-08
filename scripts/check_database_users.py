from utils.db import init_db, User
import logging

def check_users():
    db = init_db()
    try:
        users = db.session.query(User).all()
        print(f"Total Users: {len(users)}")
        for u in users:
            print(f"ID: {u.telegram_id} | Username: {u.username} | SuperAdmin: {u.is_super_admin} | Registered: {u.is_registered}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_users()
