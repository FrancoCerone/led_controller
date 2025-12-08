#!/usr/bin/env python3
"""
Server REST per controllare gli effetti LED della Raspberry Pi
Compatibile con Python 3.7.3
"""

import sys
import os
import socket

from flask import Flask, request, jsonify
from flask_cors import CORS
import time
from neopixel import *
import argparse
import RPi.GPIO as GPIO
from logo_model import Logo
from threading import Thread

# Inizializzazione GPIO
GPIO.setmode(GPIO.BOARD)

# Inizializzazione logo
logo = Logo()

# LED strip configuration
LED_COUNT = logo.get_number_of_leds()
LED_PIN = 18
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 11
LED_INVERT = False
LED_CHANNEL = 0

# Variabili globali
color = Color(255, 0, 0)
blackout = Color(0, 0, 0)
strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
canRunStrip = False

# Inizializzazione strip
parser = argparse.ArgumentParser()
parser.add_argument('-c', '--clear', action='store_true', help='clear the display on exit')
args = parser.parse_args()
strip.begin()

# Inizializzazione Flask
app = Flask(__name__)
CORS(app)  # Permette chiamate CORS dal browser

# Helper class per gestire i LED
class LEDHelper:
    @staticmethod
    def set_color_for_element(element, strip, color_val):
        """Imposta il colore per un elemento (singolo indice o lista)"""
        if type(element) == list:
            for led_index in element:
                strip.setPixelColor(led_index, color_val)
        else:
            strip.setPixelColor(element, color_val)
    
    @staticmethod
    def turn_off_element(element, strip):
        """Spegne un elemento"""
        LEDHelper.set_color_for_element(element, strip, Color(0, 0, 0))
    
    @staticmethod
    def wheel(pos):
        """Genera colori arcobaleno da 0-255"""
        if pos < 85:
            return Color(pos * 3, 255 - pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return Color(255 - pos * 3, 0, pos * 3)
        else:
            pos -= 170
            return Color(0, pos * 3, 255 - pos * 3)

# Nuovi effetti basati sulla struttura Logo
class RainbowCycleRunner(Thread):
    """Effetto arcobaleno ciclico su tutto il logo"""
    def __init__(self):
        Thread.__init__(self)
        self.running = True
    
    def terminate(self):
        self.running = False
    
    def run(self):
        global canRunStrip, color
        iterations = 3
        wait_ms = 20
        
        for j in range(256 * iterations):
            if not canRunStrip:
                break
            for i in range(strip.numPixels()):
                if not canRunStrip:
                    break
                strip.setPixelColor(i, LEDHelper.wheel((int(i * 256 / strip.numPixels()) + j) & 255))
            strip.show()
            time.sleep(wait_ms / 1000.0)

class PulseRunner(Thread):
    """Effetto pulsazione del colore"""
    def __init__(self):
        Thread.__init__(self)
        self.running = True
    
    def terminate(self):
        self.running = False
    
    def run(self):
        global canRunStrip, color, indexToTurnOn
        cycles = 5
        steps = 50
        
        for cycle in range(cycles):
            if not canRunStrip:
                break
            # Fade in
            for step in range(steps):
                if not canRunStrip:
                    break
                brightness = int(255 * (step / steps))
                r = int((color >> 16) & 0xFF) * brightness // 255
                g = int((color >> 8) & 0xFF) * brightness // 255
                b = int(color & 0xFF) * brightness // 255
                pulse_color = Color(b, r, g)
                
                for i in indexToTurnOn:
                    LEDHelper.set_color_for_element(i, strip, pulse_color)
                strip.show()
                time.sleep(0.02)
            
            # Fade out
            for step in range(steps, 0, -1):
                if not canRunStrip:
                    break
                brightness = int(255 * (step / steps))
                r = int((color >> 16) & 0xFF) * brightness // 255
                g = int((color >> 8) & 0xFF) * brightness // 255
                b = int(color & 0xFF) * brightness // 255
                pulse_color = Color(b, r, g)
                
                for i in indexToTurnOn:
                    LEDHelper.set_color_for_element(i, strip, pulse_color)
                strip.show()
                time.sleep(0.02)

class WaveRunner(Thread):
    """Effetto onda che attraversa il logo"""
    def __init__(self):
        Thread.__init__(self)
        self.running = True
    
    def terminate(self):
        self.running = False
    
    def run(self):
        global canRunStrip, color, indexToTurnOn
        cycles = 3
        wave_length = len(indexToTurnOn)
        
        for cycle in range(cycles):
            if not canRunStrip:
                break
            for pos in range(wave_length * 2):
                if not canRunStrip:
                    break
                # Spegni tutto
                for i in range(strip.numPixels()):
                    strip.setPixelColor(i, Color(0, 0, 0))
                
                # Accendi l'onda
                for i, element in enumerate(indexToTurnOn):
                    if not canRunStrip:
                        break
                    distance = abs(i - (pos % wave_length))
                    if distance < 5:
                        brightness = int(255 * (1 - distance / 5))
                        r = int((color >> 16) & 0xFF) * brightness // 255
                        g = int((color >> 8) & 0xFF) * brightness // 255
                        b = int(color & 0xFF) * brightness // 255
                        wave_color = Color(b, r, g)
                        LEDHelper.set_color_for_element(element, strip, wave_color)
                
                strip.show()
                time.sleep(0.05)

class BorderChaseRunner(Thread):
    """Effetto inseguimento sul bordo"""
    def __init__(self):
        Thread.__init__(self)
        self.running = True
    
    def terminate(self):
        self.running = False
    
    def run(self):
        global canRunStrip, color
        border_indices = logo.get_border_index()
        iterations = 10
        
        for iteration in range(iterations):
            if not canRunStrip:
                break
            for i in range(len(border_indices)):
                if not canRunStrip:
                    break
                # Spegni tutto
                for j in range(strip.numPixels()):
                    strip.setPixelColor(j, Color(0, 0, 0))
                
                # Accendi i LED del bordo in sequenza
                for j in range(max(0, i - 3), min(len(border_indices), i + 4)):
                    if not canRunStrip:
                        break
                    brightness = 255 if j == i else 100
                    r = int((color >> 16) & 0xFF) * brightness // 255
                    g = int((color >> 8) & 0xFF) * brightness // 255
                    b = int(color & 0xFF) * brightness // 255
                    chase_color = Color(b, r, g)
                    LEDHelper.set_color_for_element(border_indices[j], strip, chase_color)
                
                strip.show()
                time.sleep(0.1)

class EyesBlinkRunner(Thread):
    """Effetto lampeggio degli occhi"""
    def __init__(self):
        Thread.__init__(self)
        self.running = True
    
    def terminate(self):
        self.running = False
    
    def run(self):
        global canRunStrip, color
        eyes_indices = logo.get_eyes_strips_index()
        blinks = 5
        
        for blink in range(blinks):
            if not canRunStrip:
                break
            # Accendi occhi
            for i in eyes_indices:
                LEDHelper.set_color_for_element(i, strip, color)
            strip.show()
            time.sleep(0.2)
            
            # Spegni occhi
            for i in eyes_indices:
                LEDHelper.turn_off_element(i, strip)
            strip.show()
            time.sleep(0.2)

class ColorWheelRunner(Thread):
    """Rotazione dei colori attraverso tutto lo spettro"""
    def __init__(self):
        Thread.__init__(self)
        self.running = True
    
    def terminate(self):
        self.running = False
    
    def run(self):
        global canRunStrip, indexToTurnOn
        cycles = 2
        
        for cycle in range(cycles):
            if not canRunStrip:
                break
            for j in range(256):
                if not canRunStrip:
                    break
                for i in indexToTurnOn:
                    wheel_color = LEDHelper.wheel((j) & 255)
                    LEDHelper.set_color_for_element(i, strip, wheel_color)
                strip.show()
                time.sleep(0.02)

class FadeInOutRunner(Thread):
    """Fade in e out del colore"""
    def __init__(self):
        Thread.__init__(self)
        self.running = True
    
    def terminate(self):
        self.running = False
    
    def run(self):
        global canRunStrip, color, indexToTurnOn
        cycles = 3
        steps = 100
        
        for cycle in range(cycles):
            if not canRunStrip:
                break
            # Fade in
            for step in range(steps):
                if not canRunStrip:
                    break
                brightness = int(255 * (step / steps))
                r = int((color >> 16) & 0xFF) * brightness // 255
                g = int((color >> 8) & 0xFF) * brightness // 255
                b = int(color & 0xFF) * brightness // 255
                fade_color = Color(b, r, g)
                
                for i in range(strip.numPixels()):
                    strip.setPixelColor(i, Color(0, 0, 0))
                for i in indexToTurnOn:
                    LEDHelper.set_color_for_element(i, strip, fade_color)
                strip.show()
                time.sleep(0.01)
            
            # Fade out
            for step in range(steps, 0, -1):
                if not canRunStrip:
                    break
                brightness = int(255 * (step / steps))
                r = int((color >> 16) & 0xFF) * brightness // 255
                g = int((color >> 8) & 0xFF) * brightness // 255
                b = int(color & 0xFF) * brightness // 255
                fade_color = Color(b, r, g)
                
                for i in range(strip.numPixels()):
                    strip.setPixelColor(i, Color(0, 0, 0))
                for i in indexToTurnOn:
                    LEDHelper.set_color_for_element(i, strip, fade_color)
                strip.show()
                time.sleep(0.01)

# Funzioni helper per gli effetti
def set_color(r, g, b):
    """Imposta il colore globale"""
    global color
    color = Color(int(b), int(r), int(g))
    print(f"Color set to RGB({r}, {g}, {b})")

def turn_on():
    """Accende il logo con il colore corrente"""
    global canRunStrip
    canRunStrip = False  # Ferma eventuali effetti in corso
    time.sleep(0.1)
    
    indexToTurnOn = logo.get_bottom_up_border_leds_index()
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
    
    for i in range(strip.numPixels()):
        LEDHelper.set_color_for_element(i, strip, color)
    strip.show()

def turn_off():
    """Spegne tutti i LED"""
    global canRunStrip
    canRunStrip = False
    time.sleep(0.1)
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()

def flash():
    """Effetto flash"""
    global canRunStrip
    canRunStrip = False
    time.sleep(0.1)
    
    indexToTurnOn = logo.get_bottom_up_border_leds_index()
    for element in indexToTurnOn:
        LEDHelper.set_color_for_element(element, strip, color)
    strip.show()
    time.sleep(0.2)
    
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()

def set_all_leds_on():
    """Accende tutti i LED"""
    global canRunStrip
    canRunStrip = False
    time.sleep(0.1)
    
    indexToTurnOn = logo.get_allSripIndex()
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
    
    for i in indexToTurnOn:
        strip.setPixelColor(i, color)
    strip.show()

def set_border_led_on():
    """Accende il bordo LED"""
    global canRunStrip
    canRunStrip = False
    time.sleep(0.1)
    
    indexToTurnOn = logo.get_border_index()
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
    
    for i in indexToTurnOn:
        strip.setPixelColor(i, color)
    strip.show()

def set_eyes_led_on():
    """Accende solo gli occhi"""
    global canRunStrip
    canRunStrip = False
    time.sleep(0.1)
    
    indexToTurnOn = logo.get_eyes_strips_index()
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
    
    for i in indexToTurnOn:
        strip.setPixelColor(i, color)
    strip.show()

def set_eyes_and_mouth_led_on():
    """Accende occhi e bocca"""
    global canRunStrip
    canRunStrip = False
    time.sleep(0.1)
    
    indexToTurnOn = logo.get_eyes_and_mounth_strips_index()
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
    
    for i in indexToTurnOn:
        strip.setPixelColor(i, color)
    strip.show()

# Nuove funzioni effetti
def rainbow_cycle():
    """Effetto arcobaleno ciclico"""
    global canRunStrip, indexToTurnOn
    canRunStrip = True
    indexToTurnOn = logo.get_allSripIndex()
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
    runner = RainbowCycleRunner()
    runner.start()

def pulse():
    """Effetto pulsazione"""
    global canRunStrip, indexToTurnOn
    canRunStrip = True
    indexToTurnOn = logo.get_bottom_up_border_leds_index()
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
    runner = PulseRunner()
    runner.start()

def wave():
    """Effetto onda"""
    global canRunStrip, indexToTurnOn
    canRunStrip = True
    indexToTurnOn = logo.get_bottom_up_border_leds_index()
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
    runner = WaveRunner()
    runner.start()

def border_chase():
    """Effetto inseguimento sul bordo"""
    global canRunStrip
    canRunStrip = True
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
    runner = BorderChaseRunner()
    runner.start()

def eyes_blink():
    """Effetto lampeggio occhi"""
    global canRunStrip
    canRunStrip = True
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
    runner = EyesBlinkRunner()
    runner.start()

def color_wheel():
    """Rotazione colori"""
    global canRunStrip, indexToTurnOn
    canRunStrip = True
    indexToTurnOn = logo.get_bottom_up_border_leds_index()
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
    runner = ColorWheelRunner()
    runner.start()

def fade_in_out():
    """Fade in e out"""
    global canRunStrip, indexToTurnOn
    canRunStrip = True
    indexToTurnOn = logo.get_bottom_up_border_leds_index()
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
    runner = FadeInOutRunner()
    runner.start()

# Funzione helper per ottenere l'IP locale
def get_local_ip():
    """Ottiene l'IP locale della macchina"""
    try:
        # Crea un socket temporaneo per ottenere l'IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            # Fallback: usa hostname
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            return ip
        except Exception:
            return "127.0.0.1"

# Endpoint REST
@app.route('/server-info', methods=['GET'])
def server_info():
    """Restituisce informazioni sul server incluso l'IP"""
    return jsonify({
        "ip": get_local_ip(),
        "port": 5000,
        "url": f"http://{get_local_ip()}:5000"
    })

@app.route('/', methods=['GET'])
def index():
    """Pagina principale con lista degli endpoint disponibili"""
    endpoints = {
        "endpoints": [
            {"method": "GET/POST", "path": "/turn-on", "description": "Accende il logo"},
            {"method": "GET/POST", "path": "/turn-off", "description": "Spegne tutti i LED"},
            {"method": "GET/POST", "path": "/flash", "description": "Effetto flash"},
            {"method": "GET/POST", "path": "/set-color", "description": "Imposta colore RGB (parametri: r, g, b)"},
            {"method": "GET/POST", "path": "/all-leds-on", "description": "Accende tutti i LED"},
            {"method": "GET/POST", "path": "/border-led-on", "description": "Accende il bordo LED"},
            {"method": "GET/POST", "path": "/eyes-on", "description": "Accende solo gli occhi"},
            {"method": "GET/POST", "path": "/eyes-mouth-on", "description": "Accende occhi e bocca"},
            {"method": "GET/POST", "path": "/rainbow-cycle", "description": "Effetto arcobaleno ciclico"},
            {"method": "GET/POST", "path": "/pulse", "description": "Effetto pulsazione"},
            {"method": "GET/POST", "path": "/wave", "description": "Effetto onda"},
            {"method": "GET/POST", "path": "/border-chase", "description": "Effetto inseguimento sul bordo"},
            {"method": "GET/POST", "path": "/eyes-blink", "description": "Effetto lampeggio occhi"},
            {"method": "GET/POST", "path": "/color-wheel", "description": "Rotazione colori"},
            {"method": "GET/POST", "path": "/fade-in-out", "description": "Fade in e out"},
        ]
    }
    return jsonify(endpoints)

@app.route('/turn-on', methods=['GET', 'POST'])
def api_turn_on():
    """Accende il logo"""
    turn_on()
    return jsonify({"status": "success", "message": "Logo turned on"})

@app.route('/turn-off', methods=['GET', 'POST'])
def api_turn_off():
    """Spegne tutti i LED"""
    turn_off()
    return jsonify({"status": "success", "message": "All LEDs turned off"})

@app.route('/flash', methods=['GET', 'POST'])
def api_flash():
    """Effetto flash"""
    flash()
    return jsonify({"status": "success", "message": "Flash effect executed"})

@app.route('/set-color', methods=['GET', 'POST'])
def api_set_color():
    """Imposta il colore RGB"""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        r = int(data.get('r', 255))
        g = int(data.get('g', 0))
        b = int(data.get('b', 0))
    else:
        r = int(request.args.get('r', 255))
        g = int(request.args.get('g', 0))
        b = int(request.args.get('b', 0))
    
    set_color(r, g, b)
    # Applica il colore al logo
    indexToTurnOn = logo.get_bottom_up_border_leds_index()
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
    for element in indexToTurnOn:
        LEDHelper.set_color_for_element(element, strip, color)
    strip.show()
    
    return jsonify({"status": "success", "message": f"Color set to RGB({r}, {g}, {b})"})

@app.route('/all-leds-on', methods=['GET', 'POST'])
def api_all_leds_on():
    """Accende tutti i LED"""
    set_all_leds_on()
    return jsonify({"status": "success", "message": "All LEDs turned on"})

@app.route('/border-led-on', methods=['GET', 'POST'])
def api_border_led_on():
    """Accende il bordo LED"""
    set_border_led_on()
    return jsonify({"status": "success", "message": "Border LEDs turned on"})

@app.route('/eyes-on', methods=['GET', 'POST'])
def api_eyes_on():
    """Accende solo gli occhi"""
    set_eyes_led_on()
    return jsonify({"status": "success", "message": "Eyes LEDs turned on"})

@app.route('/eyes-mouth-on', methods=['GET', 'POST'])
def api_eyes_mouth_on():
    """Accende occhi e bocca"""
    set_eyes_and_mouth_led_on()
    return jsonify({"status": "success", "message": "Eyes and mouth LEDs turned on"})

@app.route('/rainbow-cycle', methods=['GET', 'POST'])
def api_rainbow_cycle():
    """Effetto arcobaleno ciclico"""
    rainbow_cycle()
    return jsonify({"status": "success", "message": "Rainbow cycle effect started"})

@app.route('/pulse', methods=['GET', 'POST'])
def api_pulse():
    """Effetto pulsazione"""
    pulse()
    return jsonify({"status": "success", "message": "Pulse effect started"})

@app.route('/wave', methods=['GET', 'POST'])
def api_wave():
    """Effetto onda"""
    wave()
    return jsonify({"status": "success", "message": "Wave effect started"})

@app.route('/border-chase', methods=['GET', 'POST'])
def api_border_chase():
    """Effetto inseguimento sul bordo"""
    border_chase()
    return jsonify({"status": "success", "message": "Border chase effect started"})

@app.route('/eyes-blink', methods=['GET', 'POST'])
def api_eyes_blink():
    """Effetto lampeggio occhi"""
    eyes_blink()
    return jsonify({"status": "success", "message": "Eyes blink effect started"})

@app.route('/color-wheel', methods=['GET', 'POST'])
def api_color_wheel():
    """Rotazione colori"""
    color_wheel()
    return jsonify({"status": "success", "message": "Color wheel effect started"})

@app.route('/fade-in-out', methods=['GET', 'POST'])
def api_fade_in_out():
    """Fade in e out"""
    fade_in_out()
    return jsonify({"status": "success", "message": "Fade in-out effect started"})

if __name__ == '__main__':
    print("Inizializzazione LED strip...")
    numpixel = strip.numPixels()
    
    # Spegni tutti i LED
    print("Spegnimento di tutti i LED...")
    for i in range(numpixel):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
    time.sleep(0.5)
    
    # Effetto debug: accendi 10 LED alla volta lentamente
    print("Test LED: accensione 10 LED alla volta...")
    test_color = Color(0, 255, 0)  # Verde per il test
    leds_per_group = 10
    delay = 0.3  # 300ms tra ogni gruppo (molto lento)
    
    for start_idx in range(0, numpixel, leds_per_group):
        # Accendi il gruppo corrente
        for i in range(start_idx, min(start_idx + leds_per_group, numpixel)):
            strip.setPixelColor(i, test_color)
        strip.show()
        print(f"LED {start_idx} - {min(start_idx + leds_per_group - 1, numpixel - 1)} accesi")
        time.sleep(delay)
        
        # Spegni il gruppo corrente
        for i in range(start_idx, min(start_idx + leds_per_group, numpixel)):
            strip.setPixelColor(i, Color(0, 0, 0))
        strip.show()
        time.sleep(0.1)
    
    # Accendi tutti i LED alla fine
    print("Test completato. Accensione di tutti i LED...")
    for i in range(numpixel):
        strip.setPixelColor(i, color)
    strip.show()
    time.sleep(0.5)
    
    print("Server REST LED avviato!")
    print("Accessibile su http://0.0.0.0:5000")
    print("Vedi http://0.0.0.0:5000/ per la lista degli endpoint")
    
    # Avvia il server Flask
    app.run(host='0.0.0.0', port=5000, debug=False)
