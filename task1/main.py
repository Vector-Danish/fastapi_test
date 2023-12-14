import psycopg2
from fastapi import FastAPI, HTTPException,Path
from pymongo import MongoClient
from pydantic import BaseModel

DB_CONFIG = {
    "dbname": "user_registration",
    "user": "postgres",
    "password": "password",
    "host": "localhost",
    "port": "5432",
}

mongo_client = MongoClient("mongodb://localhost:27017")
mongo_db = mongo_client["profile_pictures"]

app = FastAPI()

class User(BaseModel):
    full_name: str
    email: str
    password: str
    phone: str
    profile_picture: str

@app.post("/register/")
async def register_user(entry: User):
    """
    Register a new user with the provided user details.

    Parameters:
    - entry (User): The user details to be registered, including full_name, email, password, phone, and profile_picture.

    Returns:
    - dict: A dictionary containing a detail message indicating the success of the user registration.

    Raises:
    - HTTPException: If the email is already registered, a 400 Bad Request error is raised.
    """
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM users WHERE email = %s", (entry.email,))
        user_exist = cursor.fetchone()

        if user_exist:
            raise HTTPException(status_code=400, detail="Email already registered")

        cursor.execute(
            "INSERT INTO users (full_name, email, password, phone) VALUES (%s, %s, %s, %s) RETURNING *",
            (entry.full_name, entry.email, entry.password, entry.phone),
        )
        user_data = cursor.fetchone()

        user_profile = {"user_id": user_data[0], "profile_picture": entry.profile_picture}
        mongo_db.profile_pictures.insert_one(user_profile)

        conn.commit()
        return {"detail": "User registration successfull"}
    finally:
        cursor.close()
        conn.close()


@app.get("/user/{user_id}")
async def get_user_info(user_id: int):
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user_data = cursor.fetchone()

        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")

        mongo_query = {"user_id": user_id}
        profile_picture = mongo_db.profile_pictures.find_one(mongo_query)

        response = {
            "full_name": user_data[1],
            "email": user_data[2],
            "phone": user_data[4],
            "profile_picture": profile_picture["profile_picture"] if profile_picture else None,
        }

        return response
    finally:
        cursor.close()
        conn.close()
    