import socket
import threading
import random
import time
import json
import os
from datetime import datetime
from protocol import encode_message, decode_message

# =======================
# Configurações do Servidor
# =======================
HOST = '0.0.0.0'
PORT = 65432
NUM_PLAYERS = 2

# =======================
# Regras do Jogo
# =======================
# Em Liar's Dice (versão do filme), 1 (ás) é coringa.
# - Se a aposta for face 1 -> contam apenas os 1.
# - Se a aposta for 2..6 -> contam a face apostada + todos os 1.
RULE_WILD_ONES = True

# =======================
# Estado Global
# =======================
clients = []            # [{"socket": sock, "addr": (ip, port)}]
player_data = {}        # {sock: {"name": str, "dice_count": int, "dice_roll": [int,...]}}
# CORREÇÃO: Usar RLock (Reentrant Lock) para permitir que a mesma thread
# adquira o lock múltiplas vezes. Isso evita o deadlock quando uma função
# com lock (handle_challenge) chama outra função com lock (start_new_round).
game_lock = threading.RLock()
game_started = False
current_turn_index = 0
last_bid = {"quantity": 0, "face": 0}
game_should_end = False

# =======================
# Logging (console + arquivo)
# =======================
LOG_FILE = "server_log.txt"

def _ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log(event, **fields):
    """
    Log estruturado: imprime no console e grava em server_log.txt.
    Ex.: log("SEND", to="João", type="info", payload={...})
    """
    record = {"ts": _ts(), "event": event, **fields}
    line = json.dumps(record, ensure_ascii=False)
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

# =======================
# Utilitários
# =======================
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def get_player_name(sock):
    return player_data.get(sock, {}).get("name", f"?({sock.fileno()})")

def send_to(sock, msg_type, payload):
    """
    Envia uma mensagem para um cliente e registra no log.
    """
    try:
        sock.sendall(encode_message(msg_type, payload))
        log("SEND", to=get_player_name(sock), type=msg_type, payload=payload)
    except Exception as e:
        log("SEND_ERROR", to=get_player_name(sock), error=str(e))

def broadcast(msg_type, payload):
    """
    Envia uma mensagem a todos os clientes e registra no log (um por um).
    """
    for c in list(clients):
        send_to(c["socket"], msg_type, payload)

def count_matches_in_hand(face, hand):
    """
    Conta quantos dados da mão 'hand' batem com a aposta considerando a regra do coringa.
    - face == 1: contam apenas os 1.
    - face 2..6: contam face OU 1 se RULE_WILD_ONES == True.
    """
    if face == 1:
        return sum(1 for d in hand if d == 1)
    if RULE_WILD_ONES:
        return sum(1 for d in hand if d == face or d == 1)
    return sum(1 for d in hand if d == face)

# =======================
# Fluxo do Jogo
# =======================
def start_new_round():
    """
    Nova rodada:
    - Zera aposta
    - Rola dados dos jogadores ativos
    - Envia dados (privado) a cada jogador
    - Chama o próximo turno válido
    """
    global last_bid, current_turn_index, game_should_end

    with game_lock:
        active_socks = [s for s in player_data if player_data[s]['dice_count'] > 0]

        if len(active_socks) <= 1:
            winner = player_data[active_socks[0]]['name'] if active_socks else "Ninguém"
            broadcast("game_over", {"message": f"O vencedor é {winner}!"})
            log("GAME_OVER", winner=winner)
            game_should_end = True
            return

        last_bid = {"quantity": 0, "face": 0}

        # (Re)rola os dados e envia individualmente
        for s in active_socks:
            n = player_data[s]['dice_count']
            player_data[s]['dice_roll'] = [random.randint(1, 6) for _ in range(n)]
            send_to(s, "round_start", {"dice": player_data[s]['dice_roll']})
            # Loga no servidor (não é enviado aos outros jogadores)
            log("ROLL", player=get_player_name(s), dice=player_data[s]['dice_roll'])

        # Garante que o jogador do turno atual tem dados
        while player_data[clients[current_turn_index]['socket']]['dice_count'] == 0:
            current_turn_index = (current_turn_index + 1) % len(clients)

        time.sleep(0.5)
        prompt_turn()

