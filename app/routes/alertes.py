from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from app import db
from app.models import Alerte

alertes_bp = Blueprint('alertes', __name__)


@alertes_bp.route('/')
@login_required
def index():
    alertes  = Alerte.query.order_by(Alerte.timestamp.desc()).limit(200).all()
    non_lues = Alerte.query.filter_by(lue=False).count()
    stats = {
        'total':    Alerte.query.count(),
        'critical': Alerte.query.filter_by(severite='critical').count(),
        'warning':  Alerte.query.filter_by(severite='warning').count(),
        'non_lues': non_lues,
    }
    return render_template('alertes/index.html', alertes=alertes, stats=stats)


@alertes_bp.route('/lire/<int:id>', methods=['POST'])
@login_required
def marquer_lue(id):
    a = Alerte.query.get_or_404(id)
    a.lue = True
    db.session.commit()
    return jsonify({'ok': True})


@alertes_bp.route('/lire-toutes', methods=['POST'])
@login_required
def lire_toutes():
    Alerte.query.filter_by(lue=False).update({'lue': True})
    db.session.commit()
    return jsonify({'ok': True})


@alertes_bp.route('/supprimer-toutes', methods=['POST'])
@login_required
def supprimer_toutes():
    Alerte.query.delete()
    db.session.commit()
    return jsonify({'ok': True})


@alertes_bp.route('/api')
@login_required
def api():
    alertes = Alerte.query.order_by(Alerte.timestamp.desc()).limit(50).all()
    return jsonify([a.to_dict() for a in alertes])
