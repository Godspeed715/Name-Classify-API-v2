"""
Utility functions for the Name Classification API.

This module provides functions for:
- Processing external API responses for demographic data
- Classifying ages into demographic groups
- Making concurrent requests to multiple demographic APIs
"""

import httpx
import asyncio
import logging

# Configure logging for better error tracking
logger = logging.getLogger(__name__)


def highest_country(data: list) -> dict:
    """
    Find the country with the highest probability from nationalize API response.
    
    Iterates through the list of countries and their probabilities
    to find and return the entry with the maximum probability value.
    
    Args:
        data (list): List of dictionaries containing country data with keys:
            - country_id (str): ISO country code
            - probability (float): Probability value from API
    
    Returns:
        dict: Dictionary containing the country with highest probability
        Format: {'country_id': str, 'probability': float}
    
    Raises:
        ValueError: If data list is empty
        KeyError: If country data doesn't contain expected keys
    """
    try:
        if not data or len(data) == 0:
            raise ValueError("Country data list cannot be empty")
        
        # Initialize with the first country as the highest
        highest_index = 0
        
        # Iterate through remaining countries to find max probability
        for country_index in range(1, len(data)):
            current_probability = data[country_index].get('probability', 0)
            highest_probability = data[highest_index].get('probability', 0)
            
            # Update if current country has higher probability
            if current_probability > highest_probability:
                highest_index = country_index
        
        return data[highest_index]
        
    except (ValueError, KeyError, IndexError) as e:
        logger.error(f"Error finding highest probability country: {e}")
        raise


def age_classify(age: int) -> str:
    """
    Classify an age value into demographic age groups.
    
    Uses standard demographic classification:
    - child: 0-12 years
    - teen: 13-19 years
    - adult: 20-59 years
    - senior: 60+ years
    
    Args:
        age (int): The age value to classify
    
    Returns:
        str: The age group classification
        Possible values: 'child', 'teen', 'adult', 'senior', 'invalid_age'
    """
    try:
        # Validate age is a non-negative integer
        if not isinstance(age, int) or age < 0:
            logger.warning(f"Invalid age value provided: {age}")
            return 'invalid_age'
        
        # Classify age into appropriate group
        if 0 <= age <= 12:
            return 'child'
        elif 13 <= age <= 19:
            return 'teen'
        elif 20 <= age <= 59:
            return 'adult'
        elif age >= 60:
            return 'senior'
        else:
            logger.warning(f"Age {age} does not fall into any classification")
            return 'invalid_age'
            
    except Exception as e:
        logger.error(f"Error classifying age {age}: {e}")
        return 'invalid_age'


async def api_calls(name: str) -> dict:
    """
    Make concurrent API calls to three demographic data providers.
    
    Fetches data from:
    - Genderize.io: Predicts gender based on name
    - Agify.io: Estimates age based on name
    - Nationalize.io: Predicts country of origin based on name
    
    All requests are made asynchronously in parallel for efficiency.
    Includes validation to ensure all APIs returned meaningful data.
    
    Args:
        name (str): The person's name to lookup in demographic APIs
    
    Returns:
        dict: Dictionary containing either:
            - Success case: {'genderize': dict, 'agify': dict, 'nationalize': dict}
            - Error case: {'status': '502', 'message': str}
    
    Error scenarios:
        - Genderize returns null gender or 0 samples
        - Agify returns null age value
        - Nationalize returns empty country list
    """
    try:
        # Create async HTTP client for making requests
        async with httpx.AsyncClient() as client:
            # Prepare request parameters with the name
            params = {'name': name}
            
            # Create three concurrent requests to demographic APIs
            task_1 = client.get('https://api.genderize.io/', params=params)
            task_2 = client.get('https://api.agify.io/', params=params)
            task_3 = client.get('https://api.nationalize.io/', params=params)
            
            # Wait for all requests to complete concurrently
            genderize_response, agify_response, nationalize_response = await asyncio.gather(
                task_1, task_2, task_3
            )
            
            # Extract JSON data from responses
            genderize_data = genderize_response.json()
            agify_data = agify_response.json()
            nationalize_data = nationalize_response.json()
            
            logger.info(f"Received API responses for name: {name}")
            
            # Validate genderize data - must have valid gender and sample count
            if (genderize_data.get('gender') is None or 
                genderize_data.get('gender') == 'null' or 
                genderize_data.get('count') == 0):
                error_msg = "Genderize API returned an invalid response"
                logger.warning(f"{error_msg} for name: {name}")
                return {"status": "502", "message": error_msg}
            
            # Validate agify data - must have valid age
            if (agify_data.get('age') is None or 
                agify_data.get('age') == 'null'):
                error_msg = "Agify API returned an invalid response"
                logger.warning(f"{error_msg} for name: {name}")
                return {"status": "502", "message": error_msg}
            
            # Validate nationalize data - must have at least one country
            if (nationalize_data.get('country') is None or 
                len(nationalize_data.get('country', [])) == 0):
                error_msg = "Nationalize API returned an invalid response"
                logger.warning(f"{error_msg} for name: {name}")
                return {"status": "502", "message": error_msg}
            
            # Return successfully compiled demographic data
            return {
                'genderize': genderize_data,
                'agify': agify_data,
                'nationalize': nationalize_data
            }
            
    except asyncio.TimeoutError:
        error_msg = "API requests timed out"
        logger.error(f"{error_msg} for name: {name}")
        return {"status": "502", "message": error_msg}
        
    except httpx.RequestError as e:
        error_msg = f"Failed to connect to demographic APIs: {str(e)}"
        logger.error(f"{error_msg} when looking up name: {name}")
        return {"status": "502", "message": "Failed to reach demographic APIs"}
        
    except Exception as e:
        error_msg = f"Unexpected error in api_calls: {str(e)}"
        logger.error(f"{error_msg} for name: {name}")
        return {"status": "502", "message": "An unexpected error occurred while fetching demographic data"}
