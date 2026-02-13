from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from datetime import datetime, timedelta
import traceback
import math

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

# Vedic Astrology Constants
NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira",
    "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
    "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati",
    "Vishakha", "Anuradha", "Jyeshta", "Mula", "Purva Ashadha",
    "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
    "Uttara Bhadrapada", "Revati"
]

RASIS = [
    "Mesha", "Vrishabha", "Mithuna", "Karka", "Simha",
    "Kanya", "Tula", "Vrischika", "Dhanu", "Makara",
    "Kumbha", "Meena"
]

RASI_LORDS = [
    "Mangal", "Shukra", "Budha", "Chandra", "Surya",
    "Budha", "Shukra", "Mangal", "Guru", "Shani",
    "Shani", "Guru"
]

NAKSHATRA_LORDS = [
    "Ketu", "Shukra", "Surya", "Chandra", "Mangal",
    "Rahu", "Guru", "Shani", "Budha", "Ketu",
    "Shukra", "Surya", "Chandra", "Mangal", "Rahu",
    "Guru", "Shani", "Budha", "Ketu", "Shukra",
    "Surya", "Chandra", "Mangal", "Rahu", "Guru",
    "Shani", "Budha"
]

TITHIS = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima/Amavasya"
]

YOGAS = [
    "Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana",
    "Atiganda", "Sukarma", "Dhriti", "Shula", "Ganda",
    "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra",
    "Siddhi", "Sadhya", "Shubha", "Shukla", "Brahma",
    "Indra", "Vaidhriti", "Parigha", "Shiva", "Siddha",
    "Sadhaka", "Vimala"
]

