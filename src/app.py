"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from datetime import datetime
import os
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

WEEKDAY_MAP = {
    "monday": "monday",
    "tuesday": "tuesday",
    "wednesday": "wednesday",
    "thursday": "thursday",
    "friday": "friday",
    "saturday": "saturday",
    "sunday": "sunday",
}

SCHEDULE_PATTERN = re.compile(
    r"(?P<days>[^,]+),\s*(?P<start>\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))\s*-\s*"
    r"(?P<end>\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))"
)


def parse_schedule(schedule: str):
    match = SCHEDULE_PATTERN.search(schedule)
    if not match:
        raise ValueError(f"Unable to parse schedule: {schedule}")

    days_part = match.group("days")
    start_time = datetime.strptime(match.group("start").upper(), "%I:%M %p")
    end_time = datetime.strptime(match.group("end").upper(), "%I:%M %p")

    if end_time <= start_time:
        raise ValueError(f"Schedule end time must be after start time: {schedule}")

    days = []
    normalized = days_part.replace(" and ", ",")
    for token in normalized.split(","):
        name = token.strip().rstrip("s").lower()
        if not name:
            continue
        if name not in WEEKDAY_MAP:
            raise ValueError(f"Unknown weekday in schedule: {name}")
        days.append(WEEKDAY_MAP[name])

    if not days:
        raise ValueError(f"No days found in schedule: {schedule}")

    start_minutes = start_time.hour * 60 + start_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute

    return [(day, start_minutes, end_minutes) for day in days]


def schedule_overlap(schedule_a, schedule_b):
    for day_a, start_a, end_a in schedule_a:
        for day_b, start_b, end_b in schedule_b:
            if day_a != day_b:
                continue
            if start_a < end_b and start_b < end_a:
                return True
    return False


# In-memory activity database
activities = {
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
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Validate max participants
    if len(activity["participants"]) >= activity["max_participants"]:
        raise HTTPException(
            status_code=400,
            detail="Activity is full"
        )

    # Validate schedule overlap with other signed-up activities for this student
    try:
        new_schedule = parse_schedule(activity["schedule"])
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    for other_name, other_activity in activities.items():
        if other_name == activity_name:
            continue
        if email not in other_activity["participants"]:
            continue

        try:
            other_schedule = parse_schedule(other_activity["schedule"])
        except ValueError:
            continue

        if schedule_overlap(new_schedule, other_schedule):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Signup would create a schedule conflict with "
                    f"{other_name}."
                )
            )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
