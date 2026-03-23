"""
notifications.py — Service de notifications NetWatch
Canaux : Email (SMTP/Gmail) + SMS (Twilio) + WhatsApp (Twilio)
"""
import os
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


# ── Config depuis variables d'environnement ───────────────────
def _cfg(key, default=''):
    return os.environ.get(key, default)


def _email_html(titre, message, couleur, ip, nom, type_alerte):
    """Génère un email HTML professionnel."""
    emoji = {'down': '🔴', 'up': '🟢', 'latence': '🟡'}.get(type_alerte, '⚠️')
    now   = datetime.now().strftime('%d/%m/%Y à %H:%M:%S')
    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,sans-serif">
  <div style="max-width:580px;margin:30px auto;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.1)">
    <!-- Header -->
    <div style="background:#070b14;padding:28px 32px;text-align:center">
      <div style="font-size:32px;margin-bottom:8px">{emoji}</div>
      <h1 style="color:#00d4ff;font-size:20px;margin:0;letter-spacing:1px">NETWATCH</h1>
      <p style="color:#475569;font-size:12px;margin:4px 0 0">Surveillance Réseau — Alerte Automatique</p>
    </div>
    <!-- Body -->
    <div style="padding:32px">
      <div style="background:{couleur}15;border-left:4px solid {couleur};border-radius:8px;padding:16px 20px;margin-bottom:24px">
        <h2 style="color:{couleur};margin:0 0 6px;font-size:16px">{titre}</h2>
        <p style="color:#374151;margin:0;font-size:14px">{message}</p>
      </div>
      <table style="width:100%;border-collapse:collapse;font-size:13px">
        <tr style="background:#f9fafb">
          <td style="padding:10px 14px;color:#6b7280;font-weight:600;border-bottom:1px solid #e5e7eb">Équipement</td>
          <td style="padding:10px 14px;color:#111827;border-bottom:1px solid #e5e7eb"><b>{nom}</b></td>
        </tr>
        <tr>
          <td style="padding:10px 14px;color:#6b7280;font-weight:600;border-bottom:1px solid #e5e7eb">Adresse IP</td>
          <td style="padding:10px 14px;color:#111827;font-family:monospace;border-bottom:1px solid #e5e7eb">{ip}</td>
        </tr>
        <tr style="background:#f9fafb">
          <td style="padding:10px 14px;color:#6b7280;font-weight:600">Heure</td>
          <td style="padding:10px 14px;color:#111827">{now}</td>
        </tr>
      </table>
    </div>
    <!-- Footer -->
    <div style="background:#f9fafb;padding:16px 32px;text-align:center;border-top:1px solid #e5e7eb">
      <p style="color:#9ca3af;font-size:11px;margin:0">
        NetWatch · ISI Keur Massar · L3 RI DEVNET<br>
        Ceci est un message automatique — Ne pas répondre
      </p>
    </div>
  </div>