def prompt_turn():
    """
    Anuncia de quem é a vez e envia o 'your_turn' ao jogador correto.
    """
    turn_sock = clients[current_turn_index]['socket']
    turn_name = get_player_name(turn_sock)

    state = {
        "players": [{"name": d["name"], "dice_count": d["dice_count"]} for d in player_data.values()],
        "last_bid": last_bid,
        "current_turn": turn_name
    }

    broadcast("game_update", {"state": state, "message": f"Vez de {turn_name}"})
    send_to(turn_sock, "your_turn", None)
    log("TURN", player=turn_name, last_bid=last_bid)

def handle_challenge():
    """
    Processa 'duvido':
    - Identifica apostador (jogador anterior com dados)
    - Revela dados de todos (tempo real) + envia resumo 'reveal_all'
    - Conta com a regra do coringa e decide quem perde dado
    - Define próximo turno e inicia nova rodada
    """
    global current_turn_index

    with game_lock:
        # Quem é o apostador? -> o jogador anterior ao desafiante com dados
        bidder_idx = current_turn_index
        while True:
            bidder_idx = (bidder_idx - 1 + len(clients)) % len(clients)
            if player_data[clients[bidder_idx]['socket']]['dice_count'] > 0:
                break

        challenger_sock = clients[current_turn_index]['socket']
        bidder_sock = clients[bidder_idx]['socket']

        challenger = get_player_name(challenger_sock)
        bidder = get_player_name(bidder_sock)

        broadcast("info", {
            "message": f"\n!!! {challenger} duvidou da aposta de {bidder} "
                       f"({last_bid['quantity']}x {last_bid['face']}) !!!"
        })
        log("CHALLENGE", challenger=challenger, bidder=bidder, last_bid=last_bid)
        time.sleep(0.8)

        # Revelação e contagem
        total_count = 0
        revealed_data = []
        face = last_bid['face']

        for psock, pdata in player_data.items():
            if pdata['dice_count'] > 0:
                hand = pdata['dice_roll']
                revealed_data.append({"player": pdata['name'], "dice": hand})
                # Mostra em tempo real
                broadcast("info", {"message": f"{pdata['name']}: {hand}"})
                # Loga servidor
                log("REVEAL", player=pdata['name'], dice=hand)
                # Contagem com regra do coringa
                total_count += count_matches_in_hand(face, hand)
                time.sleep(0.6)

        # Resumo final (para clientes) e no log do servidor
        broadcast("reveal_all", {"dice_data": revealed_data})
        log("REVEAL_ALL", data=revealed_data, counted_face=face, total_count=total_count,
            wild_ones=RULE_WILD_ONES)

        # Decide quem perde um dado
        if total_count >= last_bid['quantity']:
            # Aposta válida -> desafiante perde um dado
            player_data[challenger_sock]['dice_count'] -= 1
            broadcast("info", {
                "message": f"Aposta VERDADEIRA! Havia {total_count}. {challenger} perde 1 dado."
            })
            log("CHALLENGE_RESULT", result="VALID_BID",
                loser=challenger, total_count=total_count)
            # Próximo turno: desafiante começa
            # (mantém current_turn_index como está)
        else:
            # Aposta falsa -> apostador perde um dado
            player_data[bidder_sock]['dice_count'] -= 1
            broadcast("info", {
                "message": f"Aposta FALSA! Havia apenas {total_count}. {bidder} perde 1 dado."
            })
            log("CHALLENGE_RESULT", result="BLUFF",
                loser=bidder, total_count=total_count)
            # Próximo turno: apostador começa
            current_turn_index = bidder_idx

        # Pausa para os jogadores lerem o resultado antes da próxima rodada
        time.sleep(4)
        start_new_round()

