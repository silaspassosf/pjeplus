import sys
import json
import struct
import threading
import socket
import os

HOST = "127.0.0.1"
PORT = int(os.environ.get('INFOJUD_PORT', 18765))

def read_native_message():
    raw_len = sys.stdin.buffer.read(4)
    if len(raw_len) == 0:
        return None
    msg_len = struct.unpack("<I", raw_len)[0]
    data = sys.stdin.buffer.read(msg_len)
    if not data:
        return None
    return json.loads(data.decode("utf-8"))

def send_native_message(obj):
    data = json.dumps(obj).encode("utf-8")
    length = struct.pack("<I", len(data))
    
    sys.stderr.write(f"[send_native_message] Sending {len(data)} bytes: {obj}\n")
    sys.stderr.flush()
    
    sys.stdout.buffer.write(length)
    sys.stdout.buffer.flush()  # flush após length
    
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()  # flush após data

def handle_client(conn):
    try:
        buf = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                return
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                line = line.strip()
                if not line:
                    continue
                req = json.loads(line.decode("utf-8"))

                if req.get("action") == "open_url":
                    sys.stderr.write(f"Sending to extension: {req}\n")
                    sys.stderr.flush()
                    send_native_message({"action": "open_url", "url": req.get("url", "")})
                    conn.sendall((json.dumps({"ok": True, "status": "sent"}) + "\n").encode("utf-8"))
                else:
                    conn.sendall((json.dumps({"ok": False, "error": "unknown action"}) + "\n").encode("utf-8"))
    except Exception as e:
        try:
            conn.sendall((json.dumps({"ok": False, "error": str(e)}) + "\n").encode("utf-8"))
        except:
            pass
    finally:
        conn.close()

def tcp_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind((HOST, PORT))
        s.listen(5)
        sys.stderr.write(f"TCP server listening on {HOST}:{PORT}\n")
        sys.stderr.flush()
        while True:
            conn, _ = s.accept()
            threading.Thread(target=handle_client, args=(conn,), daemon=True).start()
    except Exception as e:
        sys.stderr.write(f"TCP server error: {e}\n")
        sys.stderr.flush()

def main():
    sys.stderr.write("native_host started\n"); sys.stderr.flush()
    threading.Thread(target=tcp_server, daemon=True).start()

    while True:
        msg = read_native_message()
        if msg is None:
            sys.stderr.write("stdin closed, exiting\n"); sys.stderr.flush()
            break
        sys.stderr.write(f"From extension: {msg}\n")
        sys.stderr.flush()

if __name__ == "__main__":
    main()