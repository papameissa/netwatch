from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models import User

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            return render_template('auth/403.html'), 403
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/')
@admin_required
def index():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/index.html', users=users)


@admin_bp.route('/users/creer', methods=['GET', 'POST'])
@admin_required
def creer_user():
    if request.method == 'POST':
        username = request.form['username'].strip()
        if User.query.filter_by(username=username).first():
            flash('Ce nom d\'utilisateur existe déjà.', 'error')
        else:
            u = User(username=username, role=request.form.get('role', 'operateur'))
            u.set_password(request.form['password'])
            db.session.add(u)
            db.session.commit()
            flash(f'Utilisateur "{username}" créé.', 'success')
            return redirect(url_for('admin.index'))
    return render_template('admin/creer_user.html')


@admin_bp.route('/users/toggle/<int:id>', methods=['POST'])
@admin_required
def toggle_user(id):
    u = User.query.get_or_404(id)
    if u.id != current_user.id:
        u.actif = not u.actif
        db.session.commit()
        flash(f'Utilisateur {"activé" if u.actif else "désactivé"}.', 'success')
    return redirect(url_for('admin.index'))


@admin_bp.route('/users/role/<int:id>', methods=['POST'])
@admin_required
def change_role(id):
    u = User.query.get_or_404(id)
    if u.id != current_user.id:
        u.role = 'admin' if u.role == 'operateur' else 'operateur'
        db.session.commit()
        flash(f'Rôle de {u.username} changé en {u.role}.', 'success')
    return redirect(url_for('admin.index'))
