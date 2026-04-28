import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
import xgboost as xgb
from sklearn.metrics import mean_squared_error, r2_score
import joblib
import os
from src.utils import load_config, get_logger
from src.preprocessing import DataProcessor

class ModelTrainer:
    def __init__(self):
        self.config = load_config()
        self.logger = get_logger(__name__)
        self.models = {}
        self.best_model = None
        self.best_score = -np.inf

    def train(self):
        self.logger.info("Starting training pipeline...")
        
        # Data Loading & Processing
        dp = DataProcessor()
        df = dp.load_data()
        df = dp.feature_engineering(df)
        X_train, X_test, y_train, y_test = dp.preprocess(df)
        
        # Define Models
        self.models = {
            "Linear Regression": LinearRegression(),
            "Random Forest": RandomForestRegressor(**self.config['model_params']['random_forest']),
            "XGBoost": xgb.XGBRegressor(**self.config['model_params']['xgboost'])
        }
        
        results = {}
        
        for name, model in self.models.items():
            self.logger.info(f"Training {name}...")
            model.fit(X_train, y_train)
            
            y_pred = model.predict(X_test)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            r2 = r2_score(y_test, y_pred)
            
            results[name] = {"RMSE": rmse, "R2": r2}
            self.logger.info(f"{name} - RMSE: {rmse:.4f}, R2: {r2:.4f}")
            
            if r2 > self.best_score:
                self.best_score = r2
                self.best_model = model
        
        self.save_model()
        return results

    def save_model(self):
        if self.best_model:
            save_path = os.path.join(self.config['directories']['models'], self.config['files']['model'])
            joblib.dump(self.best_model, save_path)
            self.logger.info(f"Best model saved to {save_path} with R2: {self.best_score:.4f}")

if __name__ == "__main__":
    trainer = ModelTrainer()
    trainer.train()
