import json

def encode_message(msg_type, payload=None, player_id=None, game_id=None):
    """
    Cria uma string JSON a partir de um dicionário.
    - msg_type: tipo da mensagem (ex: 'READY', 'BET', 'CHALLENGE', etc.)
    - payload: dados adicionais (ex: aposta, resultado da rodada)
    - player_id: identificador único do jogador
    - game_id: identificador da partida (pode ser None neste caso)
    Retorna: string JSON pronta para envio via socket.
    """
    return json.dumps({
        "type": msg_type,
        "player_id": player_id,
        "game_id": game_id,
        "payload": payload
    })

def decode_message(msg_str):
    """
    Converte string JSON recebida em um dicionário Python.
    É usada no lado do servidor e do cliente para interpretar mensagens.
    """
    return json.loads(msg_str)
