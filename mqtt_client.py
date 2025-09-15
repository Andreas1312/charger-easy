# /opt/juice-charger/mqtt_client.py
import paho.mqtt.client as mqtt
import time
import json
import logging
from logging.handlers import RotatingFileHandler
import yaml
import sys

from juice_booster_control import JuiceBoosterControl

# --- Konfigurationsdatei laden ---
CONFIG_PATH = "/opt/juice-charger/config.yaml"

try:
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
except FileNotFoundError:
    print(f"Fehler: Konfigurationsdatei '{CONFIG_PATH}' nicht gefunden. Bitte erstellen Sie sie.", file=sys.stderr)
    sys.exit(1)
except yaml.YAMLError as e:
    print(f"Fehler beim Parsen der Konfigurationsdatei '{CONFIG_PATH}': {e}", file=sys.stderr)
    sys.exit(1)

# --- Logging Konfiguration (aus der config.yaml) ---
log_level_str = config['logging'].get('level', 'INFO').upper()
log_level = getattr(logging, log_level_str, logging.INFO)

log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler = RotatingFileHandler(config['logging']['file_path'], maxBytes=10*1024*1024, backupCount=5)
file_handler.setFormatter(log_formatter)
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

logger = logging.getLogger('mqtt_client_logger')
logger.setLevel(log_level)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# --- MQTT Konfiguration (aus der config.yaml) ---
MQTT_BROKER_HOST = config['mqtt']['broker_host']
MQTT_BROKER_PORT = config['mqtt']['broker_port']
MQTT_CLIENT_ID = config['mqtt']['client_id']
MQTT_USERNAME = config['mqtt'].get('username')
MQTT_PASSWORD = config['mqtt'].get('password')
BASE_TOPIC = config['mqtt']['base_topic']

# --- EVCC-kompatible MQTT Topics ---
TOPIC_ENABLE_SET = f"{BASE_TOPIC}/enable/set"
TOPIC_MAX_CURRENT_SET = f"{BASE_TOPIC}/maxCurrent/set"
TOPIC_STATUS_GET = f"{BASE_TOPIC}/status"
TOPIC_ENABLED_GET = f"{BASE_TOPIC}/enabled"
TOPIC_CHARGE_CURRENT_GET = f"{BASE_TOPIC}/chargeCurrent"
TOPIC_DEBUG_STATUS = f"{BASE_TOPIC}/debug/status"

# --- RLC Percentages (aus der config.yaml) ---
RLC_PERCENTAGES_FROM_CONFIG = config.get('rlc_percentages', {})

# --- Buzzer Konfiguration (aus der config.yaml) ---
BUZZER_CONFIG = config.get('buzzer', {'enabled': False, 'melodies': {}})

# --- LED Konfiguration (aus der config.yaml) ---
LED_ENABLED = config.get('leds', {}).get('enabled', False)


# --- Globale Zustandsvariablen ---
controller = None
client = None
# RLC_enabled = False 
evcc_enabled = False             
evcc_target_current = 6          
was_charging = False             
# Verfolgt den letzten CP-Status, um Änderungen zu erkennen und Melodien auszulösen
last_cp_state = None


# --- MQTT Callbacks ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Erfolgreich mit MQTT-Broker verbunden.")
        client.subscribe([(TOPIC_ENABLE_SET, 0), (TOPIC_MAX_CURRENT_SET, 0)])
        logger.info(f"Abonniert auf: {TOPIC_ENABLE_SET}, {TOPIC_MAX_CURRENT_SET}")
    else:
        logger.error(f"Verbindung fehlgeschlagen mit Code: {rc}")

def on_message(client, userdata, msg):
    global evcc_enabled, evcc_target_current
    payload = msg.payload.decode('utf-8')
    logger.debug(f"MQTT-Nachricht empfangen: Topic='{msg.topic}', Payload='{payload}'")

    if msg.topic == TOPIC_ENABLE_SET:
        evcc_enabled = (payload.lower() == 'true')
        logger.info(f"EVCC Command: Charger {'enabled' if evcc_enabled else 'disabled'}.")
        if not evcc_enabled: # Wenn Ladegerät durch EVCC deaktiviert wird
            controller.play_melody("stop_charging") 
    elif msg.topic == TOPIC_MAX_CURRENT_SET:
        try:
            evcc_target_current = int(float(payload))
            logger.info(f"EVCC Command: Target current set to {evcc_target_current}A.")
        except ValueError:
            logger.warning(f"Ungueltiger Wert fuer Ladestrom empfangen: {payload}")

