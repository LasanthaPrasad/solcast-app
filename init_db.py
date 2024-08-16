import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', '').replace('postgres://', 'postgresql://')
db = SQLAlchemy(app)

# Define models
class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    api_key = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Location {self.name}>'

# Function to recreate database and add sample data
def init_db():
    with app.app_context():
        # Drop all tables
        db.drop_all()
        
        # Create all tables
        db.create_all()
        
        # Add sample data
        sample_locations = [
            Location(name='New York', api_key='sample_key_1', latitude=40.7128, longitude=-74.0060),
            Location(name='London', api_key='sample_key_2', latitude=51.5074, longitude=-0.1278),
            Location(name='Tokyo', api_key='sample_key_3', latitude=35.6762, longitude=139.6503),
            Location(name='Sydney', api_key='sample_key_4', latitude=-33.8688, longitude=151.2093),
            Location(name='Rio de Janeiro', api_key='sample_key_5', latitude=-22.9068, longitude=-43.1729)
        ]
        
        # Add sample locations to the database
        for location in sample_locations:
            db.session.add(location)
        
        # Commit the changes
        db.session.commit()
        
        print("Database initialized with sample data.")

if __name__ == '__main__':
    init_db()