"""
Small helper functions used by the dashboard and the Phase 5 routes.
No database changes happen here — these only READ data.
"""
import calendar
from datetime import date, datetime, timezone

from app import db
from app.models import Memory, SpecialDate, SecretLetter, User, DailyAnswer


# ------------------------------------------------------------------
# Daily questions. Add or edit freely — the list is just Python.
# The question of the day = list position based on today's date, so
# both users always see the SAME question on the same day.
# ------------------------------------------------------------------
DAILY_QUESTIONS = [
    "What was your favorite moment today?",
    "What is one thing you want us to do together?",
    "What made you smile today?",
    "What is one memory you never want to forget?",
    "What is something small I do that you love?",
    "Where would you take us for a surprise weekend?",
    "What song reminds you of us right now?",
    "What is one thing you're grateful for today?",
    "What is a dream you haven't told me about yet?",
    "What is your favorite thing about our mornings or nights?",
    "What is one thing you'd like to learn together?",
    "Describe our perfect lazy day in three lines.",
    "What is something you were proud of this week?",
    "What is one thing that made you feel loved recently?",
    "If we could relive one day, which one would you pick?",
    "What is a tiny habit of mine that makes you laugh?",
    "What food would you happily share with me anywhere?",
    "What is one wish you have for us this year?",
    "What was the first thing you noticed about me?",
    "What is one thing you want to say but rarely do?",
    "Which photo of us is your favorite, and why?",
    "What is a place that feels like home to you?",
    "What is something new you'd like us to try?",
    "What is one thing I can do to make your week easier?",
    "What is a moment that felt small but meant a lot?",
    "Which of our memories makes you smile the most?",
    "What are you looking forward to the most right now?",
    "What is your favorite way for us to spend time together?",
    "What is one thing you admire about me?",
    "What would you write on a note to us, ten years from now?",
]

# A tiny personal line on the dashboard, changes every day.
DAILY_NOTES = [
    "Some days are ordinary — until you look back at them.",
    "Small moments are the ones that stay.",
    "Keep collecting the little things.",
    "Every memory here started as an ordinary day.",
    "Two people, one quiet corner of the universe.",
    "Today is a good day to add something to your story.",
    "The best memories are usually the unplanned ones.",
]


def todays_question(today=None):
    today = today or date.today()
    return DAILY_QUESTIONS[today.toordinal() % len(DAILY_QUESTIONS)]


def todays_note(today=None):
    today = today or date.today()
    return DAILY_NOTES[today.toordinal() % len(DAILY_NOTES)]


def memories_on_this_day(today=None):
    """
    Memories from the same day + month in PREVIOUS years.
    Nothing is copied or saved — we just filter the memories table.
    """
    today = today or date.today()
    month_days = [today.strftime('%m-%d')]
    # A memory from 29 Feb should still show up on 28 Feb in non-leap years.
    if month_days[0] == '02-28' and not calendar.isleap(today.year):
        month_days.append('02-29')

    return (
        Memory.query
        .filter(
            db.func.strftime('%m-%d', Memory.memory_date).in_(month_days),
            Memory.memory_date < date(today.year, 1, 1),
        )
        .order_by(Memory.memory_date.desc())
        .all()
    )


def upcoming_special_dates(limit=3, today=None):
    """Next special dates, soonest first. (Few rows, so sorting in Python is fine.)"""
    today = today or date.today()
    coming = [sd for sd in SpecialDate.query.all() if sd.next_occurrence(today) is not None]
    coming.sort(key=lambda sd: sd.next_occurrence(today))
    return coming[:limit]


def locked_surprise_count(user_id):
    """
    How many still-sealed surprises are waiting for this user.
    Only a NUMBER is returned — no titles, hints or bodies.
    Uses the same UTC date as SecretLetter.is_unlocked() so both always agree.
    """
    today_utc = datetime.now(timezone.utc).date()
    return (
        SecretLetter.query
        .filter(
            SecretLetter.recipient_id == user_id,
            SecretLetter.unlock_date.isnot(None),
            SecretLetter.unlock_date > today_utc,
        )
        .count()
    )


def daily_status(user_id, today=None):
    """
    Returns (my_answer, partner, partner_answer) for today.
    NOTE: partner_answer's TEXT must only be shown if my_answer exists.
    """
    today = today or date.today()
    my_answer = DailyAnswer.query.filter_by(user_id=user_id, answer_date=today).first()
    partner = User.query.filter(User.id != user_id).first()
    partner_answer = None
    if partner:
        partner_answer = DailyAnswer.query.filter_by(user_id=partner.id, answer_date=today).first()
    return my_answer, partner, partner_answer