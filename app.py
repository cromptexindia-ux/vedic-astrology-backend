from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from datetime import datetime
import traceback
from pyjhora.models import HoroModel
from pyjhora.utils import convert_to_dms
import pyswisseph as swe

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store calculation logs
calculation_logs = []

def log_calculation(step, data):
    """Log calculation steps"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "step": step,
        "data": data
    }
    calculation_logs.append(log_entry)
    logger.info(f"{step}: {data}")

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "Backend is running"}), 200

@app.route('/api/calculate-birth-chart', methods=['POST'])
def calculate_birth_chart():
    """Calculate complete birth chart"""
    try:
        data = request.json
        
        # Log input
        log_calculation("INPUT", {
            "name": data.get('name'),
            "sex": data.get('sex'),
            "birth_date": data.get('birth_date'),
            "birth_time": data.get('birth_time'),
            "timezone": data.get('timezone'),
            "latitude": data.get('latitude'),
            "longitude": data.get('longitude'),
            "ayanamsa": data.get('ayanamsa', 'Chitra Paksha')
        })
        
        # Create HoroModel from pyjhora
        horo = HoroModel(
            name=data.get('name'),
            sex=data.get('sex'),
            birth_date=data.get('birth_date'),
            birth_time=data.get('birth_time'),
            timezone=data.get('timezone'),
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            ayanamsa=data.get('ayanamsa', 'Chitra Paksha')
        )
        
        log_calculation("HORO_MODEL_CREATED", {"status": "HoroModel initialized"})
        
        # Extract all calculations
        result = {
            "name": horo.name,
            "sex": horo.sex,
            "birth_date": str(horo.birth_date),
            "birth_time": str(horo.birth_time),
            "timezone": horo.timezone,
            "latitude": horo.latitude,
            "longitude": horo.longitude,
            "ayanamsa": horo.ayanamsa,
            
            # Tithi (Lunar Day)
            "tithi": {
                "name": horo.tithi[0] if horo.tithi else "Unknown",
                "number": horo.tithi[1] if len(horo.tithi) > 1 else 0,
                "paksha": horo.tithi_paksha if hasattr(horo, 'tithi_paksha') else "Unknown"
            },
            
            # Lagna (Ascendant)
            "lagna": {
                "sign": horo.lagna[0] if horo.lagna else "Unknown",
                "lord": horo.lagna_lord if hasattr(horo, 'lagna_lord') else "Unknown",
                "degrees": horo.lagna_degrees if hasattr(horo, 'lagna_degrees') else 0
            },
            
            # Rasi (Moon Sign)
            "rasi": {
                "sign": horo.rasi[0] if horo.rasi else "Unknown",
                "lord": horo.rasi_lord if hasattr(horo, 'rasi_lord') else "Unknown"
            },
            
            # Nakshatra (Birth Star)
            "nakshatra": {
                "name": horo.nakshatra[0] if horo.nakshatra else "Unknown",
                "number": horo.nakshatra[1] if len(horo.nakshatra) > 1 else 0,
                "lord": horo.nakshatra_lord if hasattr(horo, 'nakshatra_lord') else "Unknown",
                "pada": horo.nakshatra_pada if hasattr(horo, 'nakshatra_pada') else 0
            },
            
            # Yoga
            "yoga": {
                "name": horo.yoga[0] if horo.yoga else "Unknown",
                "number": horo.yoga[1] if len(horo.yoga) > 1 else 0
            },
            
            # Karanam
            "karanam": horo.karanam if hasattr(horo, 'karanam') else "Unknown",
            
            # Planetary Positions
            "planets": get_planetary_positions(horo),
            
            # Karakas
            "karakas": get_karakas(horo),
            
            # Arudhas
            "arudhas": get_arudhas(horo)
        }
        
        log_calculation("BIRTH_CHART_CALCULATED", {"status": "Complete"})
        
        return jsonify({
            "success": True,
            "data": result,
            "logs": calculation_logs
        }), 200
        
    except Exception as e:
        error_msg = f"Error calculating birth chart: {str(e)}\n{traceback.format_exc()}"
        log_calculation("ERROR", error_msg)
        logger.error(error_msg)
        return jsonify({
            "success": False,
            "error": str(e),
            "logs": calculation_logs
        }), 400

@app.route('/api/calculate-tithi', methods=['POST'])
def calculate_tithi():
    """Calculate Tithi (Lunar Day)"""
    try:
        data = request.json
        
        log_calculation("TITHI_CALCULATION_START", data)
        
        horo = HoroModel(
            name="Temp",
            sex="M",
            birth_date=data.get('birth_date'),
            birth_time=data.get('birth_time'),
            timezone=data.get('timezone'),
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            ayanamsa=data.get('ayanamsa', 'Chitra Paksha')
        )
        
        # Get Sun and Moon positions
        sun_pos = horo.sun_position if hasattr(horo, 'sun_position') else 0
        moon_pos = horo.moon_position if hasattr(horo, 'moon_position') else 0
        
        log_calculation("PLANETARY_POSITIONS", {
            "sun_longitude": sun_pos,
            "moon_longitude": moon_pos
        })
        
        result = {
            "tithi_name": horo.tithi[0] if horo.tithi else "Unknown",
            "tithi_number": horo.tithi[1] if len(horo.tithi) > 1 else 0,
            "paksha": horo.tithi_paksha if hasattr(horo, 'tithi_paksha') else "Unknown",
            "sun_longitude": sun_pos,
            "moon_longitude": moon_pos
        }
        
        log_calculation("TITHI_CALCULATED", result)
        
        return jsonify({
            "success": True,
            "data": result,
            "logs": calculation_logs
        }), 200
        
    except Exception as e:
        error_msg = f"Error calculating Tithi: {str(e)}"
        log_calculation("ERROR", error_msg)
        return jsonify({
            "success": False,
            "error": str(e),
            "logs": calculation_logs
        }), 400

@app.route('/api/calculate-lagna', methods=['POST'])
def calculate_lagna():
    """Calculate Lagna (Ascendant)"""
    try:
        data = request.json
        
        log_calculation("LAGNA_CALCULATION_START", data)
        
        horo = HoroModel(
            name="Temp",
            sex="M",
            birth_date=data.get('birth_date'),
            birth_time=data.get('birth_time'),
            timezone=data.get('timezone'),
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            ayanamsa=data.get('ayanamsa', 'Chitra Paksha')
        )
        
        result = {
            "lagna_sign": horo.lagna[0] if horo.lagna else "Unknown",
            "lagna_lord": horo.lagna_lord if hasattr(horo, 'lagna_lord') else "Unknown",
            "lagna_degrees": horo.lagna_degrees if hasattr(horo, 'lagna_degrees') else 0
        }
        
        log_calculation("LAGNA_CALCULATED", result)
        
        return jsonify({
            "success": True,
            "data": result,
            "logs": calculation_logs
        }), 200
        
    except Exception as e:
        error_msg = f"Error calculating Lagna: {str(e)}"
        log_calculation("ERROR", error_msg)
        return jsonify({
            "success": False,
            "error": str(e),
            "logs": calculation_logs
        }), 400

@app.route('/api/get-logs', methods=['GET'])
def get_logs():
    """Get all calculation logs"""
    return jsonify({
        "logs": calculation_logs
    }), 200

@app.route('/api/clear-logs', methods=['POST'])
def clear_logs():
    """Clear calculation logs"""
    global calculation_logs
    calculation_logs = []
    return jsonify({"status": "Logs cleared"}), 200

def get_planetary_positions(horo):
    """Extract planetary positions"""
    planets = {}
    
    planet_names = ['sun', 'moon', 'mars', 'mercury', 'jupiter', 'venus', 'saturn', 'rahu', 'ketu']
    
    for planet in planet_names:
        try:
            position = getattr(horo, f'{planet}_position', None)
            sign = getattr(horo, f'{planet}_sign', None)
            if position:
                planets[planet] = {
                    "longitude": position,
                    "sign": sign
                }
        except:
            pass
    
    return planets

def get_karakas(horo):
    """Extract Karakas"""
    karakas = {}
    
    try:
        karakas['atma_karaka'] = horo.atma_karaka if hasattr(horo, 'atma_karaka') else "Unknown"
        karakas['amatya_karaka'] = horo.amatya_karaka if hasattr(horo, 'amatya_karaka') else "Unknown"
    except:
        pass
    
    return karakas

def get_arudhas(horo):
    """Extract Arudhas"""
    arudhas = {}
    
    try:
        arudhas['lagna_aruda'] = horo.lagna_aruda if hasattr(horo, 'lagna_aruda') else "Unknown"
        arudhas['dhana_aruda'] = horo.dhana_aruda if hasattr(horo, 'dhana_aruda') else "Unknown"
    except:
        pass
    
    return arudhas

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
