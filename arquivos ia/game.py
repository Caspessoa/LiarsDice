import random

class LiarDiceGame:
    def __init__(self, players):
        """
        Inicializa o jogo com a lista de jogadores.
        - players: lista de IDs (strings) dos jogadores.
        """
        self.players = players
        self.hands = {p: [] for p in players}         # Mão de dados de cada jogador
        self.dice_count = {p: 5 for p in players}     # Quantos dados cada jogador ainda tem
        self.current_bet = None                       # Última aposta feita
        self.turn_index = 0                           # Índice do jogador da vez

    def roll_dice(self):
        """Rola os dados para todos os jogadores."""
        for player in self.players:
            self.hands[player] = [random.randint(1, 6) for _ in range(self.dice_count[player])]

    def get_hand(self, player):
        """Retorna a mão de um jogador específico."""
        return self.hands[player]

    def set_bet(self, player, quantity, face):
        """Define a aposta atual."""
        self.current_bet = (quantity, face, player)

    def next_turn(self):
        """
        Passa a vez para o próximo jogador que ainda tenha dados.
        Retorna o ID do próximo jogador.
        """
        while True:
            self.turn_index = (self.turn_index + 1) % len(self.players)
            if self.dice_count[self.players[self.turn_index]] > 0:
                return self.players[self.turn_index]

    def reveal_all(self):
        """Retorna todas as mãos para mostrar na hora do desafio."""
        return self.hands

    def resolve_challenge(self):
        """
        Resolve um desafio:
        - Conta quantos dados batem com o valor apostado (ou são 1, que é curinga).
        - Determina quem perde um dado.
        Retorna: (perdedor, quantidade total encontrada)
        """
        quantity, face, bettor = self.current_bet
        total_count = sum(die == face or die == 1 for hand in self.hands.values() for die in hand)
        if total_count >= quantity:
            # Apostador vence, desafiante perde um dado
            loser = self.next_turn()
        else:
            # Apostador perde um dado
            loser = bettor

        self.dice_count[loser] -= 1
        return loser, total_count

    def is_game_over(self):
        """Verifica se só resta 1 jogador com dados."""
        return sum(1 for c in self.dice_count.values() if c > 0) == 1

    def get_winner(self):
        """Retorna o jogador com mais dados (o vencedor)."""
        return max(self.dice_count, key=lambda p: self.dice_count[p])
