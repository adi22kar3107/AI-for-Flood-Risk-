import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib
import os

def train_model():
    print("Starting model training pipeline...")
    
    # Check if a dummy dataset exists, else create one for demonstration
    if not os.path.exists("data.csv"):
        print("data.csv not found. Creating a synthetic dataset for demonstration...")
        data = {
            'rainfall_mm': [10, 20, 50, 120, 150, 5, 80, 200, 30, 250, 15, 300, 60, 180, 220],
            'river_level_m': [2.1, 2.3, 3.5, 5.0, 5.5, 1.5, 4.2, 6.0, 2.5, 6.5, 2.2, 7.0, 3.8, 5.8, 6.2],
            'soil_moisture_pct': [40, 45, 60, 80, 85, 30, 70, 90, 50, 95, 42, 98, 65, 88, 92],
            'flood_risk': [0, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1]
        }
        df = pd.DataFrame(data)
        df.to_csv("data.csv", index=False)
    
    df = pd.read_csv("data.csv")
    
    if df.empty:
        print("Dataset is empty. Please provide valid tabular data.")
        return
        
    X = df[['rainfall_mm', 'river_level_m', 'soil_moisture_pct']]
    y = df['flood_risk']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    score = model.score(X_test, y_test)
    print(f"Model trained successfully! Test Accuracy: {score:.2f}")
    
    joblib.dump(model, "model.pkl")
    print("Model saved as model.pkl")

if __name__ == "__main__":
    train_model()
