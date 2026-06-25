"""Initialise the QA Café production database."""

from app import app, db, seed_database, seed_users


with app.app_context():
    db.create_all()
    seed_database()
    seed_users()

print("QA Café database initialised successfully.")