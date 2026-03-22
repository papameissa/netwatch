from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
import os

db       = SQLAlchemy()
migrate  = Migrate()
socketio = SocketIO()
login    = LoginManager()
csrf     = CSRFProtect()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY']                     = os.environ.get('SECRET_KEY', 'dev')
    app.config['SQLALCHEMY_DATABASE_URI']        = os.environ.get('DATABASE_URL', 'sqlite:///netwatch.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    socketio.init_app(app,
        message_queue=os.environ.get('REDIS_URL'),
        cors_allowed_origins='*',
        async_mode='eventlet')

    login.init_app(app)
    login.login_view    = 'auth.login'
    login.login_message = 'Connectez-vous pour accéder.'

    from app.routes.auth      import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.reseau    import reseau_bp
    from app.routes.alertes   import alertes_bp
    from app.routes.admin     import admin_bp

    app.register_blueprint(auth_bp,      url_prefix='/auth')
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(reseau_bp,    url_prefix='/reseau')
    app.register_blueprint(alertes_bp,   url_prefix='/alertes')
    app.register_blueprint(admin_bp,     url_prefix='/admin')

    with app.app_context():
        db.create_all()
        _seed()

    from app.scanner import scanner
    scanner.init_app(app, socketio)
    return app


def _seed():
    from app.models import User
    if not User.query.filter_by(username='admin').first():
        u = User(username='admin', role='admin')
        u.set_password('Admin@2024!')
        db.session.add(u)
        db.session.commit()
        print('✅ Admin → admin / Admin@2024!')


from app import login as lm
from app.models import User as _User

@lm.user_loader
def load_user(uid):
    return _User.query.get(int(uid))
