# hass-components
Home Assistant custom components

## rflink2
RFLink custom component allowing to use second RFLink module

### Installation
* download or clone repository files
* add to `configuration.yaml`:
    ```
    rflink2:
      port: /dev/ttyACM0
    ```

## ups_pico
### Requirements
* **smbus2** v0.2.0 Python package - should be installed automatically by HA

### Installation
* download or clone repository files
* copy dirs/files to your Home Assistant config directory - for example `/home/homeassistant/.homeassistant` with this structure:
    ```
    └── .homeassistant
        ├── configuration.yaml
        │   (... and the other current files)
        └── custom_components
            ├── switch
            │   └── ups_pico.py
            └── ups_pico.py
    ```
* add to `configuration.yaml`:
    ````
    ups_pico:
    
    switch:
      - platform: ups_pico
    ````
* restart Home Assistant
* you should see entities for sensors and switches like:
    ````
    ups_pico.pwrmode
    ups_pico.voltrpi
    ups_pico.voltbat
    ups_pico.tempntc1
    switch.ups_pico_enabled_leds
    switch.ups_pico_blue_led
    switch.ups_pico_green_led
    switch.ups_pico_orange_led
    ````
* if it doesn't work, look to the log files