</body>
</html>"""


def envoyer_email(sujet, message, type_alerte, nom_eq, ip_eq):
    """Envoie un email via SMTP (Gmail ou autre)."""
    smtp_host  = _cfg('SMTP_HOST', 'smtp.gmail.com')
    smtp_port  = int(_cfg('SMTP_PORT', '587'))
    smtp_user  = _cfg('SMTP_USER')
    smtp_pass  = _cfg('SMTP_PASS')
    dest       = _cfg('NOTIF_EMAIL')

    if not all([smtp_user, smtp_pass, dest]):
        print('⚠ Email non configuré (SMTP_USER, SMTP_PASS, NOTIF_EMAIL manquants)')
        return False

    couleurs = {'down': '#ef4444', 'up': '#10b981', 'latence': '#f59e0b'}
    couleur  = couleurs.get(type_alerte, '#6b7280')
    titres   = {'down': '🔴 Panne détectée', 'up': '🟢 Équipement rétabli', 'latence': '🟡 Latence élevée'}
    titre    = titres.get(type_alerte, '⚠️ Alerte réseau')

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"[NetWatch] {titre} — {nom_eq} ({ip_eq})"
        msg['From']    = f"NetWatch <{smtp_user}>"
        msg['To']      = dest

        # Version texte (fallback)
        texte = f"{titre}\n\nÉquipement : {nom_eq}\nIP : {ip_eq}\nMessage : {message}\nHeure : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        msg.attach(MIMEText(texte, 'plain'))

        # Version HTML
        html = _email_html(titre, message, couleur, ip_eq, nom_eq, type_alerte)
        msg.attach(MIMEText(html, 'html'))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, dest, msg.as_string())

        print(f'📧 Email envoyé → {dest} ({titre})')
        return True
    except Exception as e:
        print(f'❌ Erreur email : {e}')
        return False


def envoyer_sms(message_texte):
    """Envoie un SMS via Twilio."""
    account_sid = _cfg('TWILIO_ACCOUNT_SID')
    auth_token  = _cfg('TWILIO_AUTH_TOKEN')
    from_number = _cfg('TWILIO_FROM_NUMBER')   # Ex: +14155552671
    to_number   = _cfg('TWILIO_TO_NUMBER')     # Ex: +221771234567

    if not all([account_sid, auth_token, from_number, to_number]):
        print('⚠ SMS non configuré (TWILIO_* manquants)')
        return False

    try:
        from twilio.rest import Client
        client  = Client(account_sid, auth_token)
        message = client.messages.create(
            body=message_texte,
            from_=from_number,
            to=to_number,
        )
        print(f'📱 SMS envoyé → {to_number} (sid: {message.sid})')
        return True
    except Exception as e:
        print(f'❌ Erreur SMS : {e}')
        return False


def envoyer_whatsapp(message_texte):
    """Envoie un message WhatsApp via Twilio Sandbox."""
    account_sid = _cfg('TWILIO_ACCOUNT_SID')
    auth_token  = _cfg('TWILIO_AUTH_TOKEN')
    # Twilio WhatsApp sandbox : from = whatsapp:+14155238886
    from_wa     = _cfg('TWILIO_WA_FROM', 'whatsapp:+14155238886')
    to_wa       = _cfg('TWILIO_WA_TO')   # Ex: whatsapp:+221771234567

    if not all([account_sid, auth_token, to_wa]):
        print('⚠ WhatsApp non configuré (TWILIO_WA_TO manquant)')
        return False

    try:
        from twilio.rest import Client
        client  = Client(account_sid, auth_token)
        message = client.messages.create(
            body=message_texte,
            from_=from_wa,
            to=to_wa,
        )
        print(f'💬 WhatsApp envoyé → {to_wa} (sid: {message.sid})')
        return True
    except Exception as e:
        print(f'❌ Erreur WhatsApp : {e}')
        return False


def notifier(type_alerte, nom_eq, ip_eq, message, latence=None):
    """
    Envoie les notifications sur tous les canaux configurés.
    Appelé depuis le scanner dans un thread séparé.

    type_alerte : 'down' | 'up' | 'latence'
    """
    emojis = {'down': '🔴 PANNE', 'up': '🟢 RÉTABLI', 'latence': '🟡 LATENCE ÉLEVÉE'}
    emoji  = emojis.get(type_alerte, '⚠️ ALERTE')
    now    = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    # Message court pour SMS/WhatsApp
    sms_msg = f"[NetWatch] {emoji}\nÉquipement : {nom_eq}\nIP : {ip_eq}\n{message}\n{now}"
    if latence:
        sms_msg += f"\nLatence : {latence}ms"

    def _run():
        envoyer_email(f"{emoji} — {nom_eq}", message, type_alerte, nom_eq, ip_eq)
        envoyer_sms(sms_msg)
        envoyer_whatsapp(sms_msg)

    # Thread séparé pour ne pas bloquer le scanner
    threading.Thread(target=_run, daemon=True, name='notif').start()
