---
name: brave-auth-agent
description: Reuse a logged-in Brave session (X, Gmail, Reddit, etc) from agent/cron jobs via a persistent Chromium user-data-dir. Use when the user wants the agent to act on authenticated sites without re-logging in every time, or to monitor an authenticated feed.
version: 1.0
author: diegovelezg
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [browser, auth, persistent-context, brave, cdp, x, gmail, reddit, scraping]
    related_skills: [product-price-monitor, blogwatcher, competitor-news-monitor]
---

# Brave Auth Agent — Persistent Logged-In Browser

Run a long-lived Chromium-based browser (Brave) with a dedicated persistent profile so the agent inherits the user's already-logged-in sessions on sites like X, Gmail, Reddit. Connect via CDP and drive the page through `Runtime.evaluate` / `Page.*` methods. Designed for cron jobs and ad-hoc automation.

## When to Use

- "Watch r/algotrading top of the week and summarize it every Monday."
- "Post a thread to X from my account every morning."
- "Read my Gmail inbox and notify me on important emails."
- "Extract my X bookmarks into a JSON file."
- Any flow that requires a logged-in session and should survive without manual login.

Do NOT use for: one-off public pages (use `web_search` / `web_extract`), sites that require no auth, or scraping at scale where login state isn't needed.

## Critical Rule: Profile Separation

**NEVER touch `~/.config/BraveSoftware/Brave-Origin/` or any other Brave process not started by this skill.** That is the user's personal browser with their personal sessions. Touching it = angry user + broken cookies.

The skill operates ONLY on:
- Profile dir: `~/.hermes/browser-data/agent/` (default)
- PID file: `/tmp/hermes-brave-x.pid`

To stop the agent's Brave instance, ALWAYS use `hermes-brave-x stop`. Never `pkill -f brave-origin`, never `pkill -f remote-debugging-port`. Those patterns will close the user's personal browser.

## Prerequisites (one-time setup)

1. **Brave installed** — verify with `which brave-origin`. On Arch the binary lives at `/usr/sbin/brave-origin` (a bash wrapper that calls `/opt/brave-origin-bin/brave`).
2. **Profile dir created** — `mkdir -p ~/.hermes/browser-data/agent` (the wrapper does this automatically).
3. **Wrapper installed** — copy `assets/hermes-brave-x` to `~/.local/bin/` and `chmod +x`. The asset is already shipped with the skill.
4. **Python websocket-client** — needed to talk to the CDP endpoint. The hermes venv already has it after `pip install websocket-client`. If you use the agent's own python: `/home/diegovelezg/.hermes/hermes-agent/venv/bin/pip install websocket-client`.

## First Login (one-time, per site)

For each site the agent needs to access as the user (X, Gmail, Reddit, etc), log in once manually:

```bash
# 1. Launch headed Brave with the agent profile
hermes-brave-x login
# A normal Brave window opens using ~/.hermes/browser-data/agent/

# 2. In that window, navigate to the site and log in (X, Gmail, Reddit, etc)
# 3. Close the window normally
```

After this, those sessions persist in the profile dir and the agent can reuse them headless or headed without ever asking the user to log in again.

## Procedure (each agent run)

### 1. Launch the browser

Choose headed or headless:

- **Headed (recommended when interacting with anti-bot sites)** — a real window appears, no fake headless fingerprint:

  ```bash
  hermes-brave-x headed "https://x.com/home"
  ```

- **Headless (cheaper, cold-start ~3-5s, may be blocked by some sites like Reddit)**:

  ```bash
  hermes-brave-x start "https://x.com/home"
  ```

The wrapper:

