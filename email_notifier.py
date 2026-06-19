import os
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sent_emails_log.txt')

SENDER_EMAIL = 'floodrisknotification@gmail.com'

PLACEHOLDER = 'YOUR_GMAIL_APP_PASSWORD_HERE'

def get_smtp_password():
    """Retrieves the SMTP password from config.json or environment variables.
    Returns None if no real password is set (including placeholder values)."""
    # Try environment variable first
    env_pwd = os.environ.get('SMTP_PASSWORD') or os.environ.get('SENDER_PASSWORD')
    if env_pwd and env_pwd.strip() and env_pwd.strip() != PLACEHOLDER:
        return env_pwd.strip()

    # Try config.json
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
                pwd = config.get('smtp_password', '').strip()
                # Reject placeholder or empty values
                if pwd and pwd != PLACEHOLDER:
                    return pwd
        except Exception as e:
            print(f"[Notifier] Error reading config.json: {e}")

    return None

def is_smtp_configured():
    """Returns True if a real Gmail App Password has been configured."""
    return get_smtp_password() is not None

def save_smtp_password(password):
    """Saves the Gmail App Password to config.json."""
    password = password.strip()
    if not password or password == PLACEHOLDER:
        return False, 'Invalid password provided.'
    try:
        config = {}
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, 'r') as f:
                    config = json.load(f)
            except Exception:
                config = {}
        config['smtp_password'] = password
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        print(f'[Notifier] Gmail App Password saved to config.json.')
        return True, 'Password saved successfully.'
    except Exception as e:
        print(f'[Notifier] Failed to save password: {e}')
        return False, str(e)

