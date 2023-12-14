import psycopg2
from fastapi import FastAPI, HTTPException, Path
from typing import Optional
from pydantic import BaseModel

DB_CONFIG = {
    "dbname": "user_registration",
    "user": "postgres",
    "password": "password",
    "host": "localhost",
    "port": "5432",
}

app = FastAPI()

class UserDetails(BaseModel):
    full_name: str
    email: str
    phone: str
    password: str
    profile_picture: str

def create_tables():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                id SERIAL PRIMARY KEY,
                full_name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                phone INT UNIQUE NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Profiles (
                id SERIAL PRIMARY KEY,
                profile_picture VARCHAR(255) NOT NULL
            )
        """)

        conn.commit()
    finally:
        cursor.close()
        conn.close()

@app.post("/register/")
async def register_user(entry: UserDetails):
    """
    Register a new user with the provided user details.

    Parameters:
    - entry (UserDetails): The user details to be registered, including full_name, email, password, phone, and profile_picture.

    Returns:
    - dict: A dictionary containing a detail message indicating the success of the user registration.

    Raises:
    - HTTPException: If the email or phone is already registered, a 400 Bad Request error is raised.
    """
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM Users WHERE email = %s OR phone = %s", (entry.email, entry.phone))
        existing_user = cursor.fetchone()

        if existing_user:
            raise HTTPException(status_code=400, detail="Email or phone already registered")

        cursor.execute("""
            INSERT INTO Users (full_name, email, password, phone) 
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (entry.full_name, entry.email, entry.password, entry.phone))

        user_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO Profiles (id, profile_picture) VALUES (%s, %s)
        """, (user_id, entry.profile_picture))

        conn.commit()
        return {"detail": "User registration successful"}
    finally:
        cursor.close()
        conn.close()
        
create_tables()

@app.get("/user/{user_id}")
async def get_user_details(user_id: int):
    """
    Retrieve details of a user based on the provided user ID.

    Parameters:
    - user_id (int): The unique identifier of the user.

    Returns:
    - dict: A dictionary containing user details, including full_name, email, phone, and profile_picture.

    Raises:
    - HTTPException: If the user with the specified ID is not found, a 404 Not Found error is raised.
    """
    query = """
        SELECT u.id, u.full_name, u.email, u.phone, p.profile_picture
        FROM Users u
        LEFT JOIN Profiles p ON u.id = p.id
        WHERE u.id = %s
    """

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, (user_id,))
            user_details = cursor.fetchone()

            if not user_details:
                raise HTTPException(status_code=404, detail="User not found")

            user_data = {
                "full_name": user_details[1],
                "email": user_details[2],
                "phone": user_details[3],
                "profile_picture": user_details[4],
            }

            return user_data
    finally:
        conn.close()
