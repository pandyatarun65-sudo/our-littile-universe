from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from app.models import SecretLetter, User
from app.surprises import surprises_bp
from app.notifications.services import notify


def get_authorized_partner():
    return User.query.filter(User.id != current_user.id).first()


@surprises_bp.route('/letters')
@login_required
def letters_index():
    received = SecretLetter.query.filter_by(
        recipient_id=current_user.id,
        category='letter'
    ).order_by(SecretLetter.created_at.desc()).all()

    sent = SecretLetter.query.filter_by(
        user_id=current_user.id,
        category='letter'
    ).order_by(SecretLetter.created_at.desc()).all()

    return render_template(
        'surprises/letters_list.html',
        received=received,
        sent=sent
    )


@surprises_bp.route('/letters/new', methods=['GET', 'POST'])
@login_required
def letter_create():
    partner = get_authorized_partner()
    if not partner:
        flash('No partner user found. Please ensure both accounts exist.', 'warning')
        return redirect(url_for('surprises.letters_index'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        body = request.form.get('body', '').strip()
        cover_hint = request.form.get('cover_hint', '').strip()
        unlock_date_raw = request.form.get('unlock_date', '').strip()

        if not title or not body:
            flash('Title and message content are required.', 'danger')
            return redirect(request.url)

        unlock_date = None
        if unlock_date_raw:
            try:
                unlock_date = datetime.strptime(unlock_date_raw, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid unlock date format.', 'danger')
                return redirect(request.url)

        new_letter = SecretLetter(
            category='letter',
            title=title,
            body=body,
            cover_hint=cover_hint or None,
            unlock_date=unlock_date,
            user_id=current_user.id,
            recipient_id=partner.id
        )

        db.session.add(new_letter)
        db.session.commit()
        notify(partner.id, 'letter', 'A new letter is waiting for you',
               f'{current_user.name} left something for you.',
               endpoint='surprises.letter_view', params={'letter_id': new_letter.id},
               actor_id=current_user.id)
        flash('Your letter has been sealed with care.', 'success')
        return redirect(url_for('surprises.letters_index'))

    return render_template(
        'surprises/letter_form.html',
        category='letter',
        partner=partner,
        letter=None
    )


@surprises_bp.route('/open-when')
@login_required
def open_when_index():
    received = SecretLetter.query.filter_by(
        recipient_id=current_user.id,
        category='open_when'
    ).order_by(SecretLetter.created_at.desc()).all()

    sent = SecretLetter.query.filter_by(
        user_id=current_user.id,
        category='open_when'
    ).order_by(SecretLetter.created_at.desc()).all()

    return render_template(
        'surprises/open_when_list.html',
        received=received,
        sent=sent
    )


@surprises_bp.route('/open-when/new', methods=['GET', 'POST'])
@login_required
def open_when_create():
    partner = get_authorized_partner()
    if not partner:
        flash('No partner user found. Please ensure both accounts exist.', 'warning')
        return redirect(url_for('surprises.open_when_index'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        body = request.form.get('body', '').strip()
        cover_hint = request.form.get('cover_hint', '').strip()
        mood_tag = request.form.get('mood_tag', 'comfort').strip()
        unlock_date_raw = request.form.get('unlock_date', '').strip()

        if not title or not body:
            flash('Prompt title and body content are required.', 'danger')
            return redirect(request.url)

        unlock_date = None
        if unlock_date_raw:
            try:
                unlock_date = datetime.strptime(unlock_date_raw, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid unlock date format.', 'danger')
                return redirect(request.url)

        clean_title = title if title.lower().startswith('open when') else f"Open when {title}"

        new_envelope = SecretLetter(
            category='open_when',
            title=clean_title,
            body=body,
            cover_hint=cover_hint or 'A little something kept safe for this moment.',
            mood_tag=mood_tag,
            unlock_date=unlock_date,
            user_id=current_user.id,
            recipient_id=partner.id
        )

        db.session.add(new_envelope)
        db.session.commit()
        notify(partner.id, 'open_when', 'A new "Open When" envelope for you',
               f'{current_user.name} left something for you.',
               endpoint='surprises.letter_view', params={'letter_id': new_envelope.id},
               actor_id=current_user.id)
        flash('"Open When" letter created successfully.', 'success')
        return redirect(url_for('surprises.open_when_index'))

    return render_template(
        'surprises/letter_form.html',
        category='open_when',
        partner=partner,
        letter=None
    )


@surprises_bp.route('/secret-box')
@login_required
def secret_box_index():
    received = SecretLetter.query.filter_by(
        recipient_id=current_user.id,
        category='secret_box'
    ).order_by(SecretLetter.created_at.desc()).all()

    sent = SecretLetter.query.filter_by(
        user_id=current_user.id,
        category='secret_box'
    ).order_by(SecretLetter.created_at.desc()).all()

    return render_template(
        'surprises/secret_box_list.html',
        received=received,
        sent=sent
    )


@surprises_bp.route('/secret-box/new', methods=['GET', 'POST'])
@login_required
def secret_box_create():
    partner = get_authorized_partner()
    if not partner:
        flash('No partner user found. Please ensure both accounts exist.', 'warning')
        return redirect(url_for('surprises.secret_box_index'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        body = request.form.get('body', '').strip()
        cover_hint = request.form.get('cover_hint', '').strip()
        box_type = request.form.get('box_type', 'gift').strip()
        unlock_date_raw = request.form.get('unlock_date', '').strip()

        if not title or not body:
            flash('Title and surprise content are required.', 'danger')
            return redirect(request.url)

        unlock_date = None
        if unlock_date_raw:
            try:
                unlock_date = datetime.strptime(unlock_date_raw, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid unlock date format.', 'danger')
                return redirect(request.url)

        new_surprise = SecretLetter(
            category='secret_box',
            title=title,
            body=body,
            cover_hint=cover_hint or 'A surprise is tucked away inside...',
            box_type=box_type,
            unlock_date=unlock_date,
            user_id=current_user.id,
            recipient_id=partner.id
        )

        db.session.add(new_surprise)
        db.session.commit()
        notify(partner.id, 'secret_box', 'A new surprise in the Secret Box',
               f'{current_user.name} left something for you.',
               endpoint='surprises.letter_view', params={'letter_id': new_surprise.id},
               actor_id=current_user.id)
        flash('Secret surprise placed safely in the box.', 'success')
        return redirect(url_for('surprises.secret_box_index'))

    return render_template(
        'surprises/letter_form.html',
        category='secret_box',
        partner=partner,
        letter=None
    )


@surprises_bp.route('/surprises', defaults={'letter_id': None})
@surprises_bp.route('/surprises/<int:letter_id>')
@login_required
def letter_view(letter_id):
    if letter_id is None:
        raw_id = request.args.get('letter_id')
        if raw_id and raw_id.isdigit():
            letter_id = int(raw_id)
        else:
            abort(404)

    letter = SecretLetter.query.get_or_404(letter_id)

    if current_user.id != letter.recipient_id and current_user.id != letter.user_id:
        abort(404)

    is_author = (current_user.id == letter.user_id)
    is_unlocked = letter.is_unlocked()

    if not is_author and not is_unlocked:
        return render_template(
            'surprises/letter_view.html',
            letter=letter,
            locked=True,
            is_author=False
        )

    return render_template(
        'surprises/letter_view.html',
        letter=letter,
        locked=False,
        is_author=is_author
    )


@surprises_bp.route('/surprises/<int:letter_id>/edit', methods=['GET', 'POST'])
@login_required
def letter_edit(letter_id):
    letter = SecretLetter.query.get_or_404(letter_id)

    if letter.user_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        body = request.form.get('body', '').strip()
        cover_hint = request.form.get('cover_hint', '').strip()
        unlock_date_raw = request.form.get('unlock_date', '').strip()

        if not title or not body:
            flash('Title and message cannot be empty.', 'danger')
            return redirect(request.url)

        unlock_date = None
        if unlock_date_raw:
            try:
                unlock_date = datetime.strptime(unlock_date_raw, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid unlock date format.', 'danger')
                return redirect(request.url)

        letter.title = title
        letter.body = body
        letter.cover_hint = cover_hint or None
        letter.unlock_date = unlock_date

        if letter.category == 'open_when':
            letter.mood_tag = request.form.get('mood_tag', letter.mood_tag)
        elif letter.category == 'secret_box':
            letter.box_type = request.form.get('box_type', letter.box_type)

        db.session.commit()
        flash('Updated successfully.', 'success')

        if letter.category == 'open_when':
            return redirect(url_for('surprises.open_when_index'))
        elif letter.category == 'secret_box':
            return redirect(url_for('surprises.secret_box_index'))
        return redirect(url_for('surprises.letters_index'))

    return render_template(
        'surprises/letter_form.html',
        category=letter.category,
        partner=letter.recipient,
        letter=letter
    )


@surprises_bp.route('/surprises/<int:letter_id>/delete', methods=['POST'])
@login_required
def letter_delete(letter_id):
    letter = SecretLetter.query.get_or_404(letter_id)

    if letter.user_id != current_user.id:
        abort(403)

    category = letter.category
    db.session.delete(letter)
    db.session.commit()
    flash('Item removed.', 'info')

    if category == 'open_when':
        return redirect(url_for('surprises.open_when_index'))
    elif category == 'secret_box':
        return redirect(url_for('surprises.secret_box_index'))
    return redirect(url_for('surprises.letters_index'))