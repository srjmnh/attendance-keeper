from flask import Blueprint, render_template

bp = Blueprint('index', __name__)

@bp.route('/')
def index():
    """Render the homepage"""
    return render_template('index.html') 