# /opt/juice-charger/juice_booster_control.py
import spidev
import RPi.GPIO as GPIO
import time
import sys
import logging

class JuiceBoosterControl: 
    def __init__(self, spi_bus=0, spi_device=0, spi_max_speed_hz=976000, rlc_percentages_from_config=None, buzzer_config=None, led_enabled=False): 
        self.logger = logging.getLogger(__name__)
        # SPI Initialisierung 
        self.spi = spidev.SpiDev() 
        self.spi.open(spi_bus, spi_device) 
        self.spi.max_speed_hz = spi_max_speed_hz

        # --- GPIO Pin-Konfiguration --- 
        self.CP_PIN_A = 6
        self.CP_PIN_B = 26
        self.MAX_AMP_PINS = [18, 24, 23, 25]  
        self.FREE_CHARGE_PIN = 22
        self.RLC_DIP_PIN = 27 
        self.LED_GREEN_PIN = 12
        self.LED_BLUE_PIN = 19
        self.BUZZER_PIN = 13

        _hardcoded_rlc_bcm_pins_mapping = {
            'rlc1': 21, 
            'rlc2': 20, 
            'rlc3': 16, 
            'rlc4': 5   
        }
        
        rlc_mappings_list_temp = []
        if rlc_percentages_from_config:
            for rlc_config_key, percentage_value_from_config in rlc_percentages_from_config.items():
                bcm_pin = _hardcoded_rlc_bcm_pins_mapping.get(rlc_config_key)
                if bcm_pin is not None:
                    rlc_mappings_list_temp.append({'percentage': percentage_value_from_config, 'bcm_pin': bcm_pin})
                else:
                    print(f"WARNUNG: RLC-Schluessel '{rlc_config_key}' in config.yaml hat keinen zugewiesenen BCM-Pin im Code.", file=sys.stderr)
        
        rlc_mappings_list_temp.sort(key=lambda x: x['percentage'])
        self.RLC_PINS = {item['percentage']: item['bcm_pin'] for item in rlc_mappings_list_temp}

        
        self.last_set_current = -1 
      
        # --- GPIO Setup ---
        GPIO.setwarnings(False) 
        GPIO.setmode(GPIO.BCM) 
        GPIO.setup([self.CP_PIN_A, self.CP_PIN_B], GPIO.IN, pull_up_down=GPIO.PUD_DOWN) 
        GPIO.setup(self.MAX_AMP_PINS, GPIO.IN, pull_up_down=GPIO.PUD_UP) 
        GPIO.setup(self.FREE_CHARGE_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP) 
        GPIO.setup(self.RLC_DIP_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP) 
        GPIO.setup(self.LED_GREEN_PIN, GPIO.OUT)
        GPIO.setup(self.LED_BLUE_PIN, GPIO.OUT)

        rlc_bcm_pins_to_setup_list = list(self.RLC_PINS.values())
        if rlc_bcm_pins_to_setup_list: 
            GPIO.setup(rlc_bcm_pins_to_setup_list, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) 
   

        # Buzzer GPIO Setup und PWM Initialisierung
        GPIO.setup(self.BUZZER_PIN, GPIO.OUT) 
        GPIO.output(self.BUZZER_PIN, GPIO.LOW) # Sicherstellen, dass Buzzer initial aus ist

        self.buzzer_pwm = GPIO.PWM(self.BUZZER_PIN, 1000) # Standardfrequenz (wird in play_melody geaendert)
        self.buzzer_pwm.stop() # Sicherstellen, dass PWM initial gestoppt ist

        # --- Buzzer Melodien Konfiguration ---
        self.buzzer_enabled = buzzer_config.get('enabled', False) if buzzer_config else False
        self.melodies = buzzer_config.get('melodies', {}) if buzzer_config else {}

        # --- Initialisierung des Potentiometers ---
        self.startup_initialize() 
        # Spiele Startup Melodie, wenn Buzzer aktiviert ist
        if self.buzzer_enabled:
            self.play_melody("startup") # Kann "selftest_completed" sein, je nach gewählter Melodie

    
    def led (self):
        evcc_state = GPIO.input(self.FREE_CHARGE_PIN)
        rlc_state = GPIO.input(self.RLC_DIP_PIN)
        # Grüne LED für FREE_CHARGE_PIN Status
        GPIO.output(self.LED_GREEN_PIN, GPIO.HIGH if evcc_state == GPIO.HIGH else GPIO.LOW)

        # Blaue LED für RLC_DIP_PIN Status (invertiert)
        GPIO.output(self.LED_BLUE_PIN, GPIO.HIGH if rlc_state == GPIO.LOW else GPIO.LOW)

    def _write_pot(self, value, non_volatile=False): 
        msb = 0x20 if non_volatile else 0x00
        lsb = 0xFF - int(value) 
        try: 
            self.spi.xfer2([msb, lsb]) 
        except Exception as e: 
            print(f"Fehler beim Schreiben auf SPI: {e}", file=sys.stderr) 

    def _amp_to_pot_value(self, amp): 
        res_vals = [45, 61, 74, 88, 103, 119, 136, 152, 167] 
        if amp <= 0: return res_vals[0] 
        elif amp <= 6: return res_vals[1] 
        elif amp <= 8: return res_vals[2] 
        elif amp <= 10: return res_vals[3] 
        elif amp <= 13: return res_vals[4] 
        elif amp <= 16: return res_vals[5] 
        elif amp <= 20: return res_vals[6] 
        elif amp <= 25: return res_vals[7] 
        elif amp <= 32: return res_vals[8] 
        else: return res_vals[8] 

    def startup_initialize(self): 
        max_hw_current = self.get_max_hardware_current()
        pot_value_hw_max = self._amp_to_pot_value(max_hw_current)
        self._write_pot(pot_value_hw_max, non_volatile=True)
        time.sleep(5.1) # Wartezeit auf Jucice Booster bis der Set wirksam wird 
        
        pot_value_0A = self._amp_to_pot_value(0)
        self._write_pot(pot_value_0A, non_volatile=False)
        self.last_set_current = 0
        print(f"Initialisierung abgeschlossen. HW-Limit: {max_hw_current}A. Aktiver Strom: 0A.")
        
    def play_melody(self, melody_name, default_frequency=1000, default_duration_ms=200, duty_cycle=50): 
        """
        Spielt eine definierte Melodie ab.
        Wenn die Melodie nicht gefunden wird oder keine Sequenz hat, wird ein einfacher Piepton abgespielt (falls enabled).
        Frequenz (f) in Hz, Dauer (d) in Millisekunden.
        """
        if not self.buzzer_enabled:
            return

        melody_data = self.melodies.get(melody_name)
        if not melody_data or not melody_data.get('sequence'):
            # Fallback: Einfacher Piepton, wenn Melodie nicht gefunden oder keine Sequenz hat
            print(f"WARNUNG: Melodie '{melody_name}' nicht gefunden oder hat keine Sequenz. Spiele einen Standard-Piepton.", file=sys.stderr)
            try:
                self.buzzer_pwm.ChangeFrequency(default_frequency)
                self.buzzer_pwm.start(duty_cycle)
                time.sleep(default_duration_ms / 1000.0)
                self.buzzer_pwm.stop()
            except Exception as e:
                print(f"Fehler beim Standard-Buzzer: {e}", file=sys.stderr)
            return

        sequence = melody_data['sequence']
        for note in sequence:
            frequency = note.get('f', 0)
            duration_ms = note.get('d', 0)

            if frequency > 0 and duration_ms > 0:
                try:
                    self.buzzer_pwm.ChangeFrequency(frequency)
                    self.buzzer_pwm.start(duty_cycle)
                    time.sleep(duration_ms / 1000.0) # Dauer in Sekunden umwandeln
                    self.buzzer_pwm.stop()
                except Exception as e:
                    print(f"Fehler beim Abspielen Note f={frequency}, d={duration_ms}: {e}", file=sys.stderr)
                    self.buzzer_pwm.stop() # Sicherstellen, dass der Buzzer stoppt
            elif duration_ms > 0: # Frequenz 0 bedeutet Pause
                time.sleep(duration_ms / 1000.0) # Pause in Sekunden

    def get_max_hardware_current(self): 
        try: 
            selected_pins = self.MAX_AMP_PINS[0:3] 
            raw_vals = [GPIO.input(pin) for pin in selected_pins]
            #binary_str = "".join(map(str, map(int, raw_vals)))
            #read_value = int(binary_str, 2)
            #correct_index = 7 - read_value 
            position = raw_vals[0] + (raw_vals[1] << 1) + (raw_vals[2] << 2)
            max_amp_array = [6, 8, 10, 13, 16, 20, 25, 32]
            if 0 <= position <= 7:
                return max_amp_array[position]
            else:
                print(f"Ungültige Schalterposition {position}. Raw inputs: {raw_vals}", file=sys.stderr)
                return 6

            #return max_amp_array[correct_index] 
        except Exception as e: 
            print(f"Fehler beim Lesen des Drehschalters: {e}", file=sys.stderr) 
            return 6 

    def get_rlc_percentage(self): 
        if not GPIO.input(self.RLC_DIP_PIN): 
            return 100 
        
        for percentage, pin in self.RLC_PINS.items(): 
            if GPIO.input(pin): 
                return percentage
        
        return 100 

    def is_free_charging_enabled(self): 
        return GPIO.input(self.FREE_CHARGE_PIN) 

    def set_charge_current(self, requested_amperes): 
        max_hw_current = self.get_max_hardware_current() 
        rlc_percentage = self.get_rlc_percentage() 
        rlc_limited_current = max_hw_current * (rlc_percentage / 100.0) 
        
        requested_amperes = max(0, float(requested_amperes)) 
        effective_amperes = min(requested_amperes, rlc_limited_current) 
        
        if effective_amperes != self.last_set_current: 
            self.last_set_current = effective_amperes
            pot_value = self._amp_to_pot_value(effective_amperes) 
            self._write_pot(pot_value, non_volatile=False) 
        
        return effective_amperes

    def get_cp_state(self): 
        pin_a = GPIO.input(self.CP_PIN_A) 
        pin_b = GPIO.input(self.CP_PIN_B) 
        index = (pin_a << 1) | pin_b
        stati_jc_easy = ['A', 'E', 'B', 'C'] 
        return stati_jc_easy[index] if 0 <= index < len(stati_jc_easy) else 'F' 

    def cleanup(self): 
        print("Raeume GPIO und SPI auf...") 
        self.set_charge_current(0) 
        self.spi.close() 
        self.buzzer_pwm.stop() # PWM-Instanz explizit stoppen
        GPIO.cleanup()
