from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from datetime import datetime
from app import db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        u = User.query.filter_by(username=request.form['username']).first()
        if u and u.actif and u.check_password(request.form['password']):
            login_user(u, remember='remember' in request.form)
            u.last_login = datetime.utcnow()
            db.session.commit()
            return redirect(url_for('dashboard.index'))
        flash('Identifiants incorrects.', 'error')
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth_bp.route('/user_loader/<int:id>')
def user_loader_view(id):
    pass


from app import login as login_manager
from app.models import User as UserModel

@login_manager.user_loader
def load_user(user_id):
    return UserModel.query.get(int(user_id))
