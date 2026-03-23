from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
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


@admin_bp.route('/notifications', methods=['GET', 'POST'])
@admin_required
def notifications():
    import os
    config_keys = [
        'SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASS', 'NOTIF_EMAIL',
        'TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN',
        'TWILIO_FROM_NUMBER', 'TWILIO_TO_NUMBER',
        'TWILIO_WA_FROM', 'TWILIO_WA_TO',
    ]
    if request.method == 'POST':
        # Écrire dans le fichier .env
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
        lines = []
        try:
            with open(env_path, 'r') as f:
                existing = {l.split('=')[0]: l for l in f.readlines() if '=' in l}
        except Exception:
            existing = {}
        for key in config_keys:
            val = request.form.get(key, '').strip()
            if val:
                existing[key] = f"{key}={val}\n"
                os.environ[key] = val
        try:
            with open(env_path, 'w') as f:
                for line in existing.values():
                    f.write(line)
            flash('Configuration sauvegardée !', 'success')
        except Exception as e:
            flash(f'Erreur écriture .env : {e}', 'error')
        return redirect(url_for('admin.notifications'))

    config = {k: os.environ.get(k, '') for k in config_keys}
    return render_template('admin/notifications.html', config=config)


@admin_bp.route('/notifications/test/<canal>', methods=['POST'])
@admin_required
def test_notif(canal):
    from app.notifications import envoyer_email, envoyer_sms, envoyer_whatsapp
    msg = "🧪 Test NetWatch — Si vous recevez ce message, les notifications fonctionnent !"
    if canal == 'email':
        ok = envoyer_email("Test NetWatch", msg, 'up', 'Test', '0.0.0.0')
    elif canal == 'sms':
        ok = envoyer_sms(f"[NetWatch] {msg}")
    elif canal == 'whatsapp':
        ok = envoyer_whatsapp(f"[NetWatch] {msg}")
    else:
        ok = False
    return jsonify({'ok': ok, 'canal': canal})
