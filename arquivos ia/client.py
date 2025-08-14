import socket # permite criar, conectar, enviar e receber dados em "soquetes"
import threading # usamos para ouvir o servidor e esperar pelo input do usuário ao mesmo tempo.
import json

#################
#bibs de sistema#
import os #######
import sys ######
import time #####
#################
from protocol import encode_message, decode_message

# Variáveis globais para armazenar estado do cliente
# Permite comunicação direta entre Thread Princ. e Sec. (sinalização)
my_turn = False           # Indica se é a vez do jogador
my_dice = []              # Lista de dados do jogador
game_state = {}           # Estado geral do jogo (todos os jogadores)
log_file = "partida_log.txt"  # Arquivo onde o histórico será salvo

def log_event(text):
    """
    Salva um evento no arquivo de log.
    Útil para gerar um histórico da partida e usar no relatório.
    """
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(text + "\n")

def clear_screen():
    """
    Limpa a tela do terminal (compatível com Windows e Linux).
    """
    os.system('cls' if os.name == 'nt' else 'clear')

def print_game_state():
    """
    Exibe na tela:
    - Seus dados
    - Quantos dados cada jogador ainda tem
    - Quem está jogando
    - Última aposta feita
    """
    clear_screen()
    print("====== DADO MENTIROSO ======")
    print(f"Seus dados: {my_dice}\n")

    # Mostra jogadores e seus dados restantes
    if game_state.get('players'):
        for p in game_state['players']:
            t = "<- SUA VEZ" if p['name'] == game_state.get('current_turn') else ""
            print(f"{p['name']}: {p['dice_count']} dados {t}")

    # Mostra a última aposta, se houver
    if game_state.get('last_bid') and game_state['last_bid']['quantity'] > 0:
        b = game_state['last_bid']
        print(f"\nAposta na mesa: {b['quantity']}x {b['face']}")
    else:
        print("\nNenhuma aposta ainda.")

def listen(sock):
    """
    Thread responsável por ouvir mensagens do servidor
    e atualizar o estado do cliente.
    """
    global my_turn, my_dice, game_state
    while True:
        try:
            raw = sock.recv(4096) # chamada bloqueante -> thread para e aguarda dados do servidor através da conexão sock. Lê até 4096 bytes e continua
            if not raw:
                print("\nConexão fechada pelo servidor.")
                break
            
            msg = decode_message(raw) # decodifica a mensagem recebida
            tipo = msg.get('type') # extrai o tipo da mensagem
            payload = msg.get('payload') # extrai os dados secundários da mensagem

            # Início de nova rodada (dados do jogador)
            if tipo == 'round_start':
                my_dice = payload['dice']
                log_event(f"Nova rodada - seus dados: {my_dice}")

            # Atualização geral do jogo
            elif tipo == 'game_update':
                game_state = payload['state']
                print_game_state()
                print(payload['message'])
                log_event(f"Atualização: {payload['message']}")

            # É a vez do jogador
            elif tipo == 'your_turn':
                my_turn = True # crucial. Desbloqueia a thread principal para a ação do jogador.
                print("\nSua vez! Digite aposta (ex: '3 4') ou 'duvido'")
                log_event("Sua vez de jogar.")

            # Mensagens de informação ou erro
            elif tipo in ['info', 'error']:
                print(f"\n[SERVIDOR] {payload['message']}")
                log_event(f"[SERVIDOR] {payload['message']}")

            # Revelação final de todos os dados após 'duvido'
            elif tipo == 'reveal_all':
                dados_revelados = payload['dice_data']
                print("\n=== DADOS REVELADOS ===")
                for entry in dados_revelados:
                    print(f"{entry['player']}: {entry['dice']}")
                print("=======================")
                log_event(f"Revelação final: {dados_revelados}")

            # Fim do jogo
            elif tipo == 'game_over':
                print_game_state()
                print(f"\n!!! {payload['message']} !!!")
                log_event(f"FIM: {payload['message']}")
                sock.close()
                os._exit(0)  # Encerra o cliente

        # Robustez e detecção de erros
        except (ConnectionAbortedError, ConnectionResetError, json.JSONDecodeError):
            print("\nConexão com o servidor foi perdida.")
            sock.close()
            os._exit(1)
        except Exception:
            # Em caso de qualquer outra exceção, encerra a thread
            break

def main():
    global my_turn

    # Solicita dados de conexão
    host = input("IP do servidor (padrão: 127.0.0.1): ") or "127.0.0.1"
    port = 65432
    nome = input("Seu nome: ")

    # Apaga log antigo, se existir
    if os.path.exists(log_file):
        os.remove(log_file)

    # Cria socket e conecta ao servidor
    # AF_INET -> protocolo IPV4 +
    # SOCK_STREAM -> protocolo TCP
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((host, port)) # outra chamada bloqueante
    except Exception as e:
        print(f"Falha ao conectar: {e}")
        return

    # Envia o nome do jogador para o servidor
    sock.sendall(encode_message('set_name', {'name': nome}))

    # Inicia a thread que escuta o servidor
    threading.Thread(target=listen, args=(sock,), daemon=True).start()
    """
    threading.Thread(...): Cria um objeto de thread.

    target=listen: Diz à thread que a função que ela deve executar é a nossa função listen.

    args=(sock,): Passa os argumentos necessários para a função listen (no caso, o objeto sock).

    daemon=True: Uma configuração importante. Significa que esta thread é uma "serva" da thread principal. Se a thread principal for encerrada  por qualquer motivo, a thread listen também será encerrada automaticamente.

    .start(): Inicia a execução da thread. A partir deste ponto, a função listen está rodando em segundo plano.
    """

    # Loop principal do jogador
    while True:
        if my_turn: # Executa esta parte do IF assim que a função listen envia 'your_turn'
            cmd = input("> ").strip().lower() # Bloqueia thread até que o usuário digite algo

            if cmd == 'duvido':
                # Envia comando de challenge
                sock.sendall(encode_message('challenge'))
                my_turn = False

            elif len(cmd.split()) == 2:
                try:
                    # Envia aposta (quantidade, face)
                    q, f = map(int, cmd.split())
                    sock.sendall(encode_message('bid', {'quantity': q, 'face': f}))
                    my_turn = False
                except ValueError:
                    print("Formato inválido. Use dois números inteiros.")
            else:
                print("Comando inválido.")
        else:
            # Pausa para não consumir 100% da CPU enquanto espera o turno
            time.sleep(0.1)

if __name__ == "__main__":
    main()