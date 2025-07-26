import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential #type-ignore
from tensorflow.keras.layers import LSTM, Dense, Dropout #type-ignore
import warnings
warnings.filterwarnings("ignore")

def predict_crypto_price(prices):
    # Ensure we have enough data
    if len(prices) < 7:
        return [0.0] * 7  # Return zeros if insufficient data

    # Convert prices to DataFrame
    data = pd.DataFrame(prices, columns=["price"])
    
    # Normalize the data
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(data[['price']].values)

    # Parameters
    look_back = 3  # Use the past 3 days to predict the next day
    future_days = 7  # Predict next 7 days
    X, y = [], []

    # Create sequences for training
    for i in range(len(scaled_data) - look_back):
        X.append(scaled_data[i:(i + look_back), 0])
        y.append(scaled_data[i + look_back, 0])

    if not X or not y:
        return [prices[-1]] * 7  # Fallback to last price if no sequences

    X = np.array(X)
    y = np.array(y)

    # Reshape X to [samples, time steps, features] for LSTM
    X = X.reshape((X.shape[0], X.shape[1], 1))

    # Build LSTM model
    model = Sequential()
    model.add(LSTM(units=50, return_sequences=True, input_shape=(look_back, 1)))
    model.add(Dropout(0.2))
    model.add(LSTM(units=50))
    model.add(Dropout(0.2))
    model.add(Dense(units=1))

    # Compile the model
    model.compile(optimizer='adam', loss='mean_squared_error')

    # Train the model
    model.fit(X, y, epochs=50, batch_size=32, verbose=0)

    # Prepare input for prediction
    last_sequence = scaled_data[-look_back:]
    predicted_prices = []

    # Predict future prices
    current_sequence = last_sequence.copy()
    for _ in range(future_days):
        current_sequence_reshaped = current_sequence.reshape((1, look_back, 1))
        next_pred = model.predict(current_sequence_reshaped, verbose=0)
        predicted_prices.append(next_pred[0, 0])
        # Update sequence with the predicted price
        current_sequence = np.roll(current_sequence, -1)
        current_sequence[-1] = next_pred[0, 0]

    # Inverse transform to get actual price values
    predicted_prices = np.array(predicted_prices).reshape(-1, 1)
    predicted_prices = scaler.inverse_transform(predicted_prices)

    # Ensure predictions are positive and rounded
    predicted_prices = [max(0, round(float(p), 2)) for p in predicted_prices]

    return predicted_prices