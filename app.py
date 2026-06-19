import requests, json
from flask import Flask, request, jsonify, render_template, session
import joblib, os, random, threading, time
import pandas as pd
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY') or 'floodwatch_mh_secret_key_12345!'

import database
database.init_db()
MODEL_PATH = 'model.pkl'

def get_model():
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return None

# ── Cache the Maharashtra GeoJSON at startup ──────────────────────────────────
_maharashtra_geojson = None

def load_maharashtra_boundary():
    global _maharashtra_geojson
    if _maharashtra_geojson:
        return _maharashtra_geojson
    try:
        url = "https://raw.githubusercontent.com/geohacker/india/master/state/india_state.geojson"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            all_data = r.json()
            mh_feature = next(
                (f for f in all_data['features']
                 if f['properties'].get('NAME_1') == 'Maharashtra'),
                None
            )
            if mh_feature:
                _maharashtra_geojson = {
                    "type": "FeatureCollection",
                    "features": [mh_feature]
                }
                print("[OK] Maharashtra boundary loaded & cached.")
                return _maharashtra_geojson
    except Exception as e:
        print(f"[WARN] Could not fetch Maharashtra boundary: {e}")
    return None

# Pre-load at startup
load_maharashtra_boundary()
CITY_META = {
    "Mumbai":     {"lat": 19.0760, "lng": 72.8777, "baseline_river": 1.8, "coeff_river": 0.038, "vulnerability": 0.85},
    "Thane":      {"lat": 19.2183, "lng": 72.9781, "baseline_river": 1.9, "coeff_river": 0.036, "vulnerability": 0.80},
    "Raigad":     {"lat": 18.5158, "lng": 73.1180, "baseline_river": 2.0, "coeff_river": 0.040, "vulnerability": 0.82},
    "Ratnagiri":  {"lat": 16.9902, "lng": 73.3120, "baseline_river": 2.1, "coeff_river": 0.042, "vulnerability": 0.88},
    "Sindhudurg": {"lat": 16.3500, "lng": 73.9500, "baseline_river": 1.9, "coeff_river": 0.038, "vulnerability": 0.80},
    "Chiplun":    {"lat": 17.5323, "lng": 73.5174, "baseline_river": 2.1, "coeff_river": 0.040, "vulnerability": 0.85},
    "Pune":       {"lat": 18.5204, "lng": 73.8567, "baseline_river": 2.0, "coeff_river": 0.025, "vulnerability": 0.50},
    "Kolhapur":   {"lat": 16.7050, "lng": 74.2433, "baseline_river": 2.2, "coeff_river": 0.030, "vulnerability": 0.68},
    "Satara":     {"lat": 17.6805, "lng": 74.0183, "baseline_river": 2.0, "coeff_river": 0.028, "vulnerability": 0.55},
    "Sangli":     {"lat": 16.8524, "lng": 74.5815, "baseline_river": 2.3, "coeff_river": 0.032, "vulnerability": 0.65},
    "Solapur":    {"lat": 17.6869, "lng": 75.9064, "baseline_river": 1.5, "coeff_river": 0.018, "vulnerability": 0.20},
    "Aurangabad": {"lat": 19.8762, "lng": 75.3433, "baseline_river": 1.4, "coeff_river": 0.020, "vulnerability": 0.25},
    "Latur":      {"lat": 18.4088, "lng": 76.5604, "baseline_river": 1.3, "coeff_river": 0.018, "vulnerability": 0.15},
    "Nanded":     {"lat": 19.1383, "lng": 77.3210, "baseline_river": 1.5, "coeff_river": 0.022, "vulnerability": 0.35},
    "Osmanabad":  {"lat": 18.1860, "lng": 76.0388, "baseline_river": 1.4, "coeff_river": 0.019, "vulnerability": 0.18},
    "Beed":       {"lat": 18.9890, "lng": 75.7576, "baseline_river": 1.3, "coeff_river": 0.017, "vulnerability": 0.16},
    "Parbhani":   {"lat": 19.2604, "lng": 76.7748, "baseline_river": 1.5, "coeff_river": 0.020, "vulnerability": 0.28},
    "Nagpur":     {"lat": 21.1458, "lng": 79.0882, "baseline_river": 1.7, "coeff_river": 0.025, "vulnerability": 0.35},
    "Amravati":   {"lat": 20.9320, "lng": 77.7523, "baseline_river": 1.6, "coeff_river": 0.023, "vulnerability": 0.30},
    "Akola":      {"lat": 20.7062, "lng": 77.0078, "baseline_river": 1.5, "coeff_river": 0.022, "vulnerability": 0.28},
    "Buldhana":   {"lat": 20.5292, "lng": 76.1842, "baseline_river": 1.4, "coeff_river": 0.021, "vulnerability": 0.25},
    "Chandrapur": {"lat": 19.9615, "lng": 79.2961, "baseline_river": 2.0, "coeff_river": 0.030, "vulnerability": 0.45},
    "Gadchiroli": {"lat": 20.1809, "lng": 80.0000, "baseline_river": 2.2, "coeff_river": 0.033, "vulnerability": 0.52},
    "Yavatmal":   {"lat": 20.3888, "lng": 78.1204, "baseline_river": 1.6, "coeff_river": 0.022, "vulnerability": 0.30},
    "Nashik":     {"lat": 19.9975, "lng": 73.7898, "baseline_river": 1.8, "coeff_river": 0.028, "vulnerability": 0.48},
    "Dhule":      {"lat": 20.9042, "lng": 74.7749, "baseline_river": 1.5, "coeff_river": 0.020, "vulnerability": 0.22},
    "Nandurbar":  {"lat": 21.3700, "lng": 74.2400, "baseline_river": 1.7, "coeff_river": 0.028, "vulnerability": 0.32},
    "Jalgaon":    {"lat": 21.0077, "lng": 75.5626, "baseline_river": 1.6, "coeff_river": 0.022, "vulnerability": 0.28},
    "Ahmednagar": {"lat": 19.0948, "lng": 74.7480, "baseline_river": 1.5, "coeff_river": 0.020, "vulnerability": 0.24},
}

