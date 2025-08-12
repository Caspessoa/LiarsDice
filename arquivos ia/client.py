import socket
import threading
from protocol import encode_message, decode_message

HOST = '127.0.0.1'  # IP do servidor
PORT = 5000

def receive_messages(sock):
    """
    Thread que recebe mensagens do servidor e as imprime no terminal.
    """
    while True:
        try:
            msg = sock.recv(1024).decode()
            if not msg:
                break
            data = decode_message(msg)
            print(f"\n[SERVER] {data}\n> ", end="")
        except:
            break

def main():
    """
    Conecta ao servidor e aguarda comandos do usuário.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    print(f"Conectado ao servidor {HOST}:{PORT}")

    # Thread para ouvir mensagens do servidor
    threading.Thread(target=receive_messages, args=(sock,), daemon=True).start()

    # Loop principal: envia comandos digitados
    while True:
        cmd = input("> ").strip().upper()
        if cmd == "READY":
            sock.send(encode_message("READY").encode())
        elif cmd.startswith("BET"):
            try:
                _, q, f = cmd.split()
                sock.send(encode_message("BET", {"quantity": int(q), "face": int(f)}).encode())
            except:
                print("Uso: BET quantidade face (ex: BET 3 5)")
        elif cmd == "CHALLENGE":
            sock.send(encode_message("CHALLENGE").encode())

if __name__ == "__main__":
    main()
