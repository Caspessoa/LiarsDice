import socket
import threading
from protocol import encode_message, decode_message
from game import LiarDiceGame

# Configuração de host e porta
HOST = '0.0.0.0'
PORT = 5000

# Estruturas para controle de conexões e jogo
clients = {}         # player_id -> conexão socket
players_ready = []   # lista de jogadores que já deram READY
game = None          # instância do jogo
current_turn = None  # jogador da vez

def handle_client(conn, addr):
    """
    Thread que lida com cada cliente conectado.
    Recebe mensagens, decodifica e passa para o processador.
    """
    global game, current_turn
    player_id = f"{addr[0]}:{addr[1]}"
    clients[player_id] = conn
    print(f"[+] Player conectado: {player_id}")

    try:
        while True:
            msg = conn.recv(1024).decode()
            if not msg:
                break
            data = decode_message(msg)
            process_message(player_id, data)
    except:
        pass
    finally:
        print(f"[-] Player desconectado: {player_id}")
        conn.close()
        if player_id in clients:
            del clients[player_id]

def process_message(player_id, data):
    """
    Interpreta as mensagens recebidas e executa a ação correspondente.
    """
    global game, current_turn
    msg_type = data["type"]

    # Jogador indica que está pronto
    if msg_type == "READY":
        if player_id not in players_ready:
            players_ready.append(player_id)
            print(f"[INFO] {player_id} está pronto.")
        # Quando 2 jogadores estão prontos, inicia o jogo
        if len(players_ready) == 2 and game is None:
            start_game()

    # Jogador faz uma aposta
    elif msg_type == "BET":
        if player_id != current_turn:
            send_to(player_id, encode_message("ERROR", {"msg": "Não é seu turno"}))
            return
        q = data["payload"]["quantity"]
        f = data["payload"]["face"]
        game.set_bet(player_id, q, f)
        broadcast(encode_message("GAME_UPDATE", {"bet": (q, f), "player": player_id}))
        current_turn = game.next_turn()
        send_turn_notification()

    # Jogador desafia
    elif msg_type == "CHALLENGE":
        if player_id != current_turn:
            send_to(player_id, encode_message("ERROR", {"msg": "Não é seu turno"}))
            return
        all_dice = game.reveal_all()
        broadcast(encode_message("REVEAL", all_dice))
        loser, count = game.resolve_challenge()
        broadcast(encode_message("ROUND_RESULT", {"loser": loser, "count": count}))

        # Verifica fim de jogo
        if game.is_game_over():
            winner = game.get_winner()
            broadcast(encode_message("GAME_END", {"winner": winner}))
            return

        # Nova rodada
        game.roll_dice()
        for player in players_ready:
            send_to(player, encode_message("PRIVATE_HAND", game.get_hand(player)))
        current_turn = game.next_turn()
        send_turn_notification()

def start_game():
    """Inicia o jogo e envia as mãos iniciais."""
    global game, current_turn
    print("[INFO] Iniciando jogo...")
    game = LiarDiceGame(players_ready)
    game.roll_dice()
    for player in players_ready:
        send_to(player, encode_message("PRIVATE_HAND", game.get_hand(player)))
    current_turn = players_ready[0]
    send_turn_notification()

def send_turn_notification():
    """Informa a todos quem é o jogador da vez."""
    broadcast(encode_message("TURN", {"player": current_turn}))

def broadcast(message):
    """Envia uma mensagem para todos os clientes."""
    for conn in clients.values():
        conn.send(message.encode())

def send_to(player_id, message):
    """Envia uma mensagem para um cliente específico."""
    if player_id in clients:
        clients[player_id].send(message.encode())

def main():
    """Função principal do servidor."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[INFO] Servidor ouvindo em {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()
