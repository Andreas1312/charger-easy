# evcc_http_server.py

import yaml
import logging
import logging.config
import os
from flask import Flask, request, jsonify, make_response
from functools import wraps
import sys

# Importiere die tatsächliche JuiceBoosterControl-Klasse.
# Stelle sicher, dass diese Datei (juice_booster_control.py) im selben Verzeichnis liegt
# oder im Python-Pfad verfügbar ist.
try:
    from juice_booster_control import JuiceBoosterControl
except ImportError:
    print("FEHLER: 'juice_booster_control.py' konnte nicht gefunden oder importiert werden.")
    print("Bitte stellen Sie sicher, dass die Datei im selben Verzeichnis wie 'evcc_http_server.py' liegt.")
    sys.exit(1) # Beende das Skript, wenn die Kontrollklasse fehlt

app = Flask(__name__)
# Globale Variable für die JuiceBoosterControl-Instanz
juice_booster_controller: JuiceBoosterControl = None
EVCC_BEARER_TOKEN = ""
logger = None

def load_config(config_path="config.yaml"):
    """Lädt die Konfiguration aus der YAML-Datei und konfiguriert das Logging."""
    global logger
    try:
        # Laden der Konfiguration
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Konfigurationsdatei '{config_path}' nicht gefunden.")

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Konfigurieren des Loggings
        log_file_path = config.get('logging', {}).get('file_path', '/tmp/charger.log')
        log_level_str = config.get('logging', {}).get('level', 'INFO').upper()
        
        numeric_level = getattr(logging, log_level_str, None)
        if not isinstance(numeric_level, int):
            raise ValueError(f'Ungültiger Log-Level in Konfiguration ($logging.level): {log_level_str}')

        logging.config.dictConfig({
            'version': 1,
            'formatters': {
                'standard': {
                    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                }
            },
            'handlers': {
                'file': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'formatter': 'standard',
                    'filename': log_file_path,
                    'maxBytes': 10485760,  # 10 MB
                    'backupCount': 5,
                    'level': numeric_level,
                },
                'console': {
                    'class': 'logging.StreamHandler',
                    'formatter': 'standard',
                    'level': numeric_level,
                }
            },
            'root': {
                'handlers': ['file', 'console'],
                'level': numeric_level,
            },
            'disable_existing_loggers': False
        })
        logger = logging.getLogger(__name__)
        logger.info("Logging wurde konfiguriert.")
        
        return config
    except FileNotFoundError:
        print(f"FATAL: Konfigurationsdatei '{config_path}' nicht gefunden. Beende.")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"FATAL: Fehler beim Parsen der Konfigurationsdatei: {e}. Beende.")
        sys.exit(1)
    except Exception as e:
        print(f"FATAL: Ein unerwarteter Fehler beim Laden/Konfigurieren ist aufgetreten: {e}. Beende.")
        sys.exit(1)

