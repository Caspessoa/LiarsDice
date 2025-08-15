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

# Imports da biblioteca rich para uma UI avançada
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Cria uma instância do console do rich para gerenciar a exibição
console = Console()

# Dicionário que mapeia o número da face do dado para o ícone.
DICE_ICONS = {
    1: "⚀", 2: "⚁", 3: "⚂",
    4: "⚃", 5: "⚄", 6: "⚅"
}

# Variáveis globais para armazenar estado do cliente
my_turn = False           # Indica se é a vez do jogador
my_dice = []              # Lista de dados do jogador
game_state = {}           # Estado geral do jogo (todos os jogadores)
log_file = "partida_log.txt"  # Arquivo onde o histórico será salvo

def format_dice(dice_list):
    """
    Formata uma lista de dados como ícones.
    """
    return ' '.join(DICE_ICONS.get(d, str(d)) for d in dice_list)
# Permite comunicação direta entre Thread Princ. e Sec. (sinalização)

def log_event(text):
    """
    Salva um evento no arquivo de log.
    """
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(text + "\n")

def clear_screen():
    """
    Limpa a tela do terminal.
    """
    os.system('cls' if os.name == 'nt' else 'clear')

def print_game_state():
    """
    Exibe o estado do jogo na tela usando painéis da biblioteca rich.
    """
    clear_screen()

    player_lines = []
    if game_state.get('players'):
        block_width = 50  # Largura do bloco de texto para alinhamento
        for p in game_state['players']:
            # A parte da esquerda começa apenas com o nome
            left_part = Text(p['name'])
            # A parte da direita é sempre a contagem de dados
            right_part = Text(f"{p['dice_count']} dados")

            # Adiciona o indicador de turno à parte esquerda, se for o caso
            if p['name'] == game_state.get('current_turn'):
                left_part.append("  ")  # Adiciona um espaço
                left_part.append(Text.from_markup("[bold green]<- TURNO ATUAL[/bold green]"))

            # Calcula o preenchimento para alinhar nas extremidades
            padding = " " * (block_width - len(left_part) - len(right_part))
            line = Text.assemble(left_part, padding, right_part)
            player_lines.append(line)

    player_text = Text("\n").join(player_lines)

    # Cria o conteúdo para a aposta na mesa
    if game_state.get('last_bid') and game_state['last_bid']['quantity'] > 0:
        b = game_state['last_bid']
        face_char = DICE_ICONS.get(b['face'], str(b['face']))
        bid_text = Text.from_markup(f"Aposta na mesa: [bold yellow]{b['quantity']}x {face_char}[/bold yellow]")
    else:
        bid_text = Text("Nenhuma aposta ainda.")

    # Monta o conteúdo principal do painel
    main_content = Text("\n\n").join([
        player_text,
        bid_text
    ])

    # Cria e exibe o painel principal com título e subtítulo
    console.print(
        Panel(
            main_content,
            title="[bold cyan]LIAR'S DICE[/bold cyan]",
            subtitle=Text.from_markup(f"Seus dados: [bold yellow]{format_dice(my_dice)}[/bold yellow]"),
            border_style="blue"
        )
    )

def listen(sock):
    """
    Thread responsável por ouvir mensagens do servidor e atualizar o estado.
    """
    global my_turn, my_dice, game_state
    while True:
        try:
            raw = sock.recv(4096) # chamada bloqueante -> thread para e aguarda dados do servidor através da conexão sock. Lê até 4096 bytes e continua
            if not raw:
                break

            msg = decode_message(raw) # decodifica a mensagem recebida
            tipo = msg.get('type') # extrai o tipo da mensagem
            payload = msg.get('payload') # extrai os dados secundários da mensagem

            if tipo == 'round_start':
                my_dice = payload['dice']
                log_event(f"Nova rodada - seus dados: {my_dice}")

            elif tipo == 'game_update':
                game_state = payload['state']
                print_game_state()
                console.print(f"[dim]{payload['message']}[/dim]")
                log_event(f"Atualização: {payload['message']}")

            elif tipo == 'your_turn':
                my_turn = True # crucial. Desbloqueia a thread principal para a ação do jogador.
                console.print("\nSua vez! Digite aposta (ex: '3 4') ou 'duvido'")
                log_event("Sua vez de jogar.")

            elif tipo in ['info', 'error']:
                message = payload['message']
                style = ""
                # Colore mensagens de resultado com base no conteúdo
                if 'perde 1 dado' in message:
                    style = "red" if 'VERDADEIRA' in message else "green"
                elif 'entrou no jogo' in message:
                    style = "yellow"

                console.print(f"\n[bold {style}][SERVIDOR] {message}[/bold {style}]")
                log_event(f"[SERVIDOR] {message}")

            elif tipo == 'reveal_all':
                dados_revelados = payload['dice_data']

                reveal_lines = []
                for entry in dados_revelados:
                    formatted_hand = format_dice(entry['dice'])
                    reveal_lines.append(f"[bold]{entry['player']}:[/bold] {formatted_hand}")

                console.print(Panel("\n".join(reveal_lines), title="[yellow]DADOS REVELADOS[/yellow]", border_style="yellow"))
                log_event(f"Revelação final: {dados_revelados}")

            elif tipo == 'game_over':
                print_game_state()
                console.print(f"\n[bold magenta]!!! {payload['message']} !!![/bold magenta]")
                log_event(f"FIM: {payload['message']}")
                sock.close()
                os._exit(0)

        # Robustez e detecção de erros
        except (ConnectionAbortedError, ConnectionResetError, json.JSONDecodeError):
            console.print("\n[bold red]Conexão com o servidor foi perdida.[/bold red]")
            sock.close()
            os._exit(1)
        except Exception as e:
            console.print(f"\n[bold red]Ocorreu um erro inesperado: {e}[/bold red]")
            break

def main():
    global my_turn

    host = input("IP do servidor (padrão: 127.0.0.1): ") or "127.0.0.1"
    port = 65432
    nome = input("Seu nome: ")

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

    sock.sendall(encode_message('set_name', {'name': nome}))

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
                sock.sendall(encode_message('challenge'))
                my_turn = False
            elif len(cmd.split()) == 2:
                try:
                    q, f = map(int, cmd.split())
                    sock.sendall(encode_message('bid', {'quantity': q, 'face': f}))
                    my_turn = False
                except ValueError:
                    console.print("[red]Formato inválido. Use dois números inteiros.[/red]")
            else:
                console.print("[red]Comando inválido.[/red]")
        else:
            time.sleep(0.1)

if __name__ == "__main__":
    main()