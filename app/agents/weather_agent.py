from typing import Dict
import numpy as np
from sklearn.ensemble import RandomForestRegressor


class WeatherAnalysisAgent:
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100)
        
    
    def train(self, historical_data:Dict):
        x = np.array([[d['month'], d['latitude'], d['longitude']] for d in historical_data])
        
        y = np.array([d['weather_score'] for d in historical_data])
        self.model.fit(x, y)
    
    def predict_best_time(self, location: Dict) -> Dict:
        #predicts the best time to visit a location based on weather patterns
        predictions = []
        for month in range(1,13):
            
            prediction = self.model.predict([[
                month,
                location['latitude'],
                location['longitude']
            ]]).item()

            predictions.append({'month': month, 'score': float(prediction)}) 
        
        return {
            'best_months': sorted(predictions, key=lambda x: x['score'], reverse=True)[:3],
            'location': location
        }