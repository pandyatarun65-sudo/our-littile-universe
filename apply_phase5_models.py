"""
Fixes app/models.py for Phase 5 automatically (no copy-paste problems).

What it does:
  1. Makes a backup:  app/models_backup_before_phase5.py
  2. Removes any broken/half-pasted SpecialDate / DailyAnswer code
  3. Fixes line 1 import (adds `date`)
  4. Adds SpecialDate + DailyAnswer with correct indentation

Run from the project root (where run.py is):
    python apply_phase5_models.py
"""
import re
import shutil

PATH = 'app/models.py'

NEW_CODE = 'class SpecialDate(db.Model):\n    """Important dates: birthday, anniversary, first meeting, ..."""\n    __tablename__ = \'special_dates\'\n\n    id = db.Column(db.Integer, primary_key=True)\n    title = db.Column(db.String(200), nullable=False)\n    event_date = db.Column(db.Date, nullable=False)\n    category = db.Column(db.String(30), nullable=False, default=\'custom\')\n    description = db.Column(db.Text, nullable=True)\n    repeats_yearly = db.Column(db.Boolean, nullable=False, default=True)\n    created_by = db.Column(db.Integer, db.ForeignKey(\'users.id\'), nullable=False)\n    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))\n\n    creator = db.relationship(\'User\', backref=\'special_dates\', foreign_keys=[created_by])\n\n    def _in_year(self, year):\n        """Same day & month, but in the given year (29 Feb -> 28 Feb in non-leap years)."""\n        try:\n            return self.event_date.replace(year=year)\n        except ValueError:\n            return date(year, 2, 28)\n\n    def next_occurrence(self, today=None):\n        """Next date this event happens (today counts). None if a one-time date is already past."""\n        today = today or date.today()\n        if not self.repeats_yearly:\n            return self.event_date if self.event_date >= today else None\n        candidate = self._in_year(today.year)\n        if candidate < today:\n            candidate = self._in_year(today.year + 1)\n        return candidate\n\n    def days_until(self, today=None):\n        today = today or date.today()\n        nxt = self.next_occurrence(today)\n        return None if nxt is None else (nxt - today).days\n\n    def years_count(self, today=None):\n        """How many years since the original date (for \'3 years\' style labels)."""\n        nxt = self.next_occurrence(today)\n        if nxt is None or not self.repeats_yearly:\n            return 0\n        return nxt.year - self.event_date.year\n\n\nclass DailyAnswer(db.Model):\n    """One answer per user per day (editing that day\'s answer updates the same row)."""\n    __tablename__ = \'daily_answers\'\n    __table_args__ = (\n        db.UniqueConstraint(\'user_id\', \'answer_date\', name=\'uq_daily_answer_user_date\'),\n    )\n\n    id = db.Column(db.Integer, primary_key=True)\n    user_id = db.Column(db.Integer, db.ForeignKey(\'users.id\'), nullable=False)\n    answer_date = db.Column(db.Date, nullable=False)\n    question_text = db.Column(db.String(300), nullable=False)\n    answer = db.Column(db.Text, nullable=False)\n    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))\n    updated_at = db.Column(\n        db.DateTime,\n        default=lambda: datetime.now(timezone.utc),\n        onupdate=lambda: datetime.now(timezone.utc)\n    )\n\n    user = db.relationship(\'User\', backref=\'daily_answers\', foreign_keys=[user_id])\n'

text = open(PATH, encoding='utf-8').read()
shutil.copy(PATH, 'app/models_backup_before_phase5.py')

# 1) cut off anything from an earlier (broken) paste
cut_points = [i for i in (text.find('class SpecialDate'), text.find('=====')) if i != -1]
if cut_points:
    text = text[:min(cut_points)]
text = text.rstrip() + '\n\n\n'

# 2) make sure `date` is imported
if re.search(r'^from datetime import .*\bdate\b', text, flags=re.M) is None:
    if re.search(r'^from datetime import .*$', text, flags=re.M):
        text = re.sub(r'^from datetime import .*$', 'from datetime import datetime, timezone, date',
                      text, count=1, flags=re.M)
    else:
        text = 'from datetime import datetime, timezone, date\n' + text

# 3) add the new models
text += NEW_CODE

compile(text, PATH, 'exec')          # stops here if there is any syntax error
open(PATH, 'w', encoding='utf-8', newline='\n').write(text)
print('Done. app/models.py updated (backup: app/models_backup_before_phase5.py)')