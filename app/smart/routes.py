"""
Phase 5 routes: Special Dates and Daily Question.

SECURITY (backend, not JavaScript):
- every route has @login_required
- daily answers are always saved for current_user.id (never taken from the form)
- special dates: everyone logged in can view, only the creator can edit/delete
- every POST form must carry a csrf_token (checked in check_csrf)
"""
from datetime import date, datetime

from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import SpecialDate, DailyAnswer
from app.security import check_csrf, get_csrf_token
from app.smart.helpers import todays_question, daily_status
from app.notifications.services import notify

smart_bp = Blueprint('smart', __name__)

CATEGORIES = [
    ('birthday', 'Birthday'),
    ('anniversary', 'Anniversary'),
    ('first_meeting', 'First Meeting'),
    ('first_date', 'First Date'),
    ('custom', 'Other'),
]
CATEGORY_LABELS = dict(CATEGORIES)


# ------------------------------------------------------------------
# CSRF: the shared helper now lives in app/security.py (used by Phase 5 and 6)
# ------------------------------------------------------------------
@smart_bp.app_context_processor
def inject_csrf_token():
    # makes {{ csrf_token() }} available in ALL templates
    return {'csrf_token': get_csrf_token}


# ==================================================================
# SPECIAL DATES
# ==================================================================
def _read_special_date_form():
    """Reads + validates the form. Returns (form_data, parsed_date, error_message)."""
    form_data = {
        'title': request.form.get('title', '').strip(),
        'event_date': request.form.get('event_date', ''),
        'category': request.form.get('category', 'custom'),
        'description': request.form.get('description', '').strip(),
        'repeats_yearly': request.form.get('repeats_yearly') == 'on',
    }
    if form_data['category'] not in CATEGORY_LABELS:
        form_data['category'] = 'custom'

    parsed_date = None
    error = None
    if not form_data['title'] or not form_data['event_date']:
        error = 'Title and date are required.'
    elif len(form_data['title']) > 200:
        error = 'Title is too long (max 200 characters).'
    else:
        try:
            parsed_date = datetime.strptime(form_data['event_date'], '%Y-%m-%d').date()
        except ValueError:
            error = "That date doesn't look right — please pick it from the date field."
    return form_data, parsed_date, error


@smart_bp.route('/special-dates')
@login_required
def special_dates():
    today = date.today()
    everything = SpecialDate.query.all()
    upcoming = sorted(
        [sd for sd in everything if sd.next_occurrence(today) is not None],
        key=lambda sd: sd.next_occurrence(today),
    )
    past = sorted(
        [sd for sd in everything if sd.next_occurrence(today) is None],
        key=lambda sd: sd.event_date,
        reverse=True,
    )
    return render_template(
        'special_dates.html',
        upcoming=upcoming, past=past, today=today, category_labels=CATEGORY_LABELS,
    )


@smart_bp.route('/special-dates/add', methods=['GET', 'POST'])
@login_required
def add_special_date():
    if request.method == 'POST':
        check_csrf()
        form_data, parsed_date, error = _read_special_date_form()
        if error:
            flash(error, 'error')
            return render_template('special_date_form.html', form=form_data,
                                   categories=CATEGORIES, form_title='Add a Special Date')

        db.session.add(SpecialDate(
            title=form_data['title'],
            event_date=parsed_date,
            category=form_data['category'],
            description=form_data['description'] or None,
            repeats_yearly=form_data['repeats_yearly'],
            created_by=current_user.id,
        ))
        db.session.commit()
        flash('Special date saved.', 'success')
        return redirect(url_for('smart.special_dates'))

    blank = {'title': '', 'event_date': '', 'category': 'custom',
             'description': '', 'repeats_yearly': True}
    return render_template('special_date_form.html', form=blank,
                           categories=CATEGORIES, form_title='Add a Special Date')