# ─────────────────────────────────────────────────────────────────────────────
@app.route('/')
def home():
    return render_template('index.html')

# Serve the cached Maharashtra GeoJSON directly
@app.route('/api/maharashtra_boundary')
def maharashtra_boundary():
    data = load_maharashtra_boundary()
    if data:
        return jsonify(data)
    # Fallback: empty feature collection so client can still handle gracefully
    return jsonify({"type": "FeatureCollection", "features": []})

# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/predict', methods=['POST'])
def predict():
    model = get_model()
    if model is None:
        return jsonify({'error': 'Model not trained yet. Run train.py first.'}), 500

    data = request.json
    try:
        rainfall      = float(data.get('rainfall'))
        river_level   = float(data.get('river_level'))
        soil_moisture = float(data.get('soil_moisture'))

        features = pd.DataFrame(
            [[rainfall, river_level, soil_moisture]],
            columns=['rainfall_mm', 'river_level_m', 'soil_moisture_pct']
        )
        prob = model.predict_proba(features)[0][1]
        risk_percentage = round(prob * 100, 2)

        if risk_percentage > 70:
            severity = "High"
        elif risk_percentage > 30:
            severity = "Moderate"
        else:
            severity = "Low"

        return jsonify({'risk_percentage': risk_percentage, 'severity': severity})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ─────────────────────────────────────────────────────────────────────────────
