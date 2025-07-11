from flask import Flask, send_from_directory, request, redirect
from flask_socketio import SocketIO, emit
import pyautogui
import keyboard
import base64

app = Flask(__name__, static_folder='static')
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Hardcoded Auth ---
try:
    from credentials import USERNAME, PASSWORD
except ImportError:
    USERNAME = input("Enter username: ")
    PASSWORD = input("Enter password: ")

VALID_AUTH = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()

MEDIA_CONTROLS = {
    "previous": "previoustrack",
    "play_pause": "playpause",
    "next": "nexttrack",
    "volume_down": "volumedown",
    "volume_up": "volumeup",
    "mute": "volumemute",
    "sleep": ""  # Optional
}

# --- Auth Helpers ---
def is_authenticated():
    auth_cookie = request.cookies.get('auth', '')
    return auth_cookie == VALID_AUTH

def socket_authenticated():
    cookie_str = request.headers.get('Cookie', '')
    for cookie in cookie_str.split(';'):
        if cookie.strip().startswith('auth='):
            auth = cookie.strip().split('=', 1)[1]
            return auth == VALID_AUTH
    return False

# --- Routes ---
@app.route('/')
def root():
    if not is_authenticated():
        return redirect('/index.html')
    return redirect('/control.html')

@app.route('/<path:filename>')
def serve_html_file(filename):
    if filename == "control.html" and not is_authenticated():
        return redirect('/index.html')
    return send_from_directory('static/pages', filename)

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

# --- SocketIO Events ---
@socketio.on('connect')
def handle_connect():
    if not socket_authenticated():
        print("❌ Unauthorized Socket.IO connection attempt")
        return False  # Disconnects socket
    print("✅ Client connected")
    emit('heartbeat', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    print("Client disconnected")

@socketio.on('heartbeat')
def handle_heartbeat(data):
    if not socket_authenticated():
        return
    print("Heartbeat received:", data)
    emit('heartbeat', {'status': 'alive'})

@socketio.on('media_control')
def handle_media_control(data):
    if not socket_authenticated():
        return
    command = data.get('command')
    key = MEDIA_CONTROLS.get(command)
    print(f"[MEDIA] {command} → key: {key}")
    if key:
        try:
            pyautogui.press(key)
        except Exception as e:
            print(f"⚠️ Failed to send media key: {e}")

@socketio.on('mouse_click')
def handle_mouse_click(data):
    if not socket_authenticated():
        return
    action = data.get('action')
    print(f"[MOUSE CLICK] {action}")
    if action == "left_click":
        pyautogui.click(button='left')
    elif action == "right_click":
        pyautogui.click(button='right')

@socketio.on('keyboard_event')
def handle_keyboard_event(data):
    if not socket_authenticated():
        return
    ktype = data.get('type')
    key = data.get('key')
    code = data.get('code')
    print(f"[KEYBOARD] {ktype.upper()} → {key} ({code})")
    try:
        if ktype == "keydown":
            keyboard.press(key)
        elif ktype == "keyup":
            keyboard.release(key)
    except Exception as e:
        print(f"⚠️ Keyboard event error: {e}")

@socketio.on('keyboard_type')
def handle_keyboard_type(data):
    if not socket_authenticated():
        return

    key = data.get('key')
    text = data.get('text')

    if key:
        print(f"[KEY] {key}")
        try:
            # Normalize for pyautogui
            keymap = {
                ' ': 'space',
                'ArrowLeft': 'left',
                'ArrowRight': 'right',
                'ArrowUp': 'up',
                'ArrowDown': 'down',
                'Enter': 'enter',
                'Backspace': 'backspace',
                'Tab': 'tab'
            }
            resolved_key = keymap.get(key, key.lower())
            pyautogui.press(resolved_key)
        except Exception as e:
            print(f"⚠️ Key press error: {e}")

    elif text:
        print(f"[TYPE] {text}")
        try:
            pyautogui.write(text)
        except Exception as e:
            print(f"⚠️ Typing error: {e}")


# Track last mouse position per session
last_mouse_pos = {}

@socketio.on('mouse_move')
def handle_mouse_move(data):
    if not socket_authenticated():
        return

    dx = data.get('dx', 0)
    dy = data.get('dy', 0)

    try:
        pyautogui.moveRel(dx, dy, duration=0.05)
        print(f"[MOUSE MOVE] Δx={dx}, Δy={dy}")
    except Exception as e:
        print(f"⚠️ Mouse move error: {e}")



@socketio.on('mouse_move_end')
def handle_mouse_move_end():
    if not socket_authenticated():
        return
    sid = request.sid
    last_mouse_pos.pop(sid, None)
    print(f"[MOUSE MOVE END] sid={sid}")


@socketio.on('scroll')
def handle_scroll(data):
    if not socket_authenticated():
        return
    delta = data.get('deltaY')
    print(f"[SCROLL] deltaY={delta}")
    try:
        pyautogui.scroll(-int(delta))
    except Exception as e:
        print(f"⚠️ Scroll failed: {e}")

@socketio.on('scroll_end')
def handle_scroll_end():
    if not socket_authenticated():
        return
    print("[SCROLL] end")

# --- Entry ---
if __name__ == '__main__':
    print("🚀 Media Remote running at http://localhost:9090")
    socketio.run(app, host='0.0.0.0', port=9090, debug=True)
