from flask import Blueprint, render_template
from flask_login import login_required
from app.models import Equipement, Alerte

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    total    = Equipement.query.count()
    up       = Equipement.query.filter_by(dernier_statut='up').count()
    down     = Equipement.query.filter_by(dernier_statut='down').count()
    inconnu  = Equipement.query.filter_by(dernier_statut='inconnu').count()
    recents  = Equipement.query.order_by(Equipement.derniere_verif.desc()).limit(6).all()
    alertes_recentes = Alerte.query.order_by(Alerte.timestamp.desc()).limit(8).all()
    non_lues = Alerte.query.filter_by(lue=False).count()
    return render_template('dashboard/index.html',
        total=total, up=up, down=down, inconnu=inconnu,
        recents=recents, alertes_recentes=alertes_recentes, non_lues=non_lues)
