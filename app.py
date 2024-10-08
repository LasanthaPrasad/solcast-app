import os
from flask import Flask, render_template, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
import requests
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', '').replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

SOLCAST_API_KEY = os.environ.get('SOLCAST_API_KEY')
SOLCAST_BASE_URL = "https://api.solcast.com.au"

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

def get_forecast_data(resource_id):
    url = f"{SOLCAST_BASE_URL}/world_pv_power/forecasts?resource_id={resource_id}&api_key={SOLCAST_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data['forecasts'])
        df['period_end'] = pd.to_datetime(df['period_end'])
        return df
    else:
        raise Exception(f"Failed to fetch data: {response.status_code}")

def get_estimated_actuals(resource_id):
    end_date = datetime.now(pytz.UTC)
    start_date = end_date - timedelta(days=7)
    url = f"{SOLCAST_BASE_URL}/world_pv_power/estimated_actuals?resource_id={resource_id}&start={start_date.isoformat()}&end={end_date.isoformat()}&api_key={SOLCAST_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data['estimated_actuals'])
        df['period_end'] = pd.to_datetime(df['period_end'])
        return df
    else:
        raise Exception(f"Failed to fetch estimated actuals: {response.status_code}")

def generate_forecast_plot(forecast_df, actuals_df, capacity):
    plt.figure(figsize=(12, 6))
    plt.plot(forecast_df['period_end'], forecast_df['pv_estimate']/capacity*100, label='Forecast')
    plt.plot(actuals_df['period_end'], actuals_df['pv_estimate']/capacity*100, label='Estimated Actuals')
    plt.xlabel('Time')
    plt.ylabel('PV Power (% of capacity)')
    plt.title('PV Power Forecast and Estimated Actuals')
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
        longitude=data['longitude'],
        capacity=data['capacity']
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
    location.capacity = data['capacity']
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
        'longitude': location.longitude,
        'capacity': location.capacity
    })

@app.route('/forecast/<int:id>')
def forecast(id):
    location = Location.query.get_or_404(id)
    try:
        forecast_df = get_forecast_data(location.resource_id)
        actuals_df = get_estimated_actuals(location.resource_id)
        plot_url = generate_forecast_plot(forecast_df, actuals_df, location.capacity)
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
        'longitude': loc.longitude,
        'capacity': loc.capacity
    } for loc in locations])



@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error=str(e)), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False)

    