import json

def encode_message(msg_type, payload=None):
    """
    Codifica uma mensagem para envio via socket.

    Parâmetros:
        msg_type (str) - Tipo da mensagem, por exemplo:
            'info', 'error', 'game_update', 'your_turn', etc.
        payload (dict) - Conteúdo adicional da mensagem.

    Retorna:
        bytes - A mensagem convertida para JSON e depois para bytes.
    """
    return json.dumps({
        "type": msg_type,
        "payload": payload
    }).encode('utf-8')

def decode_message(msg_bytes):
    """
    Decodifica bytes recebidos de um socket para um dicionário Python.

    Parâmetros:
        msg_bytes (bytes) - Mensagem recebida no formato JSON.

    Retorna:
        dict - Mensagem convertida de JSON para dicionário Python.
    """
    return json.loads(msg_bytes.decode('utf-8'))
