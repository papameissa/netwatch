import threading, socket, time
from datetime import datetime

LATENCE_SEUIL = 200  # ms


def ping_host(ip, timeout=2):
    try:
        from ping3 import ping
        lat = ping(ip, timeout=timeout, unit='ms')
        if lat is not None and lat is not False:
            return True, round(float(lat), 2)
    except Exception:
        pass
    try:
        import subprocess, platform
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        start = time.time()
        r = subprocess.run(['ping', param, '1', '-W', str(timeout), ip],
                           capture_output=True, timeout=timeout+1)
        if r.returncode == 0:
            return True, round((time.time()-start)*1000, 2)
    except Exception:
        pass
    for port in [80, 443, 22, 53, 8080, 3306, 5432, 21, 25]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            start = time.time()
            if s.connect_ex((ip, port)) == 0:
                elapsed = round((time.time()-start)*1000, 2)
                s.close()
                return True, elapsed
            s.close()
        except Exception:
            pass
    return False, None


def scan_ports(ip, ports, timeout=0.8):
    open_ports = []
    for port in ports:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            if s.connect_ex((ip, port)) == 0:
                open_ports.append(port)
            s.close()
        except Exception:
            pass
    return open_ports


def _creer_alerte(db, eq, type_alerte, severite, message):
    from app.models import Alerte
    a = Alerte(equipement_id=eq.id, type_alerte=type_alerte,
               severite=severite, message=message)
    db.session.add(a)
    return a


def _check(app, eq_id, socketio):
    from app.models import Equipement, PingHistory
    from app.notifications import notifier
    from app import db

    with app.app_context():
        eq = Equipement.query.get(eq_id)
        if not eq or not eq.actif:
            return

        ancien       = eq.dernier_statut
        is_up, latence = ping_host(eq.ip_address)
        ports_ouverts  = scan_ports(eq.ip_address, eq.ports_list) if is_up and eq.ports_list else []
        nouveau        = 'up' if is_up else 'down'

        db.session.add(PingHistory(
            equipement_id=eq.id, statut=nouveau, latence=latence,
            ports_ouverts=','.join(map(str, ports_ouverts)),
        ))
        eq.dernier_statut   = nouveau
        eq.derniere_verif   = datetime.utcnow()
        eq.derniere_latence = latence

        # ── Alertes + Notifications ───────────────────────
        if ancien != 'down' and nouveau == 'down':
            msg = f'{eq.nom} ({eq.ip_address}) est HORS LIGNE'
            _creer_alerte(db, eq, 'down', 'critical', msg)
            socketio.emit('equipement_down', {'id': eq.id, 'nom': eq.nom, 'ip': eq.ip_address})
            notifier('down', eq.nom, eq.ip_address, msg)

        elif ancien == 'down' and nouveau == 'up':
            msg = f'{eq.nom} ({eq.ip_address}) est de nouveau EN LIGNE — {latence}ms'
            _creer_alerte(db, eq, 'up', 'info', msg)
            socketio.emit('equipement_up', {'id': eq.id, 'nom': eq.nom,
                                            'ip': eq.ip_address, 'latence': latence})
            notifier('up', eq.nom, eq.ip_address, msg, latence)

        elif nouveau == 'up' and latence and latence > LATENCE_SEUIL:
            msg = f'{eq.nom} ({eq.ip_address}) — latence élevée : {latence}ms'
            _creer_alerte(db, eq, 'latence', 'warning', msg)
            notifier('latence', eq.nom, eq.ip_address, msg, latence)

        db.session.commit()

        total_nl = sum(e.alertes_non_lues for e in Equipement.query.all())
        socketio.emit('scan_update', {**eq.to_dict(), 'alertes_non_lues': total_nl})


class NetworkScanner:
    def __init__(self):
        self._stop = threading.Event()

    def init_app(self, app, socketio):
        self._app, self._sio = app, socketio
        threading.Thread(target=self._loop, daemon=True, name='scanner').start()
        print('🔍 Scanner NetWatch démarré')

    def _loop(self):
        last = {}
        while not self._stop.is_set():
            try:
                with self._app.app_context():
                    from app.models import Equipement
                    eqs = Equipement.query.filter_by(actif=True).all()
                now = time.time()
                for eq in eqs:
                    if now - last.get(eq.id, 0) >= eq.intervalle:
                        last[eq.id] = now
                        threading.Thread(target=_check,
                                         args=(self._app, eq.id, self._sio),
                                         daemon=True).start()
            except Exception as e:
                print(f'⚠ Scanner: {e}')
            time.sleep(10)

    def stop(self): self._stop.set()


scanner = NetworkScanner()
