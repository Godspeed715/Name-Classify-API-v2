# Imported libraries
from flask import Flask, jsonify, request
from flask_cors import CORS
import uuid
from db import *
from datetime import datetime, timezone
from my_functions import *
import psycopg
import asyncio
import logging

# Configure logging for better error tracking
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection
conn = psycopg.connect('postgresql://postgres:1234@localhost:5432/postgres')

# Creates the Flask app
app = Flask(__name__)

# To prevent alphabetic sorting of JSON data
app.json.sort_keys = False

# Add cors setting to allow requests from all origins
CORS(app, origins=["*"])


@app.route('/api/profiles', methods=['POST'])
def post_data():
    """
    Handle POST request to create a new profile.
    
    Validates the input name, fetches data from external APIs (genderize, agify, nationalize),
    classifies the data, and stores it in the database.
    
    Returns:
        JSON response with status and profile data or error message
    """
    try:
        # Gets JSON data from post request
        data = request.get_json()
        
        # Validate request data exists
        if not data:
            return jsonify({
                'status': 'error', 
                'message': 'Request body is required (Bad Request)'
            }), 400
        
        name: str = data.get('name')
        
        # Validate name is provided and not empty
        if name is None or len(name.strip()) == 0:
            return jsonify({
                'status': 'error', 
                'message': 'Name field is required and cannot be empty (Bad Request)'
            }), 400
        
        # Validate name contains only alphabetic characters
        if not name.strip().replace(" ", "").isalpha():
            return jsonify({
                'status': 'error', 
                'message': 'Name must contain only letters (Unprocessable Entity)'
            }), 422
        
        # Call external APIs to fetch demographic data
        api_data = asyncio.run(api_calls(name))
        
        # Check if API call was unsuccessful
        if api_data.get('status') == '502':
            return jsonify({
                'status': 'error',
                'message': api_data.get('message')
            }), 502
        
        # Extract age from API response
        age = api_data.get('agify').get('age')
        
        # Get country data with the highest probability
        country_data = highest_country(api_data.get('nationalize').get('country'))
        
        # Build response data object
        response_data = {
            'id': str(uuid.uuid7()),
            'name': name.strip(),
            'gender': api_data.get('genderize').get('gender'),
            'gender_probability': api_data.get('genderize').get('probability'),
            'sample_size': api_data.get('genderize').get('count'),
            'age': age,
            'age_group': age_classify(age),
            'country_id': country_data.get('country_id'),
            'country_probability': country_data.get('probability'),
            'created_at': datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        
        # Store data in database
        try:
            # create_table(conn)
            insert_name_data(conn, response_data)
        except psycopg.Error as db_error:
            logger.error(f"Database error during insert: {db_error}")
            return jsonify({
                'status': 'error', 
                'message': 'Error storing profile in database (Internal Server Error)'
            }), 500
        except ValueError as e:
            return jsonify({
                'status': 'success',
                'message': 'Profile already exists',
                'data': str(e)
            })
        
        # Return successful response
        return jsonify({
            'status': 'success',
            'data': response_data
        }), 201
        
    except Exception as e:
        logger.error(f"Unexpected error in post_data: {e}")
        return jsonify({
            'status': 'error', 
            'message': 'An unexpected error occurred (Internal Server Error)'
        }), 500


@app.route('/api/profiles/<string:id>', methods=['GET'])
def get_with_id(id):
    """
    Retrieve a profile by ID.
    
    Queries the database for a profile matching the provided UUID and returns
    the complete profile data in a structured format.
    
    Args:
        id (str): The UUID of the profile to retrieve
    
    Returns:
        JSON response with profile data or appropriate error message
    """
    try:
        # Validate ID format is not empty
        if not id or len(id.strip()) == 0:
            return jsonify({
                'status': 'error',
                'message': 'Profile ID is required (Bad Request)'
            }), 400
        
        # Fetch profile data from database
        data = get_name_data_with_id(conn, id)
        
        # Check if profile was found
        if data is None:
            return jsonify({
                'status': 'error',
                'message': f'Profile with ID {id} not found (Not Found)'
            }), 404
        
        # Structure response data from database record
        response_data = {
            'id': str(data[0]),
            'name': data[1],
            'gender': data[2],
            'gender_probability': float(data[3]),
            'sample_size': data[4],
            'age': data[5],
            'age_group': data[6],
            'country_id': data[7],
            'country_probability': float(data[8]),
            'created_at': data[9]
        }
        
        return jsonify({
            'status': 'success',
            'data': response_data
        }), 200
        
    except psycopg.Error as db_error:
        logger.error(f"Database error in get_with_id: {db_error}")
        return jsonify({
            'status': 'error',
            'message': 'Error retrieving profile from database (Internal Server Error)'
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error in get_with_id: {e}")
        return jsonify({
            'status': 'error',
            'message': 'An unexpected error occurred (Internal Server Error)'
        }), 500


@app.route('/api/profiles', methods=['GET'])
def get_with_optional():
    """
    Retrieve profiles with optional filtering parameters.
    
    Supports filtering by gender, country_id, and/or age_group.
    If no parameters are provided, returns all profiles.
    
    Query Parameters:
        gender (str, optional): Filter by gender (e.g., 'male', 'female')
        country_id (str, optional): Filter by country ID (e.g., 'US', 'GB')
        age_group (str, optional): Filter by age group (e.g., 'child', 'teen', 'adult', 'senior')
    
    Returns:
        JSON response with list of matching profiles or appropriate error message
    """
    try:
        # Extract optional filter parameters from query string
        gender = request.args.get('gender', default=None, type=str)
        country_id = request.args.get('country_id', default=None, type=str)
        age_group = request.args.get('age_group', default=None, type=str)
        
        # Validate age_group parameter if provided
        valid_age_groups = ['child', 'teen', 'adult', 'senior']
        if age_group and age_group not in valid_age_groups:
            return jsonify({
                'status': 'error',
                'message': f'Invalid age_group. Must be one of: {", ".join(valid_age_groups)} (Unprocessable Entity)'
            }), 422
        
        # Query database with optional filters
        profiles = get_name_with_optional(conn, {
            'gender': gender, 
            'country_id': country_id, 
            'age_group': age_group
        })
        
        # Check if any profiles were found
        if not profiles:
            return jsonify({
                'status': 'success',
                'data': [],
                'count': 0,
                'message': 'No profiles found matching the criteria'
            }), 200
        
        # Structure profile data for response
        response_data = []
        for profile in profiles:
            response_data.append({
                'id': str(profile[0]),
                'name': profile[1],
                'gender': profile[2],
                'gender_probability': float(profile[3]),
                'sample_size': profile[4],
                'age': profile[5],
                'age_group': profile[6],
                'country_id': profile[7],
                'country_probability': float(profile[8]),
                'created_at': profile[9]
            })
        
        return jsonify({
            'status': 'success',
            'data': response_data,
            'count': len(response_data)
        }), 200
        
    except psycopg.Error as db_error:
        logger.error(f"Database error in get_with_optional: {db_error}")
        return jsonify({
            'status': 'error',
            'message': 'Error retrieving profiles from database (Internal Server Error)'
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error in get_with_optional: {e}")
        return jsonify({
            'status': 'error',
            'message': 'An unexpected error occurred (Internal Server Error)'
        }), 500


# Error Handling in Routes
@app.errorhandler(400)
def bad_request(e):
    """Handle 400 Bad Request errors"""
    return jsonify({
        'status': 'error', 
        'message': 'Bad Request. Check your input data.'
    }), 400


@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 Not Found errors"""
    return jsonify({
        'status': 'error', 
        'message': 'Endpoint not found. Check your URL.'
    }), 404


@app.errorhandler(422)
def unprocessable_entity(e):
    """Handle 422 Unprocessable Entity errors"""
    return jsonify({
        'status': 'error', 
        'message': 'Unprocessable Entity. Please check your request data.'
    }), 422


@app.errorhandler(500)
def internal_server_error(e):
    """Handle 500 Internal Server errors"""
    logger.error(f"Internal server error: {e}")
    return jsonify({
        'status': 'error', 
        'message': 'Internal Server Error. Please try again later.'
    }), 500


@app.errorhandler(502)
def bad_gateway(e):
    """Handle 502 Bad Gateway errors"""
    return jsonify({
        'status': 'error', 
        'message': 'Service temporarily unavailable. Please try again later.'
    }), 502


if __name__ == '__main__':
    app.run(debug=True)

