import threading, socket, time
from datetime import datetime

LATENCE_SEUIL = 200  # ms — au-dessus = alerte latence élevée


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
    """Crée une alerte en base."""
    from app.models import Alerte
    alerte = Alerte(
        equipement_id=eq.id,
        type_alerte=type_alerte,
        severite=severite,
        message=message,
    )
    db.session.add(alerte)
    return alerte


def _check(app, eq_id, socketio):
    from app.models import Equipement, PingHistory
    from app import db
    with app.app_context():
        eq = Equipement.query.get(eq_id)
        if not eq or not eq.actif:
            return

        ancien_statut  = eq.dernier_statut
        is_up, latence = ping_host(eq.ip_address)
        ports_ouverts  = scan_ports(eq.ip_address, eq.ports_list) if is_up and eq.ports_list else []
        nouveau_statut = 'up' if is_up else 'down'

        # Historique
        db.session.add(PingHistory(
            equipement_id=eq.id, statut=nouveau_statut, latence=latence,
            ports_ouverts=','.join(map(str, ports_ouverts)),
        ))

        eq.dernier_statut   = nouveau_statut
        eq.derniere_verif   = datetime.utcnow()
        eq.derniere_latence = latence

        # ── Alertes ──────────────────────────────────────────
        alerte_data = None

        if ancien_statut != 'down' and nouveau_statut == 'down':
            # Panne détectée
            _creer_alerte(db, eq, 'down', 'critical',
                          f'{eq.nom} ({eq.ip_address}) est HORS LIGNE')
            alerte_data = {'type': 'down', 'severite': 'critical',
                           'nom': eq.nom, 'ip': eq.ip_address, 'id': eq.id}
            socketio.emit('equipement_down', alerte_data)

        elif ancien_statut == 'down' and nouveau_statut == 'up':
            # Rétablissement
            _creer_alerte(db, eq, 'up', 'info',
                          f'{eq.nom} ({eq.ip_address}) est de nouveau EN LIGNE — {latence}ms')
            alerte_data = {'type': 'up', 'severite': 'info',
                           'nom': eq.nom, 'ip': eq.ip_address, 'id': eq.id, 'latence': latence}
            socketio.emit('equipement_up', alerte_data)

        elif nouveau_statut == 'up' and latence and latence > LATENCE_SEUIL:
            # Latence élevée
            _creer_alerte(db, eq, 'latence', 'warning',
                          f'{eq.nom} ({eq.ip_address}) — latence élevée : {latence}ms')

        db.session.commit()

        # Mettre à jour le compteur d'alertes non lues
        total_non_lues = sum(
            e.alertes_non_lues for e in Equipement.query.all()
        )
        socketio.emit('scan_update', {**eq.to_dict(), 'alertes_non_lues': total_non_lues})


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