def compute_all_regions_data():
    model = get_model()
    cities = [{"name": k, **v} for k, v in CITY_META.items()]

    weather_data = []
    try:
        lats = ",".join(str(c["lat"]) for c in cities)
        lngs = ",".join(str(c["lng"]) for c in cities)
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lats}&longitude={lngs}"
            f"&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
            f"&daily=precipitation_sum"
            f"&timezone=auto"
            f"&forecast_days=1"
        )
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            resp = r.json()
            weather_data = resp if isinstance(resp, list) else [resp]
    except Exception as e:
        print(f"[WARN] Weather API error: {e}")

    regions_list = []
    for idx, city in enumerate(cities):
        temp, humidity, current_precip, daily_rain, wind_speed = 28.0, 70, 0.0, 5.0, 12.0
        if weather_data and idx < len(weather_data):
            try:
                curr, daily = weather_data[idx].get("current", {}), weather_data[idx].get("daily", {})
                temp = curr.get("temperature_2m", temp)
                humidity = curr.get("relative_humidity_2m", humidity)
                current_precip = curr.get("precipitation", current_precip)
                wind_speed = curr.get("wind_speed_10m", wind_speed)
                precip_list = daily.get("precipitation_sum", [])
                if precip_list: daily_rain = precip_list[0] if precip_list[0] is not None else daily_rain
            except Exception as e:
                print(f"[WARN] Parse error for {city['name']}: {e}")

        rainfall_val = round(daily_rain, 1)
        river_level_val = max(city["baseline_river"], min(9.5, round(city["baseline_river"] + (daily_rain * city["coeff_river"]), 2)))
        soil_moisture_val = max(20, min(100, round(humidity * 0.8 + daily_rain * 0.15)))

        weather_risk = 0.0
        def calc_risk_fallback(r_mm, rl_m, sm_pct):
            return min(100.0, round((r_mm / 300.0 * 50) + (rl_m / 9.5 * 30) + (sm_pct / 100.0 * 20), 1))

        if model is not None:
            try:
                features = pd.DataFrame([[rainfall_val, river_level_val, soil_moisture_val]], columns=['rainfall_mm', 'river_level_m', 'soil_moisture_pct'])
                weather_risk = round(model.predict_proba(features)[0][1] * 100, 1)
            except Exception:
                weather_risk = calc_risk_fallback(rainfall_val, river_level_val, soil_moisture_val)
        else:
            weather_risk = calc_risk_fallback(rainfall_val, river_level_val, soil_moisture_val)

        risk = min(100.0, max(0.0, round((city["vulnerability"] * 35.0) + (weather_risk * 0.65), 1)))
        if rainfall_val > 100.0: risk = max(risk, weather_risk)
        severity = "High" if risk > 70 else ("Moderate" if risk > 30 else "Low")

        regions_list.append({
            "name": city["name"], "lat": city["lat"], "lng": city["lng"], "risk": risk, "severity": severity,
            "weather": {"temp": round(temp, 1), "humidity": humidity, "current_precip": round(current_precip, 1), "wind_speed": round(wind_speed, 1), "rainfall_24h": rainfall_val, "river_level": river_level_val, "soil_moisture": soil_moisture_val}
        })
    return regions_list

@app.route('/api/regions', methods=['GET'])
def regions():
    try:
        return jsonify(compute_all_regions_data())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/forecast')
def forecast_page():
    return render_template('forecast.html')

@app.route('/history')
def history_page():
    return render_template('history.html')

