from flask import Blueprint

surprises_bp = Blueprint('surprises', __name__)

from app.surprises import routes