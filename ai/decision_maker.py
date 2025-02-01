import random
import numpy as np
import tensorflow as tf

class DecisionMaker:
    def __init__(self, game_controller):
        self.game_controller = game_controller
        self.model = self.load_model()

    def load_model(self):
        # Carregar um modelo pré-treinado (substitua pelo caminho do seu modelo)
        model = tf.keras.models.load_model('path/to/your/model')
        return model

    def preprocess_state(self, hand, bench, active):
        # Pré-processar o estado do jogo para o formato esperado pelo modelo
        # Isso pode incluir a conversão de cartas em IDs numéricos, normalização, etc.
        state = {
            'hand': [card['id'] for card in hand],
            'bench': [pokemon['id'] for pokemon in bench.values() if pokemon],
            'active': active[0]['id'] if active else None
        }
        # Converter para um formato adequado para o modelo (exemplo: vetor numpy)
        state_vector = np.array([state['hand'], state['bench'], state['active']])
        return state_vector

    def make_decision(self):
        hand = self.game_controller.read_hand_cards()
        bench = self.game_controller.read_bench_pokemon()
        active = self.game_controller.read_active_pokemon()

        if not hand:
            print("No cards in hand to play.")
            return

        # Pré-processar o estado do jogo
        state_vector = self.preprocess_state(hand, bench, active)

        # Fazer uma previsão usando o modelo
        action_probabilities = self.model.predict(state_vector)
        best_action_index = np.argmax(action_probabilities)

        # Selecionar a melhor ação (exemplo: jogar a melhor carta)
        card_to_play = hand[best_action_index]
        print(f"Decisão da IA: Jogar a carta {card_to_play['name']}")
        # Chamar métodos do game_controller para jogar a carta
        # self.game_controller.play_card(card_to_play)

        return

# Exemplo de uso
# decision_maker = DecisionMaker(game_controller)
# decision_maker.make_decision()
