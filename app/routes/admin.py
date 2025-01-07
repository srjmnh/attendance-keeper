from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.services.db_service import DatabaseService
from functools import wraps

bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    return render_template('admin/dashboard.html')

@bp.route('/admin/users')
@login_required
@admin_required
def manage_users():
    db = DatabaseService()
    users = db.get_all_users()
    return render_template('admin/users.html', users=users) 