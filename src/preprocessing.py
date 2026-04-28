import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib
import os
from src.utils import load_config, get_logger

class DataProcessor:
    def __init__(self):
        self.config = load_config()
        self.logger = get_logger(__name__)
        self.scaler = StandardScaler()
        
    def load_data(self):
        """Loads data from the path specified in config."""
        path = os.path.join(self.config['directories']['data'], self.config['files']['dataset'])
        try:
            df = pd.read_csv(path)
            self.logger.info(f"Data loaded successfully from {path}. Shape: {df.shape}")
            return df
        except FileNotFoundError:
            self.logger.error(f"File not found: {path}")
            raise

    def feature_engineering(self, df):
        """Adds new features to the dataset."""
        self.logger.info("Starting feature engineering...")
        
        # Example: Engagement Score (Weighted sum of attendance and participation)
        df['EngagementScore'] = (df['Attendance'] * 0.6) + (df['Participation'] * 0.4)
        
        # Example: Studious Ratio (Study Hours / Sleep Hours) - Avoid division by zero
        df['StudiousRatio'] = df['StudyHours'] / (df['SleepHours'] + 0.1)
        
        self.logger.info("Feature engineering completed.")
        return df

    def preprocess(self, df):
        """Standard preprocessing pipeline."""
        target_col = self.config['features']['target']
        
        X = df.drop(target_col, axis=1)
        y = df[target_col]
        
        # Split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Scale
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Save scaler
        save_path = os.path.join(self.config['directories']['models'], self.config['files']['scaler'])
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        joblib.dump(self.scaler, save_path)
        self.logger.info(f"Scaler saved to {save_path}")
        
        return X_train_scaled, X_test_scaled, y_train, y_test

if __name__ == "__main__":
    dp = DataProcessor()
    df = dp.load_data()
    df = dp.feature_engineering(df)
    X_tr, X_te, y_tr, y_te = dp.preprocess(df)