def calculate_julian_day(year, month, day, hour, minute, second):
    """Calculate Julian Day Number"""
    if month <= 2:
        year -= 1
        month += 12
    
    A = year // 100
    B = 2 - A + (A // 4)
    
    JD = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + B - 1524.5
    JD += (hour + minute/60 + second/3600) / 24
    
    return JD

def calculate_sun_position(jd):
    """Calculate Sun's position (simplified)"""
    T = (jd - 2451545.0) / 36525.0
    L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T * T
    M = 357.52911 + 35999.05029 * T - 0.0001536 * T * T
    
    M_rad = math.radians(M)
    C = (1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(M_rad)
    C += (0.019993 - 0.000101 * T) * math.sin(2 * M_rad)
    C += 0.000029 * math.sin(3 * M_rad)
    
    sun_lon = (L0 + C) % 360
    return sun_lon

def calculate_moon_position(jd):
    """Calculate Moon's position (simplified)"""
    T = (jd - 2451545.0) / 36525.0
    
    Lp = 218.3164477 + 481267.88123421 * T - 0.0015786 * T * T + T * T * T / 538841 - T * T * T * T / 65194000
    D = 297.8501921 + 445267.1114034 * T - 0.0018819 * T * T + T * T * T / 545868 - T * T * T * T / 113065000
    M = 357.52910918 + 35999.0502909 * T - 0.0001536 * T * T + T * T * T / 24490000
    Mp = 134.9633964 + 477198.8675055 * T + 0.0087414 * T * T + T * T * T / 69699 - T * T * T * T / 14712000
    F = 93.2720950 + 483202.0175233 * T - 0.0036539 * T * T - T * T * T / 3526000 + T * T * T * T / 863310000
    
    A1 = 119.75 + 131.849 * T
    A2 = 72.56 + 20.186 * T
    
    moon_lon = (Lp + 6.28875 * math.sin(math.radians(Mp)) + 1.27402 * math.sin(math.radians(2*D - Mp)) +
                0.65892 * math.sin(math.radians(2*D)) + 0.21908 * math.sin(math.radians(2*Mp)) +
                0.14753 * math.sin(math.radians(D)) + 0.14120 * math.sin(math.radians(Mp - D))) % 360
    
    return moon_lon

def apply_ayanamsa(longitude, ayanamsa_value=23.638333):
    """Apply Ayanamsa to convert Sayana to Nirayana"""
    nirayana = (longitude - ayanamsa_value) % 360
    return nirayana

def get_nakshatra(moon_lon):
    """Get Nakshatra from Moon longitude"""
    nak_index = int(moon_lon / 13.333333)
    nak_index = min(nak_index, 26)
    pada = int((moon_lon % 13.333333) / 3.333333) + 1
    return NAKSHATRAS[nak_index], nak_index + 1, pada, NAKSHATRA_LORDS[nak_index]

def get_rasi(longitude):
    """Get Rasi from longitude"""
    rasi_index = int(longitude / 30)
    rasi_index = min(rasi_index, 11)
    return RASIS[rasi_index], rasi_index + 1, RASI_LORDS[rasi_index]

def get_tithi(sun_lon, moon_lon):
    """Get Tithi from Sun and Moon positions"""
    elongation = (moon_lon - sun_lon) % 360
    tithi_index = int(elongation / 12)
    tithi_index = min(tithi_index, 14)
    
    paksha = "Suklapaksha" if tithi_index < 15 else "Krishnapaksha"
    
    return TITHIS[tithi_index], tithi_index + 1, paksha

def get_yoga(sun_lon, moon_lon):
    """Get Yoga from Sun and Moon positions"""
    yoga_sum = (sun_lon + moon_lon) % 360
    yoga_index = int(yoga_sum / 13.333333)
    yoga_index = min(yoga_index, 26)
    return YOGAS[yoga_index], yoga_index + 1

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
        
        # Parse birth details
        birth_date = data.get('birth_date')  # Format: YYYY-MM-DD
        birth_time = data.get('birth_time')  # Format: HH:MM:SS
        timezone = float(data.get('timezone', 5.5))
        latitude = float(data.get('latitude', 0))
        longitude = float(data.get('longitude', 0))
        
        # Parse date and time
        date_parts = birth_date.split('-')
        time_parts = birth_time.split(':')
        
        year = int(date_parts[0])
        month = int(date_parts[1])
        day = int(date_parts[2])
        hour = int(time_parts[0])
        minute = int(time_parts[1])
        second = int(time_parts[2]) if len(time_parts) > 2 else 0
        
        # Adjust for timezone
        hour_utc = hour - timezone
        
        # Calculate Julian Day
        jd = calculate_julian_day(year, month, day, hour_utc, minute, second)
        log_calculation("JULIAN_DAY", {"jd": jd})
        
        # Calculate planetary positions
        sun_sayana = calculate_sun_position(jd)
        moon_sayana = calculate_moon_position(jd)
        
        log_calculation("SAYANA_POSITIONS", {
            "sun_sayana": sun_sayana,
            "moon_sayana": moon_sayana
        })
        
        # Apply Ayanamsa (Chitra Paksha = 23.638333)
        ayanamsa_value = 23.638333
        sun_nirayana = apply_ayanamsa(sun_sayana, ayanamsa_value)
        moon_nirayana = apply_ayanamsa(moon_sayana, ayanamsa_value)
        
        log_calculation("NIRAYANA_POSITIONS", {
            "sun_nirayana": sun_nirayana,
            "moon_nirayana": moon_nirayana,
            "ayanamsa_applied": ayanamsa_value
        })
        
        # Calculate Nakshatra
        nak_name, nak_num, pada, nak_lord = get_nakshatra(moon_nirayana)
        log_calculation("NAKSHATRA", {
            "name": nak_name,
            "number": nak_num,
            "pada": pada,
            "lord": nak_lord
        })
        
        # Calculate Rasi
        rasi_name, rasi_num, rasi_lord = get_rasi(moon_nirayana)
        log_calculation("RASI", {
            "name": rasi_name,
            "number": rasi_num,
            "lord": rasi_lord
        })
        
        # Calculate Tithi
        tithi_name, tithi_num, paksha = get_tithi(sun_nirayana, moon_nirayana)
        log_calculation("TITHI", {
            "name": tithi_name,
            "number": tithi_num,
            "paksha": paksha
        })
        
        # Calculate Yoga
        yoga_name, yoga_num = get_yoga(sun_nirayana, moon_nirayana)
        log_calculation("YOGA", {
            "name": yoga_name,
            "number": yoga_num
        })
        
        # Calculate Lagna (simplified - using time-based calculation)
        lagna_lon = (sun_nirayana + (hour * 15)) % 360
        lagna_name, lagna_num, lagna_lord = get_rasi(lagna_lon)
        log_calculation("LAGNA", {
            "name": lagna_name,
            "number": lagna_num,
            "lord": lagna_lord,
            "longitude": lagna_lon
        })
        
        result = {
            "name": data.get('name'),
            "sex": data.get('sex'),
            "birth_date": birth_date,
            "birth_time": birth_time,
            "timezone": timezone,
            "latitude": latitude,
            "longitude": longitude,
            "ayanamsa": "Chitra Paksha",
            
            "tithi": {
                "name": tithi_name,
                "number": tithi_num,
                "paksha": paksha
            },
            
            "lagna": {
                "sign": lagna_name,
                "lord": lagna_lord,
                "degrees": lagna_lon
            },
            
            "rasi": {
                "sign": rasi_name,
                "lord": rasi_lord
            },
            
            "nakshatra": {
                "name": nak_name,
                "number": nak_num,
                "lord": nak_lord,
                "pada": pada
            },
            
            "yoga": {
                "name": yoga_name,
                "number": yoga_num
            },
            
            "planets": {
                "sun": {"longitude": sun_nirayana, "sign": get_rasi(sun_nirayana)[0]},
                "moon": {"longitude": moon_nirayana, "sign": get_rasi(moon_nirayana)[0]}
            }
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
