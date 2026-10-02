from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user

from app import db
from app.models import Memory, Photo, User
from app.utils import save_uploaded_photo, delete_photo_file
from app.smart.helpers import (
    memories_on_this_day,
    upcoming_special_dates,
    locked_surprise_count,
    todays_question,
    todays_note,
    daily_status,
)

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def dashboard():
    today = date.today()

    # --- existing dashboard data (unchanged) ---
    memory_count = Memory.query.count()
    latest_memory = Memory.query.order_by(Memory.memory_date.desc()).first()
    latest_photo = Photo.query.order_by(Photo.uploaded_at.desc()).first()

    hour = datetime.now().hour
    if hour < 12:
        greeting = 'Good morning'
    elif hour < 18:
        greeting = 'Good afternoon'
    else:
        greeting = 'Good evening'

    # --- Phase 5 additions ---
    my_answer, partner, partner_answer = daily_status(current_user.id, today)

    return render_template(
        'dashboard.html',
        latest_memory=latest_memory,
        memory_count=memory_count,
        latest_photo=latest_photo,
        greeting=greeting,
        today=today,
        on_this_day=memories_on_this_day(today),
        upcoming_dates=upcoming_special_dates(limit=3, today=today),
        locked_count=locked_surprise_count(current_user.id),
        question=todays_question(today),
        my_answer=my_answer,
        partner=partner,
        partner_answered=partner_answer is not None,   # only True/False, never the text
        daily_note=todays_note(today),
    )


@main_bp.route('/timeline')
@login_required
def timeline():
    all_memories = Memory.query.order_by(Memory.memory_date.desc()).all()
    return render_template('timeline.html', memories=all_memories)


def _parse_memory_date(date_string):
    return datetime.strptime(date_string, '%Y-%m-%d').date()


@main_bp.route('/memories/add', methods=['GET', 'POST'])
@login_required
def add_memory():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        memory_date_str = request.form.get('memory_date', '')
        caption = request.form.get('caption', '').strip()
        location = request.form.get('location', '').strip()[:200]   # Phase 5: optional

        if not title or not memory_date_str:
            flash('Title and date are required.', 'error')
            return render_template('memory_form.html', memory=None, form_title='Add a Memory')

        try:
            memory_date = _parse_memory_date(memory_date_str)
        except ValueError:
            flash('That date doesn\'t look right — please pick it from the date field.', 'error')
            return render_template('memory_form.html', memory=None, form_title='Add a Memory')

        memory = Memory(
            title=title,
            description=description,
            memory_date=memory_date,
            location=location or None,
            created_by=current_user.id,
        )
        db.session.add(memory)
        db.session.commit()

        photo_file = request.files.get('photo')
        if photo_file and photo_file.filename:
            saved_path = save_uploaded_photo(photo_file)
            if saved_path:
                photo = Photo(memory_id=memory.id, file_path=saved_path, caption=caption)
                db.session.add(photo)
                db.session.commit()
            else:
                flash('Memory saved, but that photo type isn\'t supported (use jpg, png, gif or webp).', 'error')

        flash('Memory added!', 'success')
        return redirect(url_for('main.timeline'))

    return render_template('memory_form.html', memory=None, form_title='Add a Memory')


@main_bp.route('/memories/<int:memory_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_memory(memory_id):
    memory = Memory.query.get_or_404(memory_id)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        memory_date_str = request.form.get('memory_date', '')
        caption = request.form.get('caption', '').strip()

        if not title or not memory_date_str:
            flash('Title and date are required.', 'error')
            return render_template('memory_form.html', memory=memory, form_title='Edit Memory')

        try:
            memory.memory_date = _parse_memory_date(memory_date_str)
        except ValueError:
            flash('That date doesn\'t look right — please pick it from the date field.', 'error')
            return render_template('memory_form.html', memory=memory, form_title='Edit Memory')

        memory.title = title
        memory.description = description

        # Phase 5: only touch location if the form actually has a location field
        if 'location' in request.form:
            memory.location = request.form.get('location', '').strip()[:200] or None

        photo_file = request.files.get('photo')
        if photo_file and photo_file.filename:
            saved_path = save_uploaded_photo(photo_file)
            if saved_path:
                for old_photo in list(memory.photos):
                    delete_photo_file(old_photo.file_path)
                    db.session.delete(old_photo)
                db.session.add(Photo(memory_id=memory.id, file_path=saved_path, caption=caption))
            else:
                flash('That photo type isn\'t supported (use jpg, png, gif or webp) — kept the existing one.', 'error')

        db.session.commit()
        flash('Memory updated!', 'success')
        return redirect(url_for('main.timeline'))

    return render_template('memory_form.html', memory=memory, form_title='Edit Memory')


@main_bp.route('/memories/<int:memory_id>/delete', methods=['POST'])
@login_required
def delete_memory(memory_id):
    memory = Memory.query.get_or_404(memory_id)

    for photo in memory.photos:
        delete_photo_file(photo.file_path)

    db.session.delete(memory)
    db.session.commit()

    flash('Memory deleted.', 'success')
    return redirect(url_for('main.timeline'))


@main_bp.route('/gallery')
@login_required
def gallery():
    photos = Photo.query.order_by(Photo.uploaded_at.desc()).all()
    return render_template('gallery.html', photos=photos)


@main_bp.route('/search')
@login_required
def search():
    # --- what the user typed / picked (all optional) ---
    query = request.args.get('q', '').strip()
    location = request.args.get('location', '').strip()
    year = request.args.get('year', '').strip()
    author = request.args.get('author', '').strip()

    # --- data for the dropdowns ---
    users = User.query.order_by(User.name).all()
    year_rows = db.session.query(db.func.strftime('%Y', Memory.memory_date)).distinct().all()
    years = sorted({row[0] for row in year_rows if row[0]}, reverse=True)

    filters_used = any([query, location, year, author])
    results = []

    if filters_used:
        memories = Memory.query

        if query:                                   # same keyword search as before
            pattern = f'%{query}%'
            memories = memories.filter(
                db.or_(Memory.title.ilike(pattern), Memory.description.ilike(pattern))
            )
        if location:
            memories = memories.filter(Memory.location.ilike(f'%{location}%'))
        if year.isdigit() and len(year) == 4:
            memories = memories.filter(db.func.strftime('%Y', Memory.memory_date) == year)
        if author.isdigit():                        # memories are shared, so filtering by person is safe
            memories = memories.filter(Memory.created_by == int(author))

        results = memories.order_by(Memory.memory_date.desc()).all()

    return render_template(
        'search.html',
        query=query, location=location, year=year, author=author,
        users=users, years=years,
        filters_used=filters_used, results=results,
    )