@smart_bp.route('/special-dates/<int:date_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_special_date(date_id):
    sd = SpecialDate.query.get_or_404(date_id)
    if sd.created_by != current_user.id:
        abort(403)  # only the person who created it can change it

    if request.method == 'POST':
        check_csrf()
        form_data, parsed_date, error = _read_special_date_form()
        if error:
            flash(error, 'error')
            return render_template('special_date_form.html', form=form_data,
                                   categories=CATEGORIES, form_title='Edit Special Date')

        sd.title = form_data['title']
        sd.event_date = parsed_date
        sd.category = form_data['category']
        sd.description = form_data['description'] or None
        sd.repeats_yearly = form_data['repeats_yearly']
        db.session.commit()
        flash('Special date updated.', 'success')
        return redirect(url_for('smart.special_dates'))

    current = {
        'title': sd.title,
        'event_date': sd.event_date.isoformat(),
        'category': sd.category,
        'description': sd.description or '',
        'repeats_yearly': sd.repeats_yearly,
    }
    return render_template('special_date_form.html', form=current,
                           categories=CATEGORIES, form_title='Edit Special Date')


@smart_bp.route('/special-dates/<int:date_id>/delete', methods=['POST'])
@login_required
def delete_special_date(date_id):
    check_csrf()
    sd = SpecialDate.query.get_or_404(date_id)
    if sd.created_by != current_user.id:
        abort(403)
    db.session.delete(sd)
    db.session.commit()
    flash('Special date deleted.', 'success')
    return redirect(url_for('smart.special_dates'))


# ==================================================================
# DAILY QUESTION
# ==================================================================
@smart_bp.route('/daily', methods=['GET', 'POST'])
@login_required
def daily():
    today = date.today()
    question = todays_question(today)
    my_answer, partner, partner_answer = daily_status(current_user.id, today)

    if request.method == 'POST':
        check_csrf()
        text = request.form.get('answer', '').strip()

        if not text:
            flash('Write something before saving your answer.', 'error')
            return redirect(url_for('smart.daily'))
        if len(text) > 2000:
            flash('That answer is a bit long — please keep it under 2000 characters.', 'error')
            return redirect(url_for('smart.daily'))

        is_new_answer = my_answer is None
        if my_answer:
            my_answer.answer = text            # editing today's answer
        else:
            db.session.add(DailyAnswer(
                user_id=current_user.id,        # always the logged-in user
                answer_date=today,
                question_text=question,
                answer=text,
            ))
        try:
            db.session.commit()
            flash('Your answer is saved.', 'success')
            if is_new_answer and partner:       # editing an answer does not notify again
                notify(partner.id, 'daily_question', f"{current_user.name} answered today's question",
                       question, endpoint='smart.daily', actor_id=current_user.id)
        except IntegrityError:
            db.session.rollback()               # e.g. double-click created it twice
            flash('Your answer was already saved.', 'error')
        return redirect(url_for('smart.daily'))

    # Partner's answer TEXT is revealed only after I have answered myself.
    partner_answered = partner_answer is not None
    visible_partner_answer = partner_answer if my_answer else None

    # Past days: only days where I answered, plus partner's answer for those same days.
    history = (
        DailyAnswer.query
        .filter(DailyAnswer.user_id == current_user.id, DailyAnswer.answer_date < today)
        .order_by(DailyAnswer.answer_date.desc())
        .limit(30)
        .all()
    )
    partner_by_date = {}
    if partner and history:
        rows = DailyAnswer.query.filter(
            DailyAnswer.user_id == partner.id,
            DailyAnswer.answer_date.in_([h.answer_date for h in history]),
        ).all()
        partner_by_date = {row.answer_date: row for row in rows}

    return render_template(
        'daily.html',
        today=today, question=question, my_answer=my_answer, partner=partner,
        partner_answered=partner_answered, partner_answer=visible_partner_answer,
        history=history, partner_by_date=partner_by_date,
    )