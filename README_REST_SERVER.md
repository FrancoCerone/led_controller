# Server REST per Controllo LED

Server REST semplice per controllare gli effetti LED della Raspberry Pi tramite chiamate HTTP da browser.

## Installazione

1. Installa le dipendenze:
```bash
pip3 install -r requirements.txt
```

## Avvio del Server

```bash
python3 led_rest_server.py
```

Il server sarà accessibile su `http://0.0.0.0:5000` (e quindi anche dall'IP della Raspberry Pi sulla porta 5000).

## Endpoint Disponibili

Tutti gli endpoint supportano sia GET che POST e non richiedono autenticazione.

### Effetti Base
- `GET /turn-on` - Accende il logo
- `GET /turn-off` - Spegne tutti i LED
- `GET /flash` - Effetto flash

### Impostazione Colore
- `GET /set-color?r=255&g=0&b=0` - Imposta il colore RGB (valori 0-255)

### Zone LED
- `GET /all-leds-on` - Accende tutti i LED
- `GET /border-led-on` - Accende il bordo LED
- `GET /border-eyes-mouth-on` - Accende bordo, occhi e bocca
- `GET /eyes-on` - Accende solo gli occhi
- `GET /eyes-mouth-on` - Accende occhi e bocca

### Effetti Animati
- `GET /incremental-wipe` - Effetto wipe incrementale
- `GET /down-up-down` - Effetto su-giù-su
- `GET /theater-chase` - Effetto theater chase
- `GET /bottom-up-curten` - Effetto tenda dal basso
- `GET /top-down-curten` - Effetto tenda dall'alto

## Esempi di Utilizzo

### Dal Browser
Apri semplicemente l'URL nel browser:
```
http://172.20.10.4:5000/turn-on
http://172.20.10.4:5000/set-color?r=255&g=0&b=255
http://172.20.10.4:5000/theater-chase
```

### Con cURL
```bash
curl http://172.20.10.4:5000/turn-on
curl http://172.20.10.4:5000/set-color?r=255&g=0&b=0
curl http://172.20.10.4:5000/flash
```

### Con JavaScript (fetch)
```javascript
fetch('http://172.20.10.4:5000/turn-on')
fetch('http://172.20.10.4:5000/set-color?r=255&g=0&b=255')
```

## File HTML di Test

Apri `test_led_controls.html` nel browser dopo aver modificato l'indirizzo IP nella variabile `API_BASE_URL` con l'IP della tua Raspberry Pi.

## Note

- Il server è configurato per accettare connessioni da qualsiasi indirizzo IP (0.0.0.0)
- Non c'è autenticazione per semplicità
- Compatibile con Python 3.7.3
- Assicurati che la porta 5000 sia aperta nel firewall se necessario

