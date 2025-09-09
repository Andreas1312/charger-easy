## Charging Current Control for MCP4161 Digital Potentiometer    

Charging Current Control for MCP4161 Digital Potentiometer
This project provides a simple Python script to temporarily control the maximum charging current via an MCP4161-103E digital potentiometer's RAM register. Unlike a physical potentiometer on a HAT board, this method allows you to bypass hardware limitations and set a current higher than the physically set value.

⚠️ Warning
This script directly writes values to the digital potentiometer's register and has no built-in current limitation. Exercise caution as you can set the charging current higher than intended.

run `sudo python3 set-cc.py `
