"""
One-time script: creates ONLY the new Phase 5 tables
(special_dates, daily_answers).

db.create_all() skips tables that already exist, so users, memories,
photos, secret_letters and the old backup tables are NOT touched.

Run from the project root (where run.py is):
    python create_phase5_tables.py
"""
from sqlalchemy import inspect

from app import create_app, db
from app.models import SpecialDate, DailyAnswer  # noqa: F401  (makes sure models are loaded)

app = create_app()

with app.app_context():
    db.create_all()
    tables = sorted(inspect(db.engine).get_table_names())
    print('Tables in database now:')
    for name in tables:
        print('  -', name)
    for needed in ('special_dates', 'daily_answers'):
        print(('OK      ' if needed in tables else 'MISSING ') + needed)