@app.route('/api/forecast')
def forecast():
    city_name = request.args.get('city', '').strip()
    matched_key = next((k for k in CITY_META if k.lower() == city_name.lower()), None)
    if not matched_key:
        return jsonify({'error': f'City "{city_name}" not found.'}), 404

    city = CITY_META[matched_key]
    model = get_model()

    forecast_weather = []
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={city['lat']}&longitude={city['lng']}"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,"
            f"relative_humidity_2m_max,wind_speed_10m_max"
            f"&timezone=auto&forecast_days=7"
        )
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            resp = r.json()
            daily = resp.get('daily', {})
            dates         = daily.get('time', [])
            temp_max_list = daily.get('temperature_2m_max', [])
            temp_min_list = daily.get('temperature_2m_min', [])
            precip_list   = daily.get('precipitation_sum', [])
            humidity_list = daily.get('relative_humidity_2m_max', [])
            wind_list     = daily.get('wind_speed_10m_max', [])
            for i, date_str in enumerate(dates):
                forecast_weather.append({
                    'date_str': date_str,
                    'temp':     round(((temp_max_list[i] or 28) + (temp_min_list[i] or 22)) / 2, 1),
                    'rainfall': round(precip_list[i] or 0.0, 1),
                    'humidity': int(humidity_list[i] or 70),
                    'wind':     round(wind_list[i] or 12.0, 1),
                })
    except Exception as e:
        print(f"[WARN] 7-day forecast API error: {e}")

    if not forecast_weather:
        today = datetime.today()
        for i in range(7):
            forecast_weather.append({
                'date_str': (today + timedelta(days=i)).strftime('%Y-%m-%d'),
                'temp': 28.0, 'rainfall': 5.0, 'humidity': 70, 'wind': 12.0,
            })

    def calc_risk_fallback(r_mm, rl_m, sm_pct):
        v = (r_mm / 300.0 * 50) + (rl_m / 9.5 * 30) + (sm_pct / 100.0 * 20)
        return min(100.0, round(v, 1))

    def classify(r):
        if r > 70: return "High"
        if r > 30: return "Moderate"
        return "Low"

    result = []
    for i, w in enumerate(forecast_weather):
        rainfall_val    = w['rainfall']
        humidity_val    = w['humidity']
        river_level_val = round(city['baseline_river'] + (rainfall_val * city['coeff_river']), 2)
        river_level_val = max(city['baseline_river'], min(9.5, river_level_val))
        soil_moisture   = max(20, min(100, int(humidity_val * 0.8 + rainfall_val * 0.15)))

        if model is not None:
            try:
                features = pd.DataFrame(
                    [[rainfall_val, river_level_val, soil_moisture]],
                    columns=['rainfall_mm', 'river_level_m', 'soil_moisture_pct']
                )
                weather_risk = round(model.predict_proba(features)[0][1] * 100, 1)
            except Exception:
                weather_risk = calc_risk_fallback(rainfall_val, river_level_val, soil_moisture)
        else:
            weather_risk = calc_risk_fallback(rainfall_val, river_level_val, soil_moisture)

        risk = (city['vulnerability'] * 35.0) + (weather_risk * 0.65)
        if rainfall_val > 100.0:
            risk = max(risk, weather_risk)
        risk = min(100.0, max(0.0, round(risk, 1)))

        try:
            date_obj = datetime.strptime(w['date_str'], '%Y-%m-%d')
            label    = 'Today' if i == 0 else date_obj.strftime('%a')
            date_fmt = f"{date_obj.day} {date_obj.strftime('%b')}"
        except Exception:
            label    = 'Today' if i == 0 else f'Day {i+1}'
            date_fmt = w['date_str']

        result.append({
            'label': label, 'date': date_fmt,
            'temp': w['temp'], 'humidity': humidity_val,
            'rainfall_24h': rainfall_val, 'river_level': river_level_val,
            'soil_moisture': soil_moisture, 'wind_speed': w['wind'],
            'risk': risk, 'severity': classify(risk),
        })

    return jsonify(result)    

# ── Alert Signup Page Routes ─────────────────────────────────────────────────
@app.route('/alerts')
def alerts_page():
    return render_template('alerts.html')

@app.route('/api/alerts/login', methods=['POST'])
def alerts_login():
    data = request.json or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    
    if not name or not email:
        return jsonify({'error': 'Name and Email are required.'}), 400
        
    user = database.upsert_user(name, email)
    if user:
        session['user_email'] = user['email']
        return jsonify(user)
    return jsonify({'error': 'Failed to authenticate user.'}), 500

@app.route('/api/alerts/status', methods=['GET'])
def alerts_status():
    email = session.get('user_email')
    if not email:
        return jsonify({'logged_in': False})
        
    user = database.get_user(email)
    if not user:
        session.pop('user_email', None)
        return jsonify({'logged_in': False})
        
    user['logged_in'] = True
    return jsonify(user)

