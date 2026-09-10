"""Local-only Windows controls. No game input occurs until an explicit Start."""
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT = Path(__file__).resolve().parent
ORIGIN = 'http://127.0.0.1:8784'
HOST = '127.0.0.1:8784'


def validate_command(body):
    if not isinstance(body, dict) or set(body) != {'mode', 'key', 'interval'}:
        raise ValueError('Invalid helper command.')
    if body['mode'] not in ('repeat', 'fishing') or body['key'] not in ('e', 'right'):
        raise ValueError('Unsupported helper or action.')
    interval = body['interval']
    if isinstance(interval, bool) or not isinstance(interval, (int, float)) or not math.isfinite(interval) or not .2 <= interval <= 60:
        raise ValueError('Interval must be between 0.2 and 60 seconds.')
    return body


class Controller:
    def __init__(self):
        self.lock = threading.Lock()
        self.event = threading.Event()
        self.worker = None
        self.child = None
        self.message = 'Stopped'

    def running(self):
        return bool((self.worker and self.worker.is_alive()) or (self.child and self.child.poll() is None))

    def status(self):
        with self.lock:
            active = self.running()
            if not active and self.message.startswith(('Starting', 'Running', 'Paused')):
                self.message = 'Stopped'
            return {'running': active, 'message': self.message}

    def start(self, body):
        body = validate_command(body)
        if sys.platform != 'win32':
            raise ValueError('Game automation requires Windows. The item planner works on any supported browser.')
        with self.lock:
            if self.running():
                raise ValueError('Stop the active helper first.')
            if body['mode'] == 'fishing':
                self.child = subprocess.Popen([sys.executable, str(ROOT / 'fishing.py')], cwd=ROOT)
                self.message = 'Running fishing helper · F8 pauses · Esc stops'
                return
            # Import native input libraries only for an explicitly requested Windows run.
            import keyboard
            import pyautogui
            import pygetwindow as gw
            self.event = threading.Event()
            self.message = 'Starting in 3 seconds · switch to Warcraft'
            self.worker = threading.Thread(target=self.repeat, args=(body, keyboard, pyautogui, gw), daemon=True)
            self.worker.start()

    def repeat(self, body, keyboard, mouse, windows):
        try:
            if self.event.wait(3): return
            while not self.event.is_set():
                if keyboard.is_pressed('esc'): break
                win = windows.getActiveWindow()
                if not win or 'warcraft' not in win.title.lower():
                    self.message = 'Paused · bring Warcraft to the foreground'
                    self.event.wait(.1)
                    continue
                self.message = 'Running · Esc or Stop ends the helper'
                if body['key'] == 'right':
                    mouse.press('f1', presses=2, interval=.03)
                    if self.event.wait(.1): break
                    win = windows.getActiveWindow()
                    if win and 'warcraft' in win.title.lower(): mouse.click(button='right')
                else:
                    mouse.press('e')
                deadline = time.monotonic() + body['interval']
                while time.monotonic() < deadline and not self.event.wait(min(.05, max(0, deadline-time.monotonic()))):
                    if keyboard.is_pressed('esc'):
                        self.event.set()
                        break
        except Exception:
            self.message = 'Stopped · input helper error; check the terminal and game window'
            return
        finally:
            if not self.message.startswith('Stopped ·'): self.message = 'Stopped'

    def stop(self):
        with self.lock:
            self.event.set()
            if self.child and self.child.poll() is None:
                self.child.terminate()
                try: self.child.wait(timeout=2)
                except subprocess.TimeoutExpired: self.child.kill()
            if self.worker: self.worker.join(timeout=2)
            self.message = 'Stopped'


class Handler(SimpleHTTPRequestHandler):
    controller = Controller()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'web'), **kwargs)

    def log_message(self, *_): pass

    def reply(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.headers.get('Host') != HOST:
            return self.reply(403, {'error': 'Local host required.'})
        if self.path == '/api/status': return self.reply(200, self.controller.status())
        if self.path.startswith('/api/'): return self.reply(404, {'error': 'Unknown endpoint.'})
        return super().do_GET()

    def do_POST(self):
        # No CORS. Exact Host blocks DNS rebinding; exact Origin + JSON blocks
        # cross-site forms and requests from public websites to local controls.
        if self.headers.get('Host') != HOST or self.headers.get('Origin') != ORIGIN:
            return self.reply(403, {'error': 'Use this companion’s own local dashboard.'})
        if self.headers.get('Content-Type') != 'application/json':
            return self.reply(415, {'error': 'JSON required.'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 1024: raise ValueError('Invalid request size.')
            body = json.loads(self.rfile.read(size))
            if self.path == '/api/start': self.controller.start(body)
            elif self.path == '/api/stop' and body == {}: self.controller.stop()
            else: return self.reply(404, {'error': 'Unknown command.'})
            return self.reply(200, self.controller.status())
        except (ValueError, TypeError):
            return self.reply(400, {'error': 'Invalid command, platform or interval. Stop any active helper before starting.'})
        except Exception:
            return self.reply(500, {'error': 'Could not start the helper. Check installed dependencies and the terminal.'})


def main():
    if sys.platform != 'win32':
        raise SystemExit('The local input companion requires Windows. Use the public item planner on this computer.')
    server = ThreadingHTTPServer(('127.0.0.1', 8784), Handler)
    print('teet local controls: ' + ORIGIN + '/#automation', flush=True)
    import webbrowser
    webbrowser.open(ORIGIN + '/#automation')
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally:
        Handler.controller.stop()
        server.server_close()

if __name__ == '__main__': main()