def auth_required(f):
    """
    Decorator zur Überprüfung des Bearer-Tokens in der Anfrage.
    evcc sendet den Token im Header 'Authorization: Bearer <token>'.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        global logger, EVCC_BEARER_TOKEN
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            logger.warning(f"Autorisierungs-Header fehlt für Anfrage an '{request.path}'.")
            return make_response(jsonify({"error": "Authorization header missing"}), 401)
        
        try:
            token_type, token = auth_header.split(None, 1) # Split by space, max 1 split
        except ValueError:
            logger.warning(f"Autorisierungs-Header ist ungültig formatiert: '{auth_header}'.")
            return make_response(jsonify({"error": "Invalid Authorization header format"}), 401)
        
        if token_type.lower() != 'bearer':
            logger.warning(f"Ungültiger Token-Typ '{token_type}', 'Bearer' erwartet.")
            return make_response(jsonify({"error": "Invalid token type, expected Bearer"}), 401)
        
        if token != EVCC_BEARER_TOKEN:
            logger.warning(f"Bearer-Token ist ungültig oder stimmt nicht überein. Erhalten: '{token}', Erwartet: '{EVCC_BEARER_TOKEN}' (gekürzt).")
            return make_response(jsonify({"error": "Invalid Bearer token"}), 403)
        
        return f(*args, **kwargs)
    return decorated_function

# --- EVCC API Endpunkte ---

@app.route('/charger/health', methods=['GET'])
def health_check():
    """Ein einfacher Health Check Endpunkt, um die Erreichbarkeit zu prüfen."""
    return jsonify({"status": "ok"}), 200

@app.route('/charger/status', methods=['GET'])
@auth_required
def get_status():
    """Gibt den aktuellen Status des Ladegeräts zurück."""
    global juice_booster_controller, logger
    if not juice_booster_controller:
        logger.error("JuiceBoosterControl ist nicht initialisiert.")
        return make_response(jsonify({"error": "Charger not initialized"}), 500)
    
    try:
        status_data = juice_booster_controller.get_charger_status()
        logger.debug(f"Charger status requested: {status_data}")
        return jsonify(status_data), 200
    except Exception as e:
        logger.error(f"Fehler beim Abrufen des Charger-Status: {e}", exc_info=True)
        return make_response(jsonify({"error": f"Failed to get charger status: {e}"}), 500)

@app.route('/charger/minCurrent', methods=['GET'])
@auth_required
def get_min_current():
    """Gibt den minimalen Ladestrom in Ampere zurück."""
    global juice_booster_controller, logger
    if not juice_booster_controller:
        logger.error("JuiceBoosterControl ist nicht initialisiert.")
        return make_response(jsonify({"error": "Charger not initialized"}), 500)
    
    try:
        min_c = juice_booster_controller.get_min_charging_current()
        logger.debug(f"Min current requested: {min_c}")
        return jsonify(min_c), 200
    except Exception as e:
        logger.error(f"Fehler beim Abrufen des minimalen Ladestroms: {e}", exc_info=True)
        return make_response(jsonify({"error": f"Failed to get min current: {e}"}), 500)

@app.route('/charger/maxCurrent', methods=['GET'])
@auth_required
def get_max_current():
    """Gibt den maximalen Ladestrom in Ampere zurück."""
    global juice_booster_controller, logger
    if not juice_booster_controller:
        logger.error("JuiceBoosterControl ist nicht initialisiert.")
        return make_response(jsonify({"error": "Charger not initialized"}), 500)
    
    try:
        max_c = juice_booster_controller.get_max_charging_current()
        logger.debug(f"Max current requested: {max_c}")
        return jsonify(max_c), 200
    except Exception as e:
        logger.error(f"Fehler beim Abrufen des maximalen Ladestroms: {e}", exc_info=True)
        return make_response(jsonify({"error": f"Failed to get max current: {e}"}), 500)

@app.route('/charger/targetCurrent', methods=['POST'])
@auth_required
def set_target_current():
    """Setzt den Zielladestrom."""
    global juice_booster_controller, logger
    if not juice_booster_controller:
        logger.error("JuiceBoosterControl ist nicht initialisiert.")
        return make_response(jsonify({"error": "Charger not initialized"}), 500)

    data = request.get_json()
    if not data or 'value' not in data:
        logger.warning(f"Ungültige JSON-Anfrage zum Setzen des Zielladestroms: {data}")
        return make_response(jsonify({"error": "Invalid JSON payload, 'value' missing"}), 400)
    
    try:
        current = float(data['value'])
        if juice_booster_controller.set_charging_current(current):
            logger.info(f"Zielladestrom erfolgreich auf {current}A gesetzt.")
            return jsonify({"success": True, "message": f"Target current set to {current}A"}), 200
        else:
            logger.error(f"Fehler beim Setzen des Zielladestroms auf {current}A.")
            return make_response(jsonify({"success": False, "error": "Failed to set charging current"}), 500)
    except ValueError:
        logger.warning(f"Ungültiger Wert für 'value' erhalten: {data['value']} (muss eine Zahl sein).")
        return make_response(jsonify({"error": "Invalid value for 'value', must be a number"}), 400)
    except Exception as e:
        logger.error(f"Fehler beim Setzen des Zielladestroms: {e}", exc_info=True)
        return make_response(jsonify({"error": f"Failed to set target current: {e}"}), 500)

@app.route('/charger/enable', methods=['POST'])
@auth_required
def enable_charger():
    """Aktiviert oder deaktiviert das Laden."""
    global juice_booster_controller, logger
    if not juice_booster_controller:
        logger.error("JuiceBoosterControl ist nicht initialisiert.")
        return make_response(jsonify({"error": "Charger not initialized"}), 500)

    data = request.get_json()
    if not data or 'value' not in data or not isinstance(data['value'], bool):
        logger.warning(f"Ungültige JSON-Anfrage zum Aktivieren/Deaktivieren des Chargers: {data}")
        return make_response(jsonify({"error": "Invalid JSON payload, 'value' (boolean) missing"}), 400)

    try:
        on = data['value']
        if on:
            if juice_booster_controller.enable_charging():
                logger.info("Ladevorgang erfolgreich aktiviert.")
                return jsonify({"success": True, "message": "Charging enabled"}), 200
            else:
                logger.error("Fehler beim Aktivieren des Ladevorgangs.")
                return make_response(jsonify({"success": False, "error": "Failed to enable charging"}), 500)
        else:
            if juice_booster_controller.disable_charging():
                logger.info("Ladevorgang erfolgreich deaktiviert.")
                return jsonify({"success": True, "message": "Charging disabled"}), 200
            else:
                logger.error("Fehler beim Deaktivieren des Ladevorgangs.")
                return make_response(jsonify({"success": False, "error": "Failed to disable charging"}), 500)
    except Exception as e:
        logger.error(f"Fehler beim Aktivieren/Deaktivieren des Chargers: {e}", exc_info=True)
        return make_response(jsonify({"error": f"Failed to toggle charger enable state: {e}"}), 500)

@app.route('/charger/energy', methods=['GET'])
@auth_required
def get_energy():
    """Gibt die insgesamt geladene Energie in kWh zurück (optional)."""
    global juice_booster_controller, logger
    if not juice_booster_controller:
        logger.error("JuiceBoosterControl ist nicht initialisiert.")
        return make_response(jsonify({"error": "Charger not initialized"}), 500)
    
    try:
        total_energy_kwh = juice_booster_controller.get_total_energy()
        logger.debug(f"Total energy requested: {total_energy_kwh} kWh")
        return jsonify(total_energy_kwh), 200
    except AttributeError:
        # Falls get_total_energy() in juice_booster_control.py nicht implementiert ist.
        logger.warning("get_total_energy() ist nicht in juice_booster_control.py implementiert. Melde 0 kWh.")
        return jsonify(0.0), 200 # oder 404/501, je nach gewünschtem Verhalten
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Gesamtenergie: {e}", exc_info=True)
        return make_response(jsonify({"error": f"Failed to get total energy: {e}"}), 500)

if __name__ == '__main__':
    config = load_config() # Lädt die Konfiguration und konfiguriert das Logging

    http_config = config.get('http_server', {})
    evcc_port = http_config.get('port', 7070)
    EVCC_BEARER_TOKEN = http_config.get('bearer_token') # Sollte vorhanden sein
    
    if not EVCC_BEARER_TOKEN or EVCC_BEARER_TOKEN == "DeinGeheimerEvccToken123":
        logger.critical("HTTP Bearer Token wurde nicht in der Konfiguration gesetzt oder ist der Standardwert. Bitte prüfen Sie Ihre config.yaml und setzen Sie einen sicheren Token! Beende.")
        sys.exit(1)

    rlc_percentages = config.get('rlc_percentages', {})
    
    # Initialisiere die bestehende JuiceBoosterControl-Instanz
    try:
        # Hier wird die JuiceBoosterControl-Klasse aus deiner juice_booster_control.py verwendet
        juice_booster_controller = JuiceBoosterControl(rlc_percentages, logger)
        logger.info("JuiceBoosterControl erfolgreich initialisiert.")
        # Optional: buzzer_config = config.get('buzzer', {})
        # juice_booster_controller.set_buzzer_config(buzzer_config) # Falls vorhanden
    except Exception as e:
        logger.critical(f"Kritischer Fehler bei der Initialisierung von JuiceBoosterControl: {e}", exc_info=True)
        sys.exit(1) # Beende den Server bei kritischem Fehler

    logger.info(f"EVCC HTTP Server startet auf Port {evcc_port}...")
    app.run(host='0.0.0.0', port=evcc_port, debug=False)