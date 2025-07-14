"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# MongoDB connection
MONGODB_URL = "mongodb://localhost:27017"
DATABASE_NAME = "mergington_school"
COLLECTION_NAME = "activities"

try:
    client = MongoClient(MONGODB_URL)
    # Test the connection
    client.admin.command('ping')
    db = client[DATABASE_NAME]
    activities_collection = db[COLLECTION_NAME]
    logger.info("Successfully connected to MongoDB")
except ConnectionFailure:
    logger.error("Failed to connect to MongoDB")
    raise Exception("Could not connect to MongoDB")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# Initial data to populate MongoDB
initial_activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    # Sports related activities
    "Soccer Team": {
        "description": "Join the school soccer team and compete in local leagues",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 18,
        "participants": ["lucas@mergington.edu", "mia@mergington.edu"]
    },
    "Basketball Club": {
        "description": "Practice basketball skills and play friendly matches",
        "schedule": "Wednesdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["liam@mergington.edu", "ava@mergington.edu"]
    },
    # Artistic activities
    "Art Club": {
        "description": "Explore painting, drawing, and other visual arts",
        "schedule": "Mondays, 3:30 PM - 5:00 PM",
        "max_participants": 16,
        "participants": ["ella@mergington.edu", "noah@mergington.edu"]
    },
    "Drama Society": {
        "description": "Participate in theater productions and acting workshops",
        "schedule": "Fridays, 4:00 PM - 6:00 PM",
        "max_participants": 20,
        "participants": ["amelia@mergington.edu", "benjamin@mergington.edu"]
    },
    # Intellectual activities
    "Math Olympiad": {
        "description": "Prepare for math competitions and solve challenging problems",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 10,
        "participants": ["charlotte@mergington.edu", "jack@mergington.edu"]
    },
    "Science Club": {
        "description": "Conduct experiments and explore scientific concepts",
        "schedule": "Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 14,
        "participants": ["henry@mergington.edu", "grace@mergington.edu"]
    }
}

def populate_database():
    """Populate the database with initial activities if it's empty"""
    try:
        # Check if collection is empty
        if activities_collection.count_documents({}) == 0:
            logger.info("Database is empty. Populating with initial data...")
            
            # Convert dictionary to list of documents with activity_name as a field
            documents = []
            for activity_name, activity_data in initial_activities.items():
                doc = {
                    "activity_name": activity_name,
                    **activity_data
                }
                documents.append(doc)
            
            # Insert all documents
            result = activities_collection.insert_many(documents)
            logger.info(f"Inserted {len(result.inserted_ids)} activities into database")
        else:
            logger.info("Database already contains data. Skipping population.")
    except Exception as e:
        logger.error(f"Error populating database: {e}")

# Populate database on startup
populate_database()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    """Get all activities from MongoDB"""
    try:
        # Fetch all activities from MongoDB
        activities_cursor = activities_collection.find()
        activities = {}
        
        for activity_doc in activities_cursor:
            activity_name = activity_doc["activity_name"]
            # Remove MongoDB-specific fields and activity_name from the response
            activity_data = {k: v for k, v in activity_doc.items() 
                           if k not in ["_id", "activity_name"]}
            activities[activity_name] = activity_data
        
        return activities
    except Exception as e:
        logger.error(f"Error fetching activities: {e}")
        raise HTTPException(status_code=500, detail="Error fetching activities")


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    try:
        # Find the activity
        activity = activities_collection.find_one({"activity_name": activity_name})
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        # Check if student is already signed up
        if email in activity["participants"]:
            raise HTTPException(status_code=400, detail="Already signed up for this activity")

        # Check if activity is full
        if len(activity["participants"]) >= activity["max_participants"]:
            raise HTTPException(status_code=400, detail="Activity is full")

        # Add student to the activity
        result = activities_collection.update_one(
            {"activity_name": activity_name},
            {"$push": {"participants": email}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to sign up")
        
        return {"message": f"Signed up {email} for {activity_name}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error signing up for activity: {e}")
        raise HTTPException(status_code=500, detail="Error signing up for activity")


@app.delete("/activities/{activity_name}/participants/{email}")
def remove_participant(activity_name: str, email: str):
    """Remove a participant from an activity"""
    try:
        # Find the activity
        activity = activities_collection.find_one({"activity_name": activity_name})
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        # Check if participant is enrolled
        if email not in activity["participants"]:
            raise HTTPException(status_code=404, detail="Participant not found in this activity")

        # Remove participant from the activity
        result = activities_collection.update_one(
            {"activity_name": activity_name},
            {"$pull": {"participants": email}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to remove participant")
        
        return {"message": f"Removed {email} from {activity_name}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing participant: {e}")
        raise HTTPException(status_code=500, detail="Error removing participant")
