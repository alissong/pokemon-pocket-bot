import numpy as np
import tensorflow as tf
from sklearn.model_selection import train_test_split

# Carregar dados de treinamento (substitua pelo caminho dos seus dados)
data = np.load('path/to/your/training_data.npy')
states = data['states']
actions = data['actions']

# Dividir os dados em conjuntos de treinamento e teste
X_train, X_test, y_train, y_test = train_test_split(states, actions, test_size=0.2)

# Definir o modelo
model = tf.keras.models.Sequential([
    tf.keras.layers.Dense(128, activation='relu', input_shape=(X_train.shape[1],)),
    tf.keras.layers.Dense(64, activation='relu'),
    tf.keras.layers.Dense(len(np.unique(actions)), activation='softmax')
])

# Compilar o modelo
model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])

# Treinar o modelo
model.fit(X_train, y_train, epochs=10, validation_data=(X_test, y_test))

# Salvar o modelo treinado
model.save('path/to/your/model')