# --- Hauptprogramm ---
def main():
    global was_charging, controller, client, last_cp_state
    
    try:
        # Controller mit RLC-Prozentsaetzen und Buzzer-Konfiguration initialisieren
        controller = JuiceBoosterControl(
            rlc_percentages_from_config=RLC_PERCENTAGES_FROM_CONFIG,
            buzzer_config=BUZZER_CONFIG, led_enabled=LED_ENABLED
            ) 
        
        client = mqtt.Client(client_id=MQTT_CLIENT_ID)
        if MQTT_USERNAME and MQTT_PASSWORD:
            client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        client.on_connect = on_connect
        client.on_message = on_message
        
        client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
        client.loop_start()
        
        logger.info("Steuerung gestartet. Hauptschleife beginnt.")
        
        while True:
            free_charge_mode = controller.is_free_charging_enabled()
            cp_state = controller.get_cp_state()
            max_hw_current = controller.get_max_hardware_current()
            is_connected = (cp_state in ['B', 'C'])

            # LEDs aktualisieren, wenn aktiviert
            if LED_ENABLED:
                controller.led()


            # Erkennung von CP-Status-Änderungen für Melodien
            if cp_state != last_cp_state:
                if cp_state in ['B', 'C'] and last_cp_state not in ['B', 'C']:
                    logger.info(f"Fahrzeug verbunden (CP-State Wechsel von {last_cp_state} zu {cp_state}).")
                    controller.play_melody("car_connected")
                elif cp_state == 'A' and last_cp_state in ['B', 'C']:
                    logger.info(f"Fahrzeug getrennt (CP-State Wechsel von {last_cp_state} zu {cp_state}).")
                    controller.play_melody("stop_charging") # Oder andere Melodie bei Trennung
                last_cp_state = cp_state # Letzten Status aktualisieren

            requested_current_by_logic = 0
            mode_status = ""
            
            # --- Priorisierung der Lademodi (nur FreeCharge und EVCC) ---
            if free_charge_mode: 
                mode_status = "FreeCharge Mode"
                if is_connected:
                    requested_current_by_logic = max_hw_current
            else: 
                mode_status = "EVCC Control"
                if evcc_enabled and is_connected:
                    requested_current_by_logic = evcc_target_current
                else: 
                    requested_current_by_logic = 0
            
            effective_current = controller.set_charge_current(requested_current_by_logic)
            
            # Ladezustand ermitteln (wenn wirklich Strom fließt und CP='C')
            is_charging = (effective_current > 0 and cp_state == 'C')
            
            # Melodie beim tatsächlichen Start/Stopp des Ladevorgangs
            if is_charging and not was_charging:
                logger.info("Ladevorgang startet. Spiele Melodie 'start_charging'.")
                controller.play_melody("start_charging")
            elif not is_charging and was_charging:
                logger.info("Ladevorgang beendet. Spiele Melodie 'stop_charging'.")
                controller.play_melody("stop_charging")

            was_charging = is_charging
            
            # Status an MQTT publizieren (für EVCC und andere)
            client.publish(TOPIC_STATUS_GET, cp_state, retain=True)
            client.publish(TOPIC_ENABLED_GET, "true" if effective_current > 0 else "false", retain=True)
            client.publish(TOPIC_CHARGE_CURRENT_GET, str(effective_current), retain=True)

            # Debug-Status publizieren (mit allen relevanten Werten)
            debug_payload = {
                "cp_state": cp_state,
                "mode_active": mode_status,
                "evcc_cmd_enabled": evcc_enabled,
                "evcc_target_current_cmd": evcc_target_current,
                "hw_max_current": max_hw_current,
                "rlc_percentage": controller.get_rlc_percentage(), 
                "effective_current_A": effective_current,
                "is_charging": is_charging,
                "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            }
            client.publish(TOPIC_DEBUG_STATUS, json.dumps(debug_payload), retain=True)
            logger.info(f"Status: Mode={mode_status}, CP={cp_state}, HW-Max={max_hw_current}A, RLC={controller.get_rlc_percentage()}%, EVCC-Target={evcc_target_current}A, Effektiv={effective_current:.1f}A")

            time.sleep(2) 

    except KeyboardInterrupt:
        logger.info("\nProgramm wird durch Benutzer beendet.")
    except Exception as e:
        logger.error(f"Ein unerwarteter Fehler ist aufgetreten: {e}", exc_info=True)
    finally:
        if client and client.is_connected():
            client.loop_stop()
            client.disconnect()
        if controller:
            controller.cleanup()
        logger.info("Aufgeraeumt und beendet.")

if __name__ == '__main__':
    main()