# =======================
# Thread por cliente
# =======================
def handle_client(sock, addr):
    """
    Comunicação com um cliente:
    - Recebe o nome (set_name)
    - Espera o início do jogo
    - Processa ações: bid / challenge
    - Faz limpeza ao desconectar
    """
    global game_started, game_should_end, current_turn_index, last_bid
    name = f"{addr}"

    try:
        # 1) Recebe o nome do jogador
        raw = sock.recv(2048)
        if not raw:
            return
        msg = decode_message(raw)
        log("RECV", frm=name, raw=msg)

        if msg.get('type') == 'set_name':
            name = msg['payload']['name']
            with game_lock:
                player_data[sock] = {"name": name, "dice_count": 5, "dice_roll": []}
            broadcast("info", {"message": f"{name} entrou no jogo."})
            log("JOIN", player=name, addr=str(addr))
        else:
            send_to(sock, "error", {"message": "Primeira mensagem deve ser 'set_name'."})
            return

        # 2) Espera o jogo começar
        while not game_started:
            time.sleep(0.1)
            if game_should_end:
                return

        # 3) Loop principal de ações do jogador
        while not game_should_end:
            raw = sock.recv(4096)
            if not raw:
                break
            msg = decode_message(raw)
            log("RECV", frm=name, raw=msg)
            
            with game_lock:
                # Valida turno
                if clients[current_turn_index]['socket'] != sock:
                    send_to(sock, "error", {"message": "Não é seu turno."})
                    continue

                msg_type = msg.get('type')
                payload = msg.get('payload', {})

                if msg_type == 'bid':
                    try:
                        new_bid = {"quantity": int(payload['quantity']), "face": int(payload['face'])}
                        # Valida que a aposta sobe (quantidade ou mesma quantidade com face maior)
                        if (new_bid['quantity'] > last_bid['quantity'] or
                            (new_bid['quantity'] == last_bid['quantity'] and new_bid['face'] > last_bid['face'])):

                            last_bid = new_bid
                            log("BID", player=name, bid=last_bid)

                            # Passa turno para o próximo com dados
                            current_turn_index = (current_turn_index + 1) % len(clients)
                            while player_data[clients[current_turn_index]['socket']]['dice_count'] == 0:
                                current_turn_index = (current_turn_index + 1) % len(clients)

                            prompt_turn()
                        else:
                            send_to(sock, "error", {"message": "Aposta inválida. Aumente a quantidade ou a face."})
                            send_to(sock, "your_turn", None)
                    except (ValueError, TypeError, KeyError):
                        send_to(sock, "error", {"message": "Formato de aposta inválido."})
                        send_to(sock, "your_turn", None)


                elif msg_type == 'challenge':
                    if last_bid['quantity'] == 0:
                        send_to(sock, "error", {"message": "Não pode duvidar antes da primeira aposta."})
                        send_to(sock, "your_turn", None)
                    else:
                        handle_challenge()

    except Exception as e:
        log("CLIENT_ERROR", player=name, error=str(e))

    finally:
        # 4) Limpeza
        with game_lock:
            if game_started and not game_should_end:
                if sock in player_data:
                    broadcast("game_over", {"message": f"{get_player_name(sock)} saiu. Jogo encerrado."})
                    log("FORCE_END", reason=f"{get_player_name(sock)} disconnected")
                    game_should_end = True

            # Remove cliente das estruturas
            clients[:] = [c for c in clients if c['socket'] != sock]
            if sock in player_data:
                del player_data[sock]
            try:
                sock.close()
            except:
                pass

# =======================
# Bootstrap do Servidor
# =======================
def main():
    global game_started

    # Limpa log antigo
    if os.path.exists(LOG_FILE):
        try:
            os.remove(LOG_FILE)
        except:
            pass

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(NUM_PLAYERS)
    print(f"Servidor iniciado em {get_local_ip()}:{PORT}")
    log("SERVER_START", host=get_local_ip(), port=PORT, players_needed=NUM_PLAYERS)

    try:
        # Aguarda todos conectarem
        while len(clients) < NUM_PLAYERS:
            sock, addr = server.accept()
            with game_lock:
                clients.append({'socket': sock, 'addr': addr})
            log("ACCEPT", addr=str(addr))
            threading.Thread(target=handle_client, args=(sock, addr), daemon=True).start()

        print("Todos conectados. Iniciando em 3s...")
        log("ALL_CONNECTED", count=len(clients))
        time.sleep(3)
        game_started = True
        start_new_round()

        # Loop ocioso do servidor até fim do jogo
        while not game_should_end:
            time.sleep(0.5)
            
    finally:
        print("Encerrando servidor...")
        for c in clients:
            try:
                c['socket'].close()
            except:
                pass
        server.close()
        log("SERVER_STOP")

if __name__ == "__main__":
    main()