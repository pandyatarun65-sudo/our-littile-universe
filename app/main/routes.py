from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user

from app import db
from app.models import Memory, Photo
from app.utils import save_uploaded_photo, delete_photo_file

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def dashboard():
    recent_memories = Memory.query.order_by(Memory.memory_date.desc()).limit(3).all()
    return render_template('dashboard.html', memories=recent_memories)


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

        if not title or not memory_date_str:
            flash('Title and date are required.')
            return render_template('memory_form.html', memory=None, form_title='Add a Memory')

        try:
            memory_date = _parse_memory_date(memory_date_str)
        except ValueError:
            flash('That date doesn\'t look right — please pick it from the date field.')
            return render_template('memory_form.html', memory=None, form_title='Add a Memory')

        memory = Memory(
            title=title,
            description=description,
            memory_date=memory_date,
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
                flash('Memory saved, but that photo type isn\'t supported (use jpg, png, gif or webp).')

        flash('Memory added!')
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
            flash('Title and date are required.')
            return render_template('memory_form.html', memory=memory, form_title='Edit Memory')

        try:
            memory.memory_date = _parse_memory_date(memory_date_str)
        except ValueError:
            flash('That date doesn\'t look right — please pick it from the date field.')
            return render_template('memory_form.html', memory=memory, form_title='Edit Memory')

        memory.title = title
        memory.description = description

        photo_file = request.files.get('photo')
        if photo_file and photo_file.filename:
            saved_path = save_uploaded_photo(photo_file)
            if saved_path:
                for old_photo in list(memory.photos):
                    delete_photo_file(old_photo.file_path)
                    db.session.delete(old_photo)
                db.session.add(Photo(memory_id=memory.id, file_path=saved_path, caption=caption))
            else:
                flash('That photo type isn\'t supported (use jpg, png, gif or webp) — kept the existing one.')

        db.session.commit()
        flash('Memory updated!')
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

    flash('Memory deleted.')
    return redirect(url_for('main.timeline'))


@main_bp.route('/gallery')
@login_required
def gallery():
    photos = Photo.query.order_by(Photo.uploaded_at.desc()).all()
    return render_template('gallery.html', photos=photos)


@main_bp.route('/search')
@login_required
def search():
    query = request.args.get('q', '').strip()
    results = []

    if query:
        pattern = f'%{query}%'
        results = (
            Memory.query.filter(
                db.or_(Memory.title.ilike(pattern), Memory.description.ilike(pattern))
            )
            .order_by(Memory.memory_date.desc())
            .all()
        )

    return render_template('search.html', query=query, results=results)