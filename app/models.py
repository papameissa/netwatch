from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(20), default='operateur')
    actif         = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    last_login    = db.Column(db.DateTime, nullable=True)

    def set_password(self, p):   self.password_hash = generate_password_hash(p)
    def check_password(self, p): return check_password_hash(self.password_hash, p)

    @property
    def is_admin(self): return self.role == 'admin'


class Equipement(db.Model):
    __tablename__ = 'equipements'
    id               = db.Column(db.Integer, primary_key=True)
    nom              = db.Column(db.String(100), nullable=False)
    ip_address       = db.Column(db.String(45), nullable=False, unique=True)
    type_equipement  = db.Column(db.String(50), default='Autre')
    description      = db.Column(db.Text, nullable=True)
    ports_surveilles = db.Column(db.String(200), default='')
    intervalle       = db.Column(db.Integer, default=30)
    actif            = db.Column(db.Boolean, default=True)
    dernier_statut   = db.Column(db.String(10), default='inconnu')
    derniere_verif   = db.Column(db.DateTime, nullable=True)
    derniere_latence = db.Column(db.Float, nullable=True)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

    historique = db.relationship('PingHistory', backref='equipement',
                                 lazy='dynamic', cascade='all, delete-orphan',
                                 order_by='PingHistory.timestamp.desc()')
    alertes    = db.relationship('Alerte', backref='equipement',
                                 lazy='dynamic', cascade='all, delete-orphan',
                                 order_by='Alerte.timestamp.desc()')

    @property
    def ports_list(self):
        return [int(p.strip()) for p in self.ports_surveilles.split(',')
                if p.strip().isdigit()] if self.ports_surveilles else []

    @property
    def uptime_pct(self):
        total = self.historique.count()
        if not total: return None
        return round(self.historique.filter_by(statut='up').count() / total * 100, 1)

    @property
    def alertes_non_lues(self):
        return self.alertes.filter_by(lue=False).count()

    def to_dict(self):
        return {
            'id': self.id, 'nom': self.nom, 'ip': self.ip_address,
            'type': self.type_equipement, 'statut': self.dernier_statut,
            'latence': self.derniere_latence, 'uptime': self.uptime_pct,
            'ports': self.ports_surveilles, 'intervalle': self.intervalle,
            'derniere_verif': self.derniere_verif.strftime('%H:%M:%S') if self.derniere_verif else '—',
        }


class PingHistory(db.Model):
    __tablename__ = 'ping_history'
    id            = db.Column(db.Integer, primary_key=True)
    equipement_id = db.Column(db.Integer, db.ForeignKey('equipements.id'), nullable=False)
    timestamp     = db.Column(db.DateTime, default=datetime.utcnow)
    statut        = db.Column(db.String(10), nullable=False)
    latence       = db.Column(db.Float, nullable=True)
    ports_ouverts = db.Column(db.String(200), default='')


class Alerte(db.Model):
    """Historique des alertes : panne, rétablissement, latence élevée."""
    __tablename__ = 'alertes'
    id            = db.Column(db.Integer, primary_key=True)
    equipement_id = db.Column(db.Integer, db.ForeignKey('equipements.id'), nullable=False)
    timestamp     = db.Column(db.DateTime, default=datetime.utcnow)
    type_alerte   = db.Column(db.String(20), nullable=False)  # down | up | latence
    severite      = db.Column(db.String(10), default='warning')  # critical | warning | info
    message       = db.Column(db.String(300), nullable=False)
    lue           = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'equipement_id': self.equipement_id,
            'equipement_nom': self.equipement.nom,
            'equipement_ip':  self.equipement.ip_address,
            'timestamp': self.timestamp.strftime('%d/%m/%Y %H:%M:%S'),
            'type': self.type_alerte,
            'severite': self.severite,
            'message': self.message,
            'lue': self.lue,
        }
