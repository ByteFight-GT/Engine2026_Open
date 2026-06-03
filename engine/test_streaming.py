import socket
import json

# -----------------------------
# Configuration
# -----------------------------
SERVER_HOST = "127.0.0.1"  # server IP
SERVER_PORT = 8765         # server port

# -----------------------------
# Create client socket
# -----------------------------
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect to server
sock.connect((SERVER_HOST, SERVER_PORT))
print(f"Connected to {SERVER_HOST}:{SERVER_PORT} from local port {sock.getsockname()[1]}")

# -----------------------------
# Send a JSON message
# -----------------------------
message = {"type": "hello", "content": "Hi server!"}
sock.sendall((json.dumps(message) + "\n").encode("utf-8"))
print("Message sent!")

# -----------------------------
# Receive messages from server
# -----------------------------
buffer = ""
try:
    while True:
        data = sock.recv(1024).decode("utf-8")
        if not data:
            print("Server closed the connection")
            break
        
        buffer += data
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            try:
                msg = json.loads(line)
                print(msg)
            except json.JSONDecodeError:
                print("Received invalid JSON:", line)
except KeyboardInterrupt:
    print("Client shutting down")
finally:
    sock.close()