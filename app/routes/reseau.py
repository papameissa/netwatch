from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app import db, socketio
from app.models import Equipement
from app.scanner import ping_host, scan_ports

reseau_bp = Blueprint('reseau', __name__)

TYPES = ['Serveur', 'Routeur', 'Switch', 'PC', 'Firewall', 'Caméra IP', 'Imprimante', 'Autre']


@reseau_bp.route('/')
@login_required
def index():
    equipements = Equipement.query.order_by(Equipement.nom).all()
    return render_template('reseau/index.html', equipements=equipements, types=TYPES)


@reseau_bp.route('/ajouter', methods=['GET', 'POST'])
@login_required
def ajouter():
    if request.method == 'POST':
        ip = request.form['ip_address'].strip()
        if Equipement.query.filter_by(ip_address=ip).first():
            flash(f'L\'IP {ip} est déjà enregistrée.', 'error')
            return render_template('reseau/ajouter.html', types=TYPES)
        eq = Equipement(
            nom=request.form['nom'].strip(),
            ip_address=ip,
            type_equipement=request.form.get('type_equipement', 'Autre'),
            description=request.form.get('description', '').strip(),
            ports_surveilles=request.form.get('ports_surveilles', '').strip(),
            intervalle=int(request.form.get('intervalle', 30)),
        )
        db.session.add(eq)
        db.session.commit()
        flash(f'Équipement "{eq.nom}" ajouté !', 'success')
        return redirect(url_for('reseau.index'))
    return render_template('reseau/ajouter.html', types=TYPES)


@reseau_bp.route('/modifier/<int:id>', methods=['GET', 'POST'])
@login_required
def modifier(id):
    eq = Equipement.query.get_or_404(id)
    if request.method == 'POST':
        eq.nom              = request.form['nom'].strip()
        eq.type_equipement  = request.form.get('type_equipement', 'Autre')
        eq.description      = request.form.get('description', '').strip()
        eq.ports_surveilles = request.form.get('ports_surveilles', '').strip()
        eq.intervalle       = int(request.form.get('intervalle', 30))
        db.session.commit()
        flash(f'Équipement "{eq.nom}" mis à jour !', 'success')
        return redirect(url_for('reseau.index'))
    return render_template('reseau/modifier.html', eq=eq, types=TYPES)


@reseau_bp.route('/supprimer/<int:id>', methods=['POST'])
@login_required
def supprimer(id):
    eq = Equipement.query.get_or_404(id)
    nom = eq.nom
    db.session.delete(eq)
    db.session.commit()
    flash(f'Équipement "{nom}" supprimé.', 'warning')
    return redirect(url_for('reseau.index'))


@reseau_bp.route('/ping/<int:id>', methods=['POST'])
@login_required
def ping_now(id):
    eq = Equipement.query.get_or_404(id)
    is_up, latence = ping_host(eq.ip_address)
    ports_ouverts  = scan_ports(eq.ip_address, eq.ports_list) if is_up and eq.ports_list else []
    from datetime import datetime
    from app.models import PingHistory
    nouveau = 'up' if is_up else 'down'
    db.session.add(PingHistory(
        equipement_id=eq.id, statut=nouveau, latence=latence,
        ports_ouverts=','.join(map(str, ports_ouverts)),
    ))
    eq.dernier_statut   = nouveau
    eq.derniere_verif   = datetime.utcnow()
    eq.derniere_latence = latence
    db.session.commit()
    socketio.emit('scan_update', eq.to_dict())
    return jsonify(eq.to_dict())


@reseau_bp.route('/detail/<int:id>')
@login_required
def detail(id):
    eq = Equipement.query.get_or_404(id)
    historique = eq.historique.limit(100).all()
    return render_template('reseau/detail.html', eq=eq, historique=historique)


@reseau_bp.route('/api/status')
@login_required
def api_status():
    return jsonify([e.to_dict() for e in Equipement.query.all()])


@reseau_bp.route('/api/history/<int:id>')
@login_required
def api_history(id):
    eq = Equipement.query.get_or_404(id)
    data = [{'timestamp': h.timestamp.strftime('%H:%M:%S'),
             'statut': h.statut, 'latence': h.latence}
            for h in eq.historique.limit(50).all()]
    return jsonify(data)
