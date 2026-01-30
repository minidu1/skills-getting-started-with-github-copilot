"""
Tests for the Mergington High School API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add the src directory to the path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities

# Create a test client
client = TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store original state
    original_activities = {
        k: {"participants": list(v["participants"]), **{kk: vv for kk, vv in v.items() if kk != "participants"}}
        for k, v in activities.items()
    }
    yield
    # Restore original state
    for activity_name in activities:
        activities[activity_name]["participants"] = original_activities[activity_name]["participants"]


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_activities_returns_all_activities(self, reset_activities):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        assert "Soccer Team" in data
        assert "Basketball Club" in data

    def test_get_activities_has_correct_structure(self, reset_activities):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        data = response.json()
        activity = data["Soccer Team"]
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity
        assert isinstance(activity["participants"], list)

    def test_get_activities_includes_participants(self, reset_activities):
        """Test that activities include participants"""
        response = client.get("/activities")
        data = response.json()
        soccer = data["Soccer Team"]
        assert len(soccer["participants"]) > 0
        assert "lucas@mergington.edu" in soccer["participants"]


class TestSignup:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_new_student(self, reset_activities):
        """Test signing up a new student for an activity"""
        response = client.post(
            "/activities/Soccer Team/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == 200
        assert "Signed up" in response.json()["message"]
        assert "newstudent@mergington.edu" in activities["Soccer Team"]["participants"]

    def test_signup_duplicate_student(self, reset_activities):
        """Test that a student cannot sign up twice"""
        # First signup
        client.post(
            "/activities/Soccer Team/signup",
            params={"email": "duplicate@mergington.edu"}
        )
        # Try to sign up again
        response = client.post(
            "/activities/Soccer Team/signup",
            params={"email": "duplicate@mergington.edu"}
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_invalid_activity(self, reset_activities):
        """Test signing up for a non-existent activity"""
        response = client.post(
            "/activities/NonexistentActivity/signup",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_signup_already_existing_student(self, reset_activities):
        """Test that existing participants cannot sign up again"""
        response = client.post(
            "/activities/Soccer Team/signup",
            params={"email": "lucas@mergington.edu"}
        )
        assert response.status_code == 400


class TestUnregister:
    """Tests for POST /activities/{activity_name}/unregister endpoint"""

    def test_unregister_existing_student(self, reset_activities):
        """Test unregistering an existing student"""
        # Verify student is enrolled
        assert "lucas@mergington.edu" in activities["Soccer Team"]["participants"]
        
        response = client.post(
            "/activities/Soccer Team/unregister",
            params={"email": "lucas@mergington.edu"}
        )
        assert response.status_code == 200
        assert "Removed" in response.json()["message"]
        assert "lucas@mergington.edu" not in activities["Soccer Team"]["participants"]

    def test_unregister_non_enrolled_student(self, reset_activities):
        """Test unregistering a student who is not enrolled"""
        response = client.post(
            "/activities/Soccer Team/unregister",
            params={"email": "notstudent@mergington.edu"}
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]

    def test_unregister_invalid_activity(self, reset_activities):
        """Test unregistering from a non-existent activity"""
        response = client.post(
            "/activities/NonexistentActivity/unregister",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_unregister_then_can_signup_again(self, reset_activities):
        """Test that a student can sign up again after unregistering"""
        email = "reusable@mergington.edu"
        
        # Sign up
        client.post(
            "/activities/Basketball Club/signup",
            params={"email": email}
        )
        assert email in activities["Basketball Club"]["participants"]
        
        # Unregister
        client.post(
            "/activities/Basketball Club/unregister",
            params={"email": email}
        )
        assert email not in activities["Basketball Club"]["participants"]
        
        # Sign up again
        response = client.post(
            "/activities/Basketball Club/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        assert email in activities["Basketball Club"]["participants"]


class TestRoot:
    """Tests for root endpoint"""

    def test_root_redirects_to_static(self, reset_activities):
        """Test that root redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"