def write_to_fallback_log(to_email, subject, html_content):
    """Writes the email content to a local log file for testing/fallback purposes."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    divider = "=" * 80
    log_entry = (
        f"{divider}\n"
        f"TIMESTAMP: {timestamp}\n"
        f"TO: {to_email}\n"
        f"FROM: {SENDER_EMAIL}\n"
        f"SUBJECT: {subject}\n"
        f"STATUS: SIMULATED (No SMTP credentials or connection failed)\n"
        f"{divider}\n"
        f"{html_content}\n\n"
    )
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        print(f"[Notifier] Email logged to {os.path.basename(LOG_PATH)} for {to_email}")
        return True
    except Exception as e:
        print(f"[Notifier] Failed to write fallback log: {e}")
        return False

def send_email(to_email, subject, html_content):
    """Attempts to send an email via Gmail SMTP, falls back to local log file if unconfigured."""
    password = get_smtp_password()
    if not password:
        print("[Notifier] SMTP password not configured. Falling back to log file simulation.")
        return write_to_fallback_log(to_email, subject, html_content)

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(html_content, 'html'))

    try:
        # Connect to Gmail's SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, password)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        server.quit()
        print(f"[Notifier] Email successfully sent to {to_email} via SMTP.")
        return True
    except Exception as e:
        print(f"[Notifier] SMTP failed to send to {to_email}: {e}. Logging to file instead.")
        return write_to_fallback_log(to_email, subject, html_content)

def build_alerts_html(name, alerts, is_test=False):
    """Generates a premium HTML email for active alerts."""
    now_str = datetime.now().strftime('%d %B %Y')
    
    # Generate list items
    alert_items_html = ""
    for alert in alerts:
        severity = alert['severity']
        badge_color = '#ef4444' if severity == 'High' else '#f59e0b'
        badge_bg = 'rgba(239, 68, 68, 0.1)' if severity == 'High' else 'rgba(245, 158, 11, 0.1)'
        border_color = 'rgba(239, 68, 68, 0.3)' if severity == 'High' else 'rgba(245, 158, 11, 0.3)'
        
        alert_items_html += f"""
        <tr style="border-bottom: 1px solid #1e293b;">
            <td style="padding: 12px 8px; font-weight: 600; color: #ffffff;">{alert['name']}</td>
            <td style="padding: 12px 8px;">
                <span style="display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; text-transform: uppercase; color: {badge_color}; background-color: {badge_bg}; border: 1px solid {border_color};">
                    {severity}
                </span>
            </td>
            <td style="padding: 12px 8px; font-weight: 700; color: {badge_color};">{alert['risk']}%</td>
            <td style="padding: 12px 8px; color: #94a3b8; font-size: 13px;">
                🌧️ {alert['weather']['rainfall_24h']} mm<br/>
                🏞️ {alert['weather']['river_level']} m
            </td>
        </tr>
        """
        
    test_notice = ""
    if is_test:
        test_notice = """
        <div style="background-color: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 8px; padding: 12px; margin-bottom: 20px; color: #3b82f6; font-size: 13px;">
            🧪 <strong>Test Email Successful:</strong> This is a test email sent from the FloodWatch MH system to verify your settings.
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Maharashtra Flood Risk Alert</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #080e1a; color: #e2e8f0;">
        <table align="center" border="0" cellpadding="0" cellspacing="0" width="600" style="border-collapse: collapse; margin: 30px auto; background-color: #0f172a; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; overflow: hidden; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);">
            <!-- Header -->
            <tr>
                <td align="center" style="padding: 30px 20px; background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%); border-bottom: 1px solid rgba(255, 255, 255, 0.08);">
                    <span style="font-size: 40px; line-height: 1;">🌊</span>
                    <h1 style="margin: 10px 0 0 0; font-size: 24px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px;">
                        Flood<span style="color: #3b82f6;">Watch</span> MH
                    </h1>
                    <p style="margin: 5px 0 0 0; font-size: 14px; color: #94a3b8;">Daily Morning Risk Intelligence Summary</p>
                </td>
            </tr>
            <!-- Content -->
            <tr>
                <td style="padding: 30px 24px;">
                    {test_notice}
                    <p style="font-size: 16px; margin-top: 0;">Hello <strong>{name}</strong>,</p>
                    <p style="font-size: 14px; line-height: 1.5; color: #94a3b8;">
                        Here is the live flood risk notification for <strong>{now_str}</strong>. Our system has detected active 
                        <strong style="color: #ef4444;">High (Red)</strong> or <strong style="color: #f59e0b;">Moderate (Orange)</strong> alert conditions in the following Maharashtra districts:
                    </p>
                    
                    <table width="100%" cellpadding="0" cellspacing="0" style="margin: 20px 0; text-align: left; border-collapse: collapse;">
                        <thead>
                            <tr style="border-bottom: 2px solid #3b82f6;">
                                <th style="padding: 10px 8px; color: #94a3b8; font-size: 12px; text-transform: uppercase;">District</th>
                                <th style="padding: 10px 8px; color: #94a3b8; font-size: 12px; text-transform: uppercase;">Alert Level</th>
                                <th style="padding: 10px 8px; color: #94a3b8; font-size: 12px; text-transform: uppercase;">Risk Score</th>
                                <th style="padding: 10px 8px; color: #94a3b8; font-size: 12px; text-transform: uppercase;">Weather</th>
                            </tr>
                        </thead>
                        <tbody>
                            {alert_items_html}
                        </tbody>
                    </table>
                    
                    <p style="font-size: 14px; line-height: 1.5; color: #94a3b8; margin-top: 25px;">
                        Please monitor low-lying areas, keep emergency helplines ready, and follow advice from local authorities.
                    </p>
                    
                    <!-- Call to Action -->
                    <table align="center" border="0" cellpadding="0" cellspacing="0" style="margin: 30px auto 10px;">
                        <tr>
                            <td align="center" style="background-color: #3b82f6; border-radius: 8px;">
                                <a href="http://localhost:5000/" target="_blank" style="display: inline-block; padding: 12px 24px; color: #ffffff; text-decoration: none; font-size: 14px; font-weight: 700; border-radius: 8px; box-shadow: 0 4px 10px rgba(59, 130, 246, 0.45);">
                                    🗺️ View Live Risk Map
                                </a>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
            <!-- Footer -->
            <tr>
                <td style="padding: 24px; background-color: #0b0f19; border-top: 1px solid rgba(255, 255, 255, 0.05); text-align: center; font-size: 12px; color: #64748b;">
                    <p style="margin: 0 0 10px 0;">You received this alert because you are signed up for morning notifications on FloodWatch MH.</p>
                    <p style="margin: 0;">
                        To change your preferences or unsubscribe, please <a href="http://localhost:5000/alerts" target="_blank" style="color: #3b82f6; text-decoration: none;">manage notifications here</a>.
                    </p>
                    <p style="margin: 15px 0 0 0; opacity: 0.5;">© 2026 FloodWatch MH. All rights reserved.</p>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