- Cleans orphan `SingletonLock` files in the profile dir (so a previous manual login doesn't block the new launch).
- Launches Brave with `--remote-debugging-port=$PORT` (default 9222), `--remote-debugging-address=127.0.0.1`.
- Writes its own PID to `/tmp/hermes-brave-x.pid` so `stop` knows exactly which process to kill.

### 2. Find the target tab

The wrapper opens one tab pointed at the URL. If you need a different tab (e.g. user already had multiple tabs from a previous run), list them:

```bash
curl -sf http://127.0.0.1:9222/json | python3 -c "
import json, sys
for t in json.load(sys.stdin):
    print(t.get('id'), '|', t.get('title',''), '|', t.get('url',''))
"
```

### 3. Connect via CDP and drive the page

Use `websocket-client` (NOT `terminal` — this is a Python call, not a shell command). **Critical: do NOT send an `Origin` header.** When websocket-client sends no header, chromium accepts the connection. Any explicit `Origin` (even `Origin: null` or `Origin: http://127.0.0.1:9222`) makes chromium concatenate `host+origin` and reject with 403 — see Pitfalls.

```python
import json, websocket, time

# 1. Get the tab
import urllib.request
tabs = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json").read())
tab = next(t for t in tabs if "x.com" in t["url"])

# 2. Connect — NO header= argument
ws = websocket.create_connection(tab["webSocketDebuggerUrl"], timeout=15)

# 3. Send CDP commands
msg_id = 0
def call(method, params=None):
    global msg_id
    msg_id += 1
    ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
    while True:
        resp = json.loads(ws.recv())
        if resp.get("id") == msg_id:
            return resp

call("Page.enable")
call("Runtime.enable")

# 4. Inject and run JS in the page context
js = "JSON.stringify({title: document.title, url: location.href, html: document.body.innerText.length})"
result = call("Runtime.evaluate", {"expression": js, "returnByValue": True})
print(json.loads(result["result"]["result"]["value"]))

ws.close()
```

### 4. Site-specific extraction recipes

#### X / Twitter

- Login URL: `https://x.com/login` (or just navigate to `/home`)
- Tab title after auth: `Inicio / X` (Spanish locale) or `Home / X`
- Top of timeline selector: `[data-testid="primaryColumn"] [data-testid="tweet"]`
- Per-tweet attributes: `tabindex="0"` divs inside `[data-testid="primaryColumn"]`
- Avoid the `aria-label="Timeline: Trending now"` column.

#### Reddit

- Login URL: `https://www.reddit.com/login`
- Top of week URL: `https://www.reddit.com/r/<sub>/top/?t=week`
- The page uses **Shadow DOM** — extract with `document.querySelectorAll('shreddit-app shreddit-post')`
- Each post exposes attributes: `post-title`, `score`, `comment-count`, `author`, `permalink`, `post-flair-text`
- **IMPORTANT**: Reddit blocks headless Chromium with "You've been blocked by network security". Use `hermes-brave-x headed` (not `start`) when targeting Reddit.

#### Gmail

- URL: `https://mail.google.com/mail/u/0/#inbox`
- Title includes the count: `Recibidos (14) - <email> - Gmail`
- Inbox row selector: `tr.zA` (older) or `[data-legacy-thread-id]` (newer)
- Body extract via the `view-source` URL or via `Page.printToPDF` for a clean dump.

### 5. Stop the browser

```bash
hermes-brave-x stop
# kills ONLY the PID recorded in /tmp/hermes-brave-x.pid
```

Verify it's down: `hermes-brave-x status` prints `not running`.

## Wrapper Subcommands

```text
hermes-brave-x login [URL]              # headed, manual login session
hermes-brave-x headed URL               # headed + CDP (recommended)
hermes-brave-x start URL                # headless + CDP (faster but blocks on some sites)
hermes-brave-x cdp                      # print the websocket CDP URL
hermes-brave-x stop                     # kill ONLY the agent's instance
hermes-brave-x status                   # is it running?
```

Environment overrides:

- `HERMES_BRAVE_PROFILE` — change profile dir (default `~/.hermes/browser-data/agent`)
- `HERMES_BRAVE_PORT` — change CDP port (default `9222`)
- `HERMES_BRAVE_BIN` — override binary path

## Pitfalls

- **Sending `Origin` header in websocket = 403.** Chromium concatenates the request host + the Origin value, e.g. `http://127.0.0.1:9222,http://127.0.0.1:9222`. Even `--remote-allow-origins=*` does NOT match this. Solution: omit the `header=` argument entirely from `websocket.create_connection`.

- **`SingletonLock` leftover from manual login.** When you log in with `hermes-brave-x login` and just close the window, Chrome may leave a `SingletonLock` symlink. Subsequent `start` / `headed` calls refuse to launch. The wrapper cleans these automatically before launch, but if you ever see "Failed to create a ProcessSingleton", just `rm` them:
  ```bash
  rm -f ~/.hermes/browser-data/agent/Singleton{Lock,Cookie,Socket}
  ```

- **Reddit blocks headless.** Use `hermes-brave-x headed` for Reddit (and most anti-bot-protected sites). The headless UA is well-known and instantly banned.

- **Multiple Brave instances on the same port.** If you see a stale headless running on 9222, do NOT use `pkill`. Identify its PID via `pgrep -af "remote-debugging-port=9222"` (the user's personal Brave won't match this pattern) and `kill -9 <pid>` only the agent's process.

- **Two browser contexts running concurrently.** The user's personal Brave and the agent's Brave each have their own `user-data-dir`, so they're isolated. But if you ever point both at the same dir, the second launch fails with `SingletonLock`.

- **`web_search` won't read your authenticated feed.** It crawls public web. For your private timeline / inbox, this skill is the only way.

## Cron Integration

A typical cron job that scrapes Reddit once a day:

```text
cronjob(action="create",
        schedule="0 9 * * 1",     # Mondays 9am
        prompt="Load the brave-auth-agent skill. Run hermes-brave-x headed to open https://www.reddit.com/r/algotrading/top/?t=week. Use Runtime.evaluate to extract the top 25 posts (shreddit-post selector, attributes post-title, score, comment-count, author, permalink). Save the result as JSON to ~/jobs/reddit-algotrading-top.json. Stop the browser with hermes-brave-x stop. Reply with a one-paragraph summary.",
        deliver="origin")
```

## Verification

- [ ] `hermes-brave-x status` returns `not running` after a clean stop.
- [ ] A headed `hermes-brave-x login` opens a window that shows the user's already-logged-in sites (X home, Gmail inbox, etc).
- [ ] Headless `start` works for sites with weak anti-bot (X is OK, Reddit is not).
- [ ] After a successful extraction, the user's personal Brave in `~/.config/BraveSoftware/Brave-Origin/` is untouched and still logged in.
- [ ] CDP connection succeeds WITHOUT setting `Origin` header in `websocket.create_connection`.

## Files

- `assets/hermes-brave-x` — the wrapper script. Symlink or copy to `~/.local/bin/` (recommended install).
- `assets/test-brave-x-auth.sh` — round-trip auth test (launches headed, lists tabs, prints URL+title, stops).
