## Juice Booster (Juice Charger Easy) — EVCC / MQTT Integration
Dieses Repository enthält die Software, um die ursprüngliche Steuerung des Juice Booster (Juice CHARGER Easy) vollständig zu ersetzen und die Integration in EVCC über MQTT zu ermöglichen. 

Wichtig: Dieses Projekt verändert das Ladeverhalten eines EV-Ladegeräts.

Ersetzt die originale Juice Booster Ansteuerung  im Juice CHARGER Easy.
Stellt Steuerung über MQTT bereit (Integration in EVCC).
Priorisierung: Hardware-RLC-Eingänge haben wenn aktiv Vorrang vor EVCC-Steuerung. 
# Funktion des Jceasy HAT
CP-Zustand (A, B, C, E) wird per GPIO gelesen (PIC12F1572-E für CP-Auswertung).
Ladestrom wird über MCP4161-103E gesteuert. Beim ersten Start wird im EEPROM-Register (0x20) ein „Maximalstrom“ als Hardware-Fallback geschrieben. Für den laufenden Betrieb wird das RAM‑Register 0x00 des MCP4161 verwendet (volatile Pot‑Wert).
Die Software liest die DIP‑Schalter, Codierschalter und RLC‑Eingänge beim Start ein. 
# RCL Eingänge
RLC‑Inputs können vorgegebene Prozentwerte (config) darstellen und begrenzen so den Strom.

# Test
Testscript set-cc.py erlaubt manuelles Setzen eines Ladestroms (0–32 A).

# LEDs: 
- grün = EVCC aktiv, 
- blau = RLC ON (beide können gleichzeitig leuchten)
# DIP-Schalter:
- DIP1: EVCC / Always-Load (EVCC-Modus vs. immer laden)
- DIP2: RLC-Inputs aktivieren (4 RLC Eingänge)

