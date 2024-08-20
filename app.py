import os
from flask import Flask, render_template, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
import requests
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', '').replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

SOLCAST_API_KEY = os.environ.get('SOLCAST_API_KEY')

class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    resource_id = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Location {self.name}>'

def get_forecast_data(resource_id):
    url = f"https://api.solcast.com.au/pv_power/forecasts?resource_id={resource_id}&api_key={SOLCAST_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data['forecasts'])
        df['period_end'] = pd.to_datetime(df['period_end'])
        return df
    else:
        raise Exception(f"Failed to fetch data: {response.status_code}")

def generate_forecast_plot(df):
    plt.figure(figsize=(12, 6))
    plt.plot(df['period_end'], df['pv_estimate'], label='PV Estimate')
    plt.xlabel('Time')
    plt.ylabel('PV Power (kW)')
    plt.title('PV Power Forecast')
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    return base64.b64encode(img.getvalue()).decode()

@app.route('/')
def index():
    locations = Location.query.all()
    return render_template('index.html', locations=locations)

@app.route('/add_location', methods=['POST'])
def add_location():
    data = request.json
    new_location = Location(
        name=data['name'],
        resource_id=data['resource_id'],
        latitude=data['latitude'],
        longitude=data['longitude']
    )
    db.session.add(new_location)
    db.session.commit()
    return jsonify({'message': 'Location added successfully', 'id': new_location.id}), 201

@app.route('/update_location/<int:id>', methods=['PUT'])
def update_location(id):
    location = Location.query.get_or_404(id)
    data = request.json
    location.name = data['name']
    location.resource_id = data['resource_id']
    location.latitude = data['latitude']
    location.longitude = data['longitude']
    db.session.commit()
    return jsonify({'message': 'Location updated successfully'})

@app.route('/delete_location/<int:id>', methods=['DELETE'])
def delete_location(id):
    location = Location.query.get_or_404(id)
    db.session.delete(location)
    db.session.commit()
    return jsonify({'message': 'Location deleted successfully'})

@app.route('/get_location/<int:id>')
def get_location(id):
    location = Location.query.get_or_404(id)
    return jsonify({
        'id': location.id,
        'name': location.name,
        'resource_id': location.resource_id,
        'latitude': location.latitude,
        'longitude': location.longitude
    })

@app.route('/forecast/<int:id>')
def forecast(id):
    location = Location.query.get_or_404(id)
    try:
        df = get_forecast_data(location.resource_id)
        plot_url = generate_forecast_plot(df)
        return render_template('forecast.html', location=location, plot_url=plot_url)
    except Exception as e:
        app.logger.error(f"Error generating forecast for location {id}: {str(e)}")
        abort(500, description="Error generating forecast. Please check the resource ID and try again.")

@app.route('/locations')
def list_locations():
    locations = Location.query.all()
    return jsonify([{
        'id': loc.id,
        'name': loc.name,
        'latitude': loc.latitude,
        'longitude': loc.longitude
    } for loc in locations])

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error=str(e)), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False)