import pandas as pd
import numpy as np
import os

def generate_dataset(num_samples=500):
    np.random.seed(42)
    
    # Generate synthetic features
    study_hours = np.random.normal(loc=5, scale=2, size=num_samples)
    study_hours = np.clip(study_hours, 0, 15)  # Clip between 0 and 15 hours
    
    attendance = np.random.randint(50, 100, size=num_samples) # Percentage
    
    average_sleep_hours = np.random.normal(loc=7, scale=1.5, size=num_samples)
    average_sleep_hours = np.clip(average_sleep_hours, 4, 10)
    
    previous_grade = np.random.normal(loc=70, scale=15, size=num_samples)
    previous_grade = np.clip(previous_grade, 0, 100)
    
    participation_score = np.random.randint(0, 100, size=num_samples)
    
    # Points based on engagement (Simulated LMS points)
    points = (study_hours * 10) + (attendance * 2) + (participation_score * 0.5) + np.random.normal(0, 10, num_samples)
    points = np.clip(points, 0, 500)

    # Generate target variable (Final Grade) with some noise
    # Formula: Base + (Study * 1.5) + (Attendance * 0.2) + (Sleep * 0.5) + (PrevGrade * 0.6) + (Points * 0.05) + Noise
    final_grade = (
        5 + 
        (study_hours * 2.0) + 
        (attendance * 0.2) + 
        (previous_grade * 0.4) + 
        (participation_score * 0.05) +
        (points * 0.05) +
        np.random.normal(0, 5, num_samples) # Noise
    )
    
    final_grade = np.clip(final_grade, 0, 100)
    
    # Create DataFrame
    data = pd.DataFrame({
        'StudyHours': study_hours,
        'Attendance': attendance,
        'SleepHours': average_sleep_hours,
        'PreviousGrade': previous_grade,
        'Participation': participation_score,
        'Points': points,
        'FinalGrade': final_grade
    })
    
    # Save to CSV
    os.makedirs('data', exist_ok=True)
    file_path = 'data/student_performance.csv'
    data.to_csv(file_path, index=False)
    print(f"Dataset generated and saved to {file_path}")
    return data

if __name__ == "__main__":
    generate_dataset()
