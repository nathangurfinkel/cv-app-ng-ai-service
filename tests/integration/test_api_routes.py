"""
Integration tests for API routes.
Follows Single Responsibility Principle - tests only API route functionality.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app


class TestAPIRoutes:
    """Test class for API routes following Single Responsibility Principle."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_health_check(self, client):
        """Test health check endpoint."""
        # Act
        response = client.get("/")
        
        # Assert
        assert response.status_code == 200
        assert response.json()["status"] == "CV Builder AI Service is online"

    def test_health_endpoint(self, client):
        """Test dedicated health endpoint."""
        # Act
        response = client.get("/health")
        
        # Assert
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    @patch('app.routes.cv_routes.ai_service')
    @patch('app.routes.cv_routes.vectorstore_service')
    @patch('app.routes.cv_routes.data_transformation_service')
    @patch('app.routes.cv_routes.evaluation_service')
    def test_extract_cv_data_success(self, mock_eval, mock_transform, mock_vector, mock_ai, client):
        """Test successful CV data extraction endpoint."""
        # Arrange
        mock_ai.extract_structured_cv_data = AsyncMock(return_value={"personal": {"name": "John Doe"}})
        mock_transform.transform_ai_data_to_cv_data.return_value = Mock()
        mock_transform.cv_data_to_dict.return_value = {"personal": {"name": "John Doe"}}
        mock_vector.create_documents.return_value = [Mock(page_content="Test")]
        mock_vector.retrieve_documents.return_value = [Mock(page_content="Retrieved")]
        mock_eval.evaluate_cv_complete = AsyncMock(return_value={"overall_score": 8.5})
        
        request_data = {
            "cv_text": "John Doe, Software Engineer",
            "job_description": "Looking for a software engineer"
        }
        
        # Act
        response = client.post("/ai/cv/extract-cv-data", json=request_data)
        
        # Assert
        assert response.status_code == 200
        assert "personal" in response.json()

    @patch('app.routes.cv_routes.ai_service')
    def test_rephrase_section_success(self, mock_ai, client):
        """Test successful CV section rephrasing endpoint."""
        # Arrange
        mock_ai.rephrase_cv_section = AsyncMock(return_value="Rephrased content")
        
        request_data = {
            "section_content": "I am a software engineer",
            "section_type": "professional_summary",
            "job_description": "Looking for a senior developer"
        }
        
        # Act
        response = client.post("/ai/cv/rephrase-section", json=request_data)
        
        # Assert
        assert response.status_code == 200
        assert response.json()["rephrased_content"] == "Rephrased content"

    @patch('app.routes.cv_routes.ai_service')
    def test_recommend_template_success(self, mock_ai, client):
        """Test successful template recommendation endpoint."""
        # Arrange
        mock_ai.recommend_template = AsyncMock(return_value={
            "recommended_template": "classic",
            "confidence_score": 0.85
        })
        
        request_data = {
            "job_description": "Looking for a software engineer",
            "cv_data": {"experience": [{"title": "Software Engineer"}]}
        }
        
        # Act
        response = client.post("/ai/cv/recommend-template", json=request_data)
        
        # Assert
        assert response.status_code == 200
        assert response.json()["recommended_template"] == "classic"

    @patch('app.routes.evaluation_routes.evaluation_service')
    def test_evaluate_cv_success(self, mock_eval, client):
        """Test successful CV evaluation endpoint."""
        # Arrange
        mock_eval.evaluate_cv_with_committee = AsyncMock(return_value={
            "committee_analysis": "Strong candidate"
        })
        
        request_data = {
            "job_description": "Looking for a software engineer",
            "cv_json": {"personal": {"name": "John Doe"}}
        }
        
        # Act
        response = client.post("/ai/evaluation/cv", json=request_data)
        
        # Assert
        assert response.status_code == 200
        assert "committee_analysis" in response.json()


    def test_extract_cv_data_validation_error(self, client):
        """Test CV data extraction with validation error."""
        # Arrange
        request_data = {
            "cv_text": "",  # Empty CV text should cause validation error
            "job_description": "Looking for a software engineer"
        }
        
        # Act
        response = client.post("/ai/cv/extract-cv-data", json=request_data)
        
        # Assert
        assert response.status_code == 422  # Validation error

    def test_rephrase_section_validation_error(self, client):
        """Test rephrase section with validation error."""
        # Arrange
        request_data = {
            "section_content": "",  # Empty content should cause validation error
            "section_type": "professional_summary",
            "job_description": "Looking for a senior developer"
        }
        
        # Act
        response = client.post("/ai/cv/rephrase-section", json=request_data)
        
        # Assert
        assert response.status_code == 422  # Validation error
