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
    resource_id = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    capacity = db.Column(db.Float, nullable=False)
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
        
        # Add new location
        new_location = Location(
            name='Sample Location',
            resource_id='6b0d-76b6-82d2-22b0',
            latitude=-33.865143,  # Example latitude for Sydney, Australia
            longitude=151.209900,  # Example longitude for Sydney, Australia
            capacity=5000.0  # Example capacity in kW
        )
        
        # Add new location to the database
        db.session.add(new_location)
        
        # Commit the changes
        db.session.commit()
        
        print("Database initialized with new location.")
        print(f"Added: {new_location}")

if __name__ == '__main__':
    init_db()