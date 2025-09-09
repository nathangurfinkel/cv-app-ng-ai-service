"""
Pytest configuration and fixtures for AI Service tests.
Follows Single Responsibility Principle - handles only test configuration.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.ai_service import AIService
from app.services.evaluation_service import EvaluationService
from app.services.vectorstore_service import VectorstoreService
from app.services.data_transformation_service import DataTransformationService


@pytest.fixture
def client():
    """Test client for FastAPI application."""
    return TestClient(app)


@pytest.fixture
def mock_ai_service():
    """Mock AI service for testing."""
    mock = Mock(spec=AIService)
    mock.extract_structured_cv_data = AsyncMock(return_value={
        "personal": {"name": "Test User", "email": "test@example.com"},
        "experience": [{"title": "Software Engineer", "company": "Test Corp"}],
        "education": [{"degree": "Bachelor of Science", "school": "Test University"}],
        "skills": {"technical": ["Python", "FastAPI"], "soft": ["Communication"]}
    })
    mock.rephrase_cv_section = AsyncMock(return_value="Rephrased content")
    mock.recommend_template = AsyncMock(return_value={
        "recommended_template": "classic",
        "confidence_score": 0.85,
        "alternatives": ["modern", "functional"]
    })
    return mock


@pytest.fixture
def mock_evaluation_service():
    """Mock evaluation service for testing."""
    mock = Mock(spec=EvaluationService)
    mock.evaluate_cv_complete = AsyncMock(return_value={
        "overall_score": 8.5,
        "strengths": ["Strong technical skills", "Relevant experience"],
        "weaknesses": ["Could improve soft skills"],
        "recommendations": ["Add more quantifiable achievements"]
    })
    mock.evaluate_cv_with_committee = AsyncMock(return_value={
        "committee_analysis": "Overall strong candidate",
        "scores": {"technical": 9, "experience": 8, "communication": 7}
    })
    return mock


@pytest.fixture
def mock_vectorstore_service():
    """Mock vectorstore service for testing."""
    mock = Mock(spec=VectorstoreService)
    mock.create_documents = Mock(return_value=[Mock(page_content="Test content")])
    mock.clear_vectorstore = Mock()
    mock.add_documents = Mock()
    mock.retrieve_documents = Mock(return_value=[Mock(page_content="Retrieved content")])
    return mock


@pytest.fixture
def mock_data_transformation_service():
    """Mock data transformation service for testing."""
    mock = Mock(spec=DataTransformationService)
    mock.transform_ai_data_to_cv_data = Mock(return_value=Mock())
    mock.cv_data_to_dict = Mock(return_value={
        "personal": {"name": "Test User", "email": "test@example.com"},
        "experience": [{"title": "Software Engineer", "company": "Test Corp"}],
        "education": [{"degree": "Bachelor of Science", "school": "Test University"}],
        "skills": {"technical": ["Python", "FastAPI"], "soft": ["Communication"]}
    })
    return mock


@pytest.fixture
def sample_cv_data():
    """Sample CV data for testing."""
    return {
        "personal": {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "+1234567890",
            "location": "New York, NY"
        },
        "professional_summary": "Experienced software engineer with 5+ years of experience",
        "experience": [
            {
                "title": "Senior Software Engineer",
                "company": "Tech Corp",
                "startDate": "2020-01",
                "endDate": "2023-12",
                "description": "Led development of microservices architecture"
            }
        ],
        "education": [
            {
                "degree": "Bachelor of Science in Computer Science",
                "school": "University of Technology",
                "graduationYear": "2019"
            }
        ],
        "skills": {
            "technical": ["Python", "FastAPI", "AWS"],
            "soft": ["Leadership", "Communication"]
        }
    }


@pytest.fixture
def sample_job_description():
    """Sample job description for testing."""
    return """
    We are looking for a Senior Software Engineer with experience in:
    - Python and FastAPI development
    - Microservices architecture
    - AWS cloud services
    - Team leadership
    
    Requirements:
    - 5+ years of software development experience
    - Strong problem-solving skills
    - Excellent communication skills
    """


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
