import spidev
import time

def amp_to_pot_value(amp):
    res_vals = [45, 61, 74, 88, 103, 119, 136, 152, 167]
    if amp == 0: return res_vals[0]
    elif amp <= 6: return res_vals[1]
    elif amp <= 8: return res_vals[2]
    elif amp <= 10: return res_vals[3]
    elif amp <= 13: return res_vals[4]
    elif amp <= 16: return res_vals[5]
    elif amp <= 20: return res_vals[6]
    elif amp <= 25: return res_vals[7]
    elif amp <= 32: return res_vals[8]
    else: return res_vals[0]

def set_pot_current(spi, amp_value):
    raw_pot_value = amp_to_pot_value(amp_value)
    msb = 0x00 #RAM 
    lsb = 0xFF - int(raw_pot_value)
    try:
        spi.xfer2([msb, lsb])
        print(f"Befehl gesendet: Ampere={amp_value}A, Rohwert={raw_pot_value}, SPI=[{hex(msb)}, {hex(lsb)}]")
    except Exception as e:
        print(f"Fehler beim Senden via SPI: {e}")

spi = None
try:
    spi = spidev.SpiDev()
    spi.open(0, 0)
    spi.max_speed_hz = 976000
    print("SPI-Schnittstelle erfolgreich geoeffnet.")
    print("--- Manueller Potentiometer-Test ---")
    print("Geben Sie den gewuenschten Ladestrom in Ampere ein (z.B. 6, 10, 16).")
    print("Druecken Sie STRG+C zum Beenden.")

    while True:
        try:
            user_input = input("\nNeuer Ladestrom (A): ")
            target_amp = int(user_input)
            if 0 <= target_amp <= 32:
                set_pot_current(spi, target_amp)
            else:
                print("Ungueltiger Wert. Bitte zwischen 0 und 32 eingeben.")
        except ValueError:
            print("Das war keine gueltige Zahl.")
except KeyboardInterrupt:
    print("\nProgramm wird beendet. Setze Strom sicherheitshalber auf 0A.")
    if spi:
        set_pot_current(spi, 0)
finally:
    if spi:
        spi.close()
        print("SPI-Schnittstelle geschlossen.")
