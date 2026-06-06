---
name: diego-chrome-remote-control
description: Controla el navegador Chrome de Diego de forma remota via CDP (Chrome DevTools Protocol) sobre un tunnel SSH reverso. Úsalo cuando Diego active el tunnel SSH y solicite navegación, clicks, ingreso de texto o extracción de contenido desde su browser real (no headless).
version: 1.0.0
metadata:
  hermes:
    tags: [chrome, cdp, remote-control, browser, ssh-tunnel, web-automation]
    category: productivity
---

# Chrome Remote Control

## Objetivo

Controlar el navegador Chrome de Diego de forma remota usando el **Chrome DevTools Protocol (CDP)** via WebSocket. El browser es su Chrome real, visible en su pantalla — no es headless. Esto evita problemas de detección de bots.

## Arquitectura

```
Diego (local Chrome + puerto 9222) 
    ← SSH reverse tunnel (puerto 3000 en VPS)
    → CDP WebSocket 
    → Playwright/websockets en el VPS 
    → commands
```

**Importante:** El tunnel SSH lo inicia Diego manualmente desde su compu. El VPS solo recibe la conexión CDP.

## Paso 1: Activar el tunnel (Diego ejecuta)

Diego ejecuta en su terminal local:

```bash
ssh -R 0.0.0.0:3000:localhost:9222 root@46.225.4.40 -p 22
```

- Puerto 3000 ya está abierto en el firewall del VPS
- Una vez conectado, avisar al agente "tunnel activo"

## Paso 2: Obtener el WebSocket URL

Antes de ejecutar comandos, obtener la lista de pages/targets disponibles:

```bash
curl -s http://46.225.4.40:3000/json
```

Elegir el `webSocketDebuggerUrl` de la página desired (tipo "page", no "iframe" ni "service_worker").

## Paso 3: Scripts CDP

Usar Python con la librería `websockets` (ya instalada en el VPS).

### Navegar a una URL

```python
python3 << 'EOF'
import asyncio, json
import websockets

async def cdp_send(ws_url, method, params=None, id=1):
    async with websockets.connect(ws_url) as ws:
        msg = json.dumps({"id": id, "method": method, "params": params or {}})
        await ws.send(msg)
        resp = await ws.recv()
        return json.loads(resp)

async def navigate(url):
    ws_url = "ws://46.225.4.40:3000/devtools/page/7A7DE261E36E509888211A5CF3008766"
    result = await cdp_send(ws_url, "Page.navigate", {"url": url})
    print(f"Nav result: {result}")
    # Wait for page load
    await asyncio.sleep(2)

asyncio.run(navigate("https://example.com"))
EOF
```

### Click en un elemento

```python
async def click(selector):
    ws_url = "ws://46.225.4.40:3000/devtools/page/7A7DE261E36E509888211A5CF3008766"
    # First find the element
    result = await cdp_send(ws_url, "Runtime.evaluate", {
        "expression": f'document.querySelector("{selector}").click()'
    })
    print(result)
```

### Escribir texto en un campo

```python
async def type_text(selector, text):
    ws_url = "ws://46.225.4.40:3000/devtools/page/7A7DE261E36E509888211A5CF3008766"
    # Focus + type
    await cdp_send(ws_url, "Runtime.evaluate", {
        "expression": f'document.querySelector("{selector}").focus()'
    })
    await cdp_send(ws_url, "Input.insertText", {"text": text})
```

### Tomar screenshot

```python
async def screenshot():
    ws_url = "ws://46.225.4.40:3000/devtools/page/7A7DE261E36E509888211A5CF3008766"
    # Enable screenshot domain
    await cdp_send(ws_url, "Page.enable")
    # Capture screenshot
    result = await cdp_send(ws_url, "Page.captureScreenshot", {"format": "png"})
    import base64
    data = base64.b64decode(result['result']['data'])
    with open("/tmp/chrome-screenshot.png", "wb") as f:
        f.write(data)
    print("Screenshot saved: /tmp/chrome-screenshot.png")
```

### Obtener contenido de texto

```python
async def get_text(selector):
    ws_url = "ws://46.225.4.40:3000/devtools/page/7A7DE261E36E509888211A5CF3008766"
    result = await cdp_send(ws_url, "Runtime.evaluate", {
        "expression": f'document.querySelector("{selector}").innerText'
    })
    print(result['result']['result']['value'])
```

## Funciones helper completas

```python
import asyncio, json, base64
import websockets

CDP_URL = "ws://46.225.4.40:3000/devtools/page/7A7DE261E36E509888211A5CF3008766"

async def cdp_send(method, params=None, id=1):
    async with websockets.connect(CDP_URL) as ws:
        await ws.send(json.dumps({"id": id, "method": method, "params": params or {}}))
        return json.loads(await ws.recv())

async def navigate(url):
    await cdp_send("Page.navigate", {"url": url})
    await asyncio.sleep(2)

async def click(selector):
    await cdp_send("Runtime.evaluate", {"expression": f'document.querySelector("{selector}").click()'})

async def type_text(selector, text):
    await cdp_send("Runtime.evaluate", {"expression": f'document.querySelector("{selector}").focus()'})
    await cdp_send("Input.insertText", {"text": text})

async def get_text(selector):
    r = await cdp_send("Runtime.evaluate", {"expression": f'document.querySelector("{selector}").innerText'})
    return r['result']['result']['value']

async def screenshot(path="/tmp/chrome-screenshot.png"):
    await cdp_send("Page.enable")
    r = await cdp_send("Page.captureScreenshot", {"format": "png"})
    with open(path, "wb") as f:
        f.write(base64.b64decode(r['result']['data']))
    return path

# Uso:
# asyncio.run(navigate("https://reddit.com"))
# asyncio.run(click("button.submit"))
# asyncio.run(screenshot())
```

## Notas

- `websockets` ya está instalado (`python3 -m pip install websockets`)
- El Page ID puede cambiar — siempre verificar con `curl -s http://46.225.4.40:3000/json`
- Los comandos son síncronos por página — si Diego cambia de tab, el Page ID cambia
- `asyncio.sleep(2)` después de `navigate` para esperar que cargue la página
- Para errores: wrapear en try/except y mostrar `resp['error']` si existe