"""
Database module for Name Classification API.

This module handles all database operations including:
- Table creation for storing profile data
- Insert operations for new profiles
- Retrieve operations for profiles by ID or filters
- Delete operations for profile records
"""
import os

import psycopg
import logging
from psycopg import Error as PsycopgError

# Configure logging for better error tracking
logger = logging.getLogger(__name__)

# Database connection URI
DB_URI = os.environ.get('DB_URI')


def create_table(conn):
    """
    Create the name_classify_db table if it doesn't already exist.
    
    The table stores demographic profile information including basic details,
    API response data, and timestamps.
    
    Args:
        conn: PostgreSQL database connection object
    
    Raises:
        psycopg.Error: If database operation fails
    """
    try:
        with conn.cursor() as cur:
            # SQL command to create table with proper data types and constraints
            table_query = '''
                CREATE TABLE IF NOT EXISTS name_classify_db(
                    id UUID PRIMARY KEY UNIQUE DEFAULT uuid_generate_v4(),
                    name TEXT NOT NULL,
                    gender TEXT NOT NULL,
                    gender_probability DECIMAL NOT NULL,
                    sample_size INT NOT NULL,
                    age INT NOT NULL,
                    age_group TEXT NOT NULL,
                    country_id TEXT NOT NULL,
                    country_probability DECIMAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
                )
            '''
            cur.execute(table_query)
            conn.commit()
            logger.info("Table created or already exists")
    except PsycopgError as e:
        logger.error(f"Error creating table: {e}")
        conn.rollback()
        raise


def insert_name_data(conn, data: dict):
    """
    Insert a new profile record into the database.
    
    Before insertion, checks if the record already exists to prevent duplicates.
    
    Args:
        conn: PostgreSQL database connection object
        data (dict): Dictionary containing profile data with keys:
            - id, name, gender, gender_probability, sample_size,
              age, age_group, country_id, country_probability, created_at
    
    Returns:
        None on success, 2 if record already exists
    
    Raises:
        psycopg.Error: If database operation fails
    """
    try:
        # Check if profile already exists to prevent duplicates
        if already_added(conn, data.get('name')):
            print('already there')
            logger.warning(f"Profile with Name: {data.get('name')} already exists in database")
            raise ValueError({
                'message': 'Profile already exists',
                'data': get_name_data_with_id(data.get('id'))
            })
        
        # Insert profile data into database
        with conn.cursor() as cur:
            insert_query = '''
                INSERT INTO name_classify_db
                (id, name, gender, gender_probability, sample_size, age, age_group, 
                 country_id, country_probability, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            '''
            
            # Execute insert with values in the correct order
            cur.execute(insert_query, tuple(data.values()))
            conn.commit()
            logger.info(f"Profile {data.get('id')} successfully inserted")
            
    except PsycopgError as e:
        logger.error(f"Error inserting profile data: {e}")
        conn.rollback()
        raise


def already_added(conn, name):
    """
    Check if a profile with the given ID already exists in the database.
    
    Args:
        conn: PostgreSQL database connection object
        id (str): The UUID of the profile to check
    
    Returns:
        bool: True if profile exists, False otherwise
    
    Raises:
        psycopg.Error: If database operation fails
    """
    try:
        with conn.cursor() as cur:
            # Query to check if profile exists
            query = '''
                SELECT 1 FROM name_classify_db
                WHERE name = %s
                LIMIT 1
            '''
            cur.execute(query, (name,))
            exists = cur.fetchone() is not None
            
        return exists
        
    except PsycopgError as e:
        logger.error(f"Error checking if profile exists: {e}")
        raise


def get_name_data_with_id(conn, id):
    """
    Retrieve a complete profile record by its UUID.
    
    Args:
        conn: PostgreSQL database connection object
        id (str): The UUID of the profile to retrieve
    
    Returns:
        tuple: A tuple containing all profile fields, or None if not found
        Fields: (id, name, gender, gender_probability, sample_size,
                 age, age_group, country_id, country_probability, created_at)
    
    Raises:
        psycopg.Error: If database operation fails
    """
    try:
        with conn.cursor() as cur:
            # Query to fetch profile by ID with all fields
            get_query = '''
                SELECT id, name, gender, gender_probability, sample_size, age,
                       age_group, country_id, country_probability, created_at
                FROM name_classify_db
                WHERE id = %s
            '''
            
            cur.execute(get_query, (id,))
            data = cur.fetchone()
            
        return data
        
    except PsycopgError as e:
        logger.error(f"Error retrieving profile with ID {id}: {e}")
        raise


def get_name_with_optional(conn, arg: dict):
    """
    Retrieve profiles with optional filtering parameters.
    
    Supports filtering by gender, country_id, and/or age_group.
    If no parameters are provided, returns all profiles.
    
    Args:
        conn: PostgreSQL database connection object
        arg (dict): Dictionary with optional filter keys:
            - gender: Filter by gender value
            - country_id: Filter by country ID
            - age_group: Filter by age group
            None values are ignored in the filter
    
    Returns:
        list: List of tuples, each containing a profile record
        Returns empty list if no profiles match the criteria
    
    Raises:
        psycopg.Error: If database operation fails
    """
    try:
        # Filter out None values to build dynamic WHERE clause
        valid_args = {k: v for k, v in arg.items() if v is not None}
        
        # Base query to fetch all profile fields
        query = '''
            SELECT id, name, gender, gender_probability, sample_size, age,
                   age_group, country_id, country_probability, created_at
            FROM name_classify_db
        '''
        
        # Build WHERE clause if there are valid filter arguments
        if valid_args:
            # Create conditions for each filter parameter
            conditions = [f"{key} = %({key})s" for key in valid_args.keys()]
            where_clause = " AND ".join(conditions)
            query += f" WHERE {where_clause}"
        
        logger.info(f"Executing query with filters: {valid_args}")
        
        with conn.cursor() as cur:
            # Execute the query with the filter parameters
            cur.execute(query, valid_args)
            response = cur.fetchall()
        
        return response
        
    except PsycopgError as e:
        logger.error(f"Error retrieving profiles with filters {arg}: {e}")
        raise


def delete_name_data(conn, id):
    """
    Delete a profile record by its UUID.
    
    Args:
        conn: PostgreSQL database connection object
        id (str): The UUID of the profile to delete
    
    Raises:
        psycopg.Error: If database operation fails
    """
    try:
        with conn.cursor() as cur:
            # Query to delete profile by ID
            delete_query = '''
                DELETE FROM name_classify_db
                WHERE id = %s
            '''
            
            cur.execute(delete_query, (id,))
            conn.commit()
            
            # Log the number of rows deleted
            rows_deleted = cur.rowcount
            if rows_deleted > 0:
                logger.info(f"Profile {id} successfully deleted")
            else:
                logger.warning(f"No profile found with ID {id} to delete")
                
    except PsycopgError as e:
        logger.error(f"Error deleting profile with ID {id}: {e}")
        conn.rollback()
        raise
