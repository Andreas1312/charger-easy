# Juice Booster (Juice Charger Easy) — EVCC / MQTT Integration  

## Deutsch  

Dieses Repository enthält die Software, um die ursprüngliche Steuerung des **Juice Booster (Juice CHARGER Easy)** vollständig zu ersetzen und die Integration in **EVCC** über **MQTT** zu ermöglichen.  

⚠️ **Wichtig: Dieses Projekt verändert das Ladeverhalten des Juice Booster.**  

### Funktionen  

- Ersetzt die originale Juice Booster Ansteuerung im Juice CHARGER Easy.  
- Stellt Steuerung über MQTT bereit (Integration in EVCC).  
- Priorisierung: Hardware-RLC-Eingänge haben, wenn aktiv, Vorrang vor EVCC-Steuerung.  

### Funktion des JCeasy HAT  

- **CP-Zustand (A, B, C, E, F)** wird per GPIO gelesen (PIC12F1572-E für CP-Auswertung).  
  - Zustand A: Fahrzeug nicht angeschlossen und nicht ladebereit  
  - Zustand B: Fahrzeug angeschlossen, aber nicht ladebereit  
  - Zustand C: Fahrzeug angeschlossen und ladebereit  
  - Zustand E: Fehlerzustand — Juice Booster nicht mit dem Charger Easy verbunden  
    (Nach erneuter Verbindung muss der Charger Easy vom Strom getrennt und neu gestartet werden)  
  - Zustand F: Allgemeiner Fehlerzustand  

- **Ladestromregelung** über MCP4161-103E:  
  - Beim ersten Start wird im EEPROM-Register (0x20) ein „Maximalstrom“ als Hardware-Fallback gespeichert.  
  - Für den laufenden Betrieb wird das RAM-Register 0x00 verwendet (volatile Pot-Wert).  

- **DIP-Schalter, Codierschalter und RLC-Eingänge** werden beim Start eingelesen.  
- Unterstützte Ströme: 6A, 8A, 10A, 13A, 16A, 20A, 25A, 32A.  
  (Eine feinere Ansteuerung ist eventuell möglich.)  

### RLC Eingänge  

RLC-Inputs können prozentuale Begrenzungen darstellen (per config). Reihenfolge von oben nach unten:  
- RLC 1  
- RLC 2  
- RLC 3  
- RLC 4  

### LEDs  

- LEDs können in der config deaktiviert werden.  
- grün = EVCC aktiv  
- blau = RLC-Eingang ist aktiv  

### DIP-Schalter  

- **DIP1**: EVCC / FreeCharge  
  - ON → FreeCharge  
  - OFF → EVCC-Modus  
- **DIP2**: RLC-Inputs aktivieren (4 Eingänge)  
  - ON → RLC-Inputs aktiv  
  - OFF → keine Reduzierung durch RLC-Inputs  

### EVCC  

- Beispielkonfiguration: `evcc.yaml`  
- Die Steuerung über Ampere wird auf die Juice Booster Werte gemappt.  
- Feinere Ansteuerung in Arbeit.  

### Test  

- `set-cc.py` erlaubt manuelles Setzen des Ladestroms (0–32 A).  

### ToDo  

- RFID-Integration  
- mA-Regelung  

---

## English  

This repository contains the software to **fully replace the original control logic of the Juice Booster (Juice CHARGER Easy)** and to enable integration into **EVCC** via **MQTT**.  

⚠️ **Important: This project modifies the charging behavior of the Juice Booster.**  

### Features  

- Replaces the original Juice Booster control inside the Juice CHARGER Easy.  
- Provides MQTT control (integration into EVCC).  
- Priority: Hardware RLC inputs take precedence over EVCC control when active.  

### JCeasy HAT Function  

- **CP state (A, B, C, E, F)** is read via GPIO (PIC12F1572-E for CP evaluation).  
  - State A: Vehicle not connected and not ready to charge  
  - State B: Vehicle connected, not ready to charge  
  - State C: Vehicle connected and ready to charge  
  - State E: Error — Juice Booster not connected to Charger Easy  
    (After reconnection, Charger Easy must be power-cycled)  
  - State F: General error  

- **Charging current control** via MCP4161-103E:  
  - On first startup, the EEPROM register (0x20) is written with a “maximum current” as hardware fallback.  
  - During runtime, the RAM register 0x00 is used (volatile pot value).  

- **DIP switches, coding switches, and RLC inputs** are read at startup.  
- Supported currents: 6A, 8A, 10A, 13A, 16A, 20A, 25A, 32A.  
  (Finer adjustment may be possible.)  

### RLC Inputs  

RLC inputs can represent predefined percentages (configured in `config`). Order from top to bottom:  
- RLC 1  
- RLC 2  
- RLC 3  
- RLC 4  

### LEDs  

- LEDs can be disabled via config.  
- green = EVCC active  
- blue = RLC input active  

### DIP Switches  

- **DIP1**: EVCC / FreeCharge  
  - ON → FreeCharge  
  - OFF → EVCC mode  
- **DIP2**: Enable RLC inputs (4 inputs)  
  - ON → RLC inputs active  
  - OFF → no current reduction via RLC inputs  

### EVCC  

- Example configuration: `evcc.yaml`  
- Current control is mapped to Juice Booster supported values.  
- Finer adjustment is in progress.  

### Test  

- `set-cc.py` allows manual setting of charging current (0–32 A).  

### ToDo  

- RFID integration  
- mA regulation  

---

## Rechtlicher Hinweis / Legal Notice  

Alle verwendeten Produkt- und Markennamen sind Eigentum der jeweiligen Inhaber.  
Die Nennung dient ausschließlich Informationszwecken und bedeutet keine  
Verbindung oder Unterstützung durch die genannten Unternehmen.  
Dieses Projekt steht in keinerlei offizieller Beziehung zur **Juice Technology AG**.  

All product and brand names mentioned are the property of their respective owners.  
The naming is for informational purposes only and does not imply any  
connection or endorsement by the mentioned companies.  
This project is in no way affiliated with **Juice Technology AG**.  

---

## Haftungsausschluss / Disclaimer  

**Ich übernehme keine Haftung für eventuelle Softwarefehler sowie daraus resultierende Überlastungen oder Defekte an der verwendeten Hardware (z. B. Juice Booster) und/oder der Hausinstallation. Dies gilt insbesondere im Zusammenhang mit der Begrenzung der maximalen Ladeleistung. Die Nutzung der bereitgestellten Software erfolgt auf eigene Gefahr.**  

**I assume no liability for any software errors and any resulting overloads or damage to the hardware used (e.g. Juice Booster) and/or the house installation. This applies in particular in connection with the limitation of maximum charging power. The use of the provided software is at your own risk.**  
