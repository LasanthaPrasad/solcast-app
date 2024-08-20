import os
from flask import Flask, render_template, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
import solcast
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime
from solcast import forecast
from solcast.unmetered_locations import UNMETERED_LOCATIONS
sydney = UNMETERED_LOCATIONS['Sydney Opera House']



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', '').replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    api_key = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Location {self.name}>'

def get_forecast_data(api_key, latitude, longitude):
    solcast.api_key = api_key
    # forecasts = solcast.get_radiation_forecasts(latitude, longitude)
    forecasts = solcast.rooftop_pv_power(
    latitude=sydney['latitude'], 
    longitude=sydney['longitude'],
    period='PT5M',
    capacity=5,  # 5KW
    tilt=22,  # degrees
    output_parameters='pv_power_rooftop'
    )
    df = pd.DataFrame(forecasts)



    return df

def generate_forecast_plot(df):
    plt.figure(figsize=(12, 6))
    plt.plot(df['period_end'], df['ghi'], label='GHI')
    plt.plot(df['period_end'], df['air_temp'], label='Air Temperature')
    plt.plot(df['period_end'], df['ghi_clear_sky'], label='Clear Sky GHI')
    plt.xlabel('Time')
    plt.ylabel('Value')
    plt.title('Forecast Data')
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
        api_key=data['api_key'],
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
    location.api_key = data['api_key']
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
        'api_key': location.api_key,
        'latitude': location.latitude,
        'longitude': location.longitude
    })

@app.route('/forecast/<int:id>')
def forecast(id):
    location = Location.query.get_or_404(id)
    try:
        df = get_forecast_data(location.api_key, location.latitude, location.longitude)
        plot_url = generate_forecast_plot(df)
        return render_template('forecast.html', location=location, plot_url=plot_url)
    except Exception as e:
        app.logger.error(f"Error generating forecast for location {id}: {str(e)}")
        abort(500, description="Error generating forecast. Please check the API key and try again.")

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