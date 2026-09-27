from flask import Blueprint, render_template
from flask_login import login_required
from app.models import Memory

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def dashboard():
    # Show the 3 most recent memories on the dashboard.
    recent_memories = Memory.query.order_by(Memory.memory_date.desc()).limit(3).all()
    return render_template('dashboard.html', memories=recent_memories)


@main_bp.route('/timeline')
@login_required
def timeline():
    # Show every memory, newest first.
    all_memories = Memory.query.order_by(Memory.memory_date.desc()).all()
    return render_template('timeline.html', memories=all_memories)