@app.route('/api/alerts/toggle', methods=['POST'])
def alerts_toggle():
    email = session.get('user_email')
    if not email:
        return jsonify({'error': 'Not logged in.'}), 401
        
    data = request.json or {}
    enabled = data.get('notifications_enabled', True)
    
    success = database.update_notification_setting(email, enabled)
    if success:
        return jsonify({'success': True, 'notifications_enabled': 1 if enabled else 0})
    return jsonify({'error': 'Failed to update alert preferences.'}), 500

@app.route('/api/alerts/test-email', methods=['POST'])
def alerts_test_email():
    email = session.get('user_email')
    if not email:
        return jsonify({'error': 'Not logged in.'}), 401
        
    user = database.get_user(email)
    if not user:
        return jsonify({'error': 'User session not found in database.'}), 404
        
    regions_data = compute_all_regions_data()
    active_alerts = [r for r in regions_data if r['severity'] in ('High', 'Moderate')]
    
    from email_notifier import send_test_email, is_smtp_configured
    success = send_test_email(user['email'], user['name'], active_alerts)

    if success:
        configured = is_smtp_configured()
        return jsonify({
            'success': True,
            'simulated': not configured,
            'message': 'Test email sent to your inbox!' if configured else 'SMTP not configured — email saved to sent_emails_log.txt instead.'
        })
    return jsonify({'error': 'Failed to send test email.'}), 500

@app.route('/api/alerts/logout', methods=['POST'])
def alerts_logout():
    session.pop('user_email', None)
    return jsonify({'success': True})

@app.route('/api/alerts/smtp-status', methods=['GET'])
def alerts_smtp_status():
    """Returns whether the Gmail App Password has been properly configured."""
    from email_notifier import is_smtp_configured
    return jsonify({'configured': is_smtp_configured()})

@app.route('/api/alerts/configure-smtp', methods=['POST'])
def alerts_configure_smtp():
    """Saves the Gmail App Password to config.json so emails can be sent."""
    data = request.json or {}
    password = data.get('smtp_password', '').strip()
    if not password:
        return jsonify({'error': 'App password cannot be empty.'}), 400

    from email_notifier import save_smtp_password
    success, message = save_smtp_password(password)
    if success:
        return jsonify({'success': True, 'message': 'Gmail App Password saved! Emails will now be sent directly.'})
    return jsonify({'error': message}), 500

# ── Daily Scheduler Thread ───────────────────────────────────────────────────
_last_alert_sent_date = None

def daily_alert_scheduler():
    global _last_alert_sent_date
    print("[Scheduler] Background alert thread started.")
    while True:
        try:
            now = datetime.now()
            # Run alert check every morning between 8:00 AM and 8:05 AM
            current_date_str = now.strftime('%Y-%m-%d')
            if now.hour == 8 and now.minute < 5:
                if _last_alert_sent_date != current_date_str:
                    print(f"[Scheduler] Running daily morning alert dispatch for {current_date_str}...")
                    
                    regions_data = compute_all_regions_data()
                    active_alerts = [r for r in regions_data if r['severity'] in ('High', 'Moderate')]
                    
                    subscribers = database.get_subscribers()
                    
                    if subscribers and active_alerts:
                        from email_notifier import send_daily_alerts
                        send_daily_alerts(subscribers, active_alerts)
                        print(f"[Scheduler] Daily morning alerts dispatched successfully.")
                    else:
                        print(f"[Scheduler] Daily check completed: {len(subscribers)} subscribers, {len(active_alerts)} active alerts. No alerts sent.")
                    
                    _last_alert_sent_date = current_date_str
        except Exception as e:
            print(f"[Scheduler] Error checking/dispatching daily alerts: {e}")
            
        time.sleep(60)

def start_scheduler():
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        t = threading.Thread(target=daily_alert_scheduler, daemon=True)
        t.start()
        print("[Scheduler] Background thread initialized.")

# Start the scheduler
start_scheduler()

# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True, port=5000)