def build_no_alerts_html(name, is_test=False):
    """Generates an HTML email for when all districts are Low Risk (Stable conditions)."""
    now_str = datetime.now().strftime('%d %B %Y')
    
    test_notice = ""
    if is_test:
        test_notice = """
        <div style="background-color: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 8px; padding: 12px; margin-bottom: 20px; color: #3b82f6; font-size: 13px;">
            🧪 <strong>Test Email Successful:</strong> This is a test email sent from the FloodWatch MH system to verify your settings.
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Maharashtra Flood Risk Alert - Stable</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #080e1a; color: #e2e8f0;">
        <table align="center" border="0" cellpadding="0" cellspacing="0" width="600" style="border-collapse: collapse; margin: 30px auto; background-color: #0f172a; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; overflow: hidden; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);">
            <!-- Header -->
            <tr>
                <td align="center" style="padding: 30px 20px; background: linear-gradient(135deg, #065f46 0%, #0f172a 100%); border-bottom: 1px solid rgba(255, 255, 255, 0.08);">
                    <span style="font-size: 40px; line-height: 1;">💚</span>
                    <h1 style="margin: 10px 0 0 0; font-size: 24px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px;">
                        Flood<span style="color: #10b981;">Watch</span> MH
                    </h1>
                    <p style="margin: 5px 0 0 0; font-size: 14px; color: #94a3b8;">Daily Morning Risk Intelligence Summary</p>
                </td>
            </tr>
            <!-- Content -->
            <tr>
                <td style="padding: 30px 24px;">
                    {test_notice}
                    <p style="font-size: 16px; margin-top: 0;">Hello <strong>{name}</strong>,</p>
                    <p style="font-size: 14px; line-height: 1.5; color: #94a3b8;">
                        Here is your live flood risk summary for <strong>{now_str}</strong>.
                    </p>
                    
                    <div style="background-color: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 16px; text-align: center; color: #10b981; margin: 20px 0;">
                        <span style="font-size: 24px; display: block; margin-bottom: 5px;">✅ Stable Conditions</span>
                        <strong>No Active Flood Alerts</strong>
                        <p style="font-size: 13px; margin: 5px 0 0 0; color: #94a3b8;">All 28 monitored districts in Maharashtra are currently reporting low risk (below 30%).</p>
                    </div>
                    
                    <p style="font-size: 14px; line-height: 1.5; color: #94a3b8; margin-top: 25px;">
                        No special actions are required at this time. Stay safe!
                    </p>
                    
                    <!-- Call to Action -->
                    <table align="center" border="0" cellpadding="0" cellspacing="0" style="margin: 30px auto 10px;">
                        <tr>
                            <td align="center" style="background-color: #10b981; border-radius: 8px;">
                                <a href="http://localhost:5000/" target="_blank" style="display: inline-block; padding: 12px 24px; color: #ffffff; text-decoration: none; font-size: 14px; font-weight: 700; border-radius: 8px; box-shadow: 0 4px 10px rgba(16, 185, 129, 0.45);">
                                    🗺️ View Live Risk Map
                                </a>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
            <!-- Footer -->
            <tr>
                <td style="padding: 24px; background-color: #0b0f19; border-top: 1px solid rgba(255, 255, 255, 0.05); text-align: center; font-size: 12px; color: #64748b;">
                    <p style="margin: 0 0 10px 0;">You received this alert because you are signed up for morning notifications on FloodWatch MH.</p>
                    <p style="margin: 0;">
                        To change your preferences or unsubscribe, please <a href="http://localhost:5000/alerts" target="_blank" style="color: #3b82f6; text-decoration: none;">manage notifications here</a>.
                    </p>
                    <p style="margin: 15px 0 0 0; opacity: 0.5;">© 2026 FloodWatch MH. All rights reserved.</p>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

def send_daily_alerts(subscribers, alerts):
    """Sends the morning alert summary to all subscribers. If alerts list is empty, nothing is sent unless specifically overridden."""
    if not subscribers:
        print("[Notifier] No subscribers to notify.")
        return 0

    if not alerts:
        print("[Notifier] No active Red/Orange alerts today. Skipping notifications.")
        return 0

    subject = f"🚨 FLOOD WATCH MH: {len(alerts)} Active Flood Alerts Detected!"
    sent_count = 0
    for sub in subscribers:
        html = build_alerts_html(sub['name'], alerts, is_test=False)
        if send_email(sub['email'], subject, html):
            sent_count += 1
            
    print(f"[Notifier] Dispatched morning alerts to {sent_count} of {len(subscribers)} subscribers.")
    return sent_count

def send_test_email(email, name, alerts=None):
    """Sends a test email immediately. Uses real active alerts if provided, otherwise sends a mock alert sample or stable notice."""
    print(f"[Notifier] Sending test alert to {name} ({email})...")
    subject = "🧪 Test Flood Alert - FloodWatch MH"
    
    if alerts:
        html = build_alerts_html(name, alerts, is_test=True)
    else:
        # If no alerts are passed, check if we want to simulate a mockup alert or show stable
        mock_alerts = [
            {
                "name": "Mumbai",
                "severity": "High",
                "risk": 78.5,
                "weather": {
                    "rainfall_24h": 125.0,
                    "river_level": 4.5,
                }
            },
            {
                "name": "Kolhapur",
                "severity": "Moderate",
                "risk": 52.3,
                "weather": {
                    "rainfall_24h": 65.0,
                    "river_level": 3.8,
                }
            }
        ]
        html = build_alerts_html(name, mock_alerts, is_test=True)
        
    return send_email(email, subject, html)
