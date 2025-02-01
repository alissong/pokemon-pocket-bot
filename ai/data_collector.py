import numpy as np

class DataCollector:
    def __init__(self):
        self.data = []

    def record_state_action(self, state, action):
        self.data.append((state, action))

    def save_data(self, file_path):
        states, actions = zip(*self.data)
        np.save(file_path, {'states': states, 'actions': actions})

# Exemplo de uso
# data_collector = DataCollector()
# data_collector.record_state_action(current_state, action_taken)
# data_collector.save_data('path/to/your/training_data.npy')
