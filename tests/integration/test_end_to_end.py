"""
End-to-end integration tests for AI Service.
Follows Single Responsibility Principle - tests complete workflows.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app


class TestEndToEndWorkflows:
    """Test class for end-to-end workflows following Single Responsibility Principle."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @patch('app.routes.cv_routes.ai_service')
    @patch('app.routes.cv_routes.vectorstore_service')
    @patch('app.routes.cv_routes.data_transformation_service')
    @patch('app.routes.cv_routes.evaluation_service')
    def test_complete_cv_tailoring_workflow(self, mock_eval, mock_transform, mock_vector, mock_ai, client):
        """Test complete CV tailoring workflow from start to finish."""
        # Arrange
        mock_ai.extract_structured_cv_data = AsyncMock(return_value={
            "personal": {"name": "John Doe", "email": "john@example.com"},
            "experience": [{"title": "Software Engineer", "company": "Tech Corp"}],
            "education": [{"degree": "Bachelor of Science", "school": "University"}],
            "skills": {"technical": ["Python", "FastAPI"], "soft": ["Communication"]}
        })
        
        mock_transform.transform_ai_data_to_cv_data.return_value = Mock()
        mock_transform.cv_data_to_dict.return_value = {
            "personal": {"name": "John Doe", "email": "john@example.com"},
            "experience": [{"title": "Software Engineer", "company": "Tech Corp"}],
            "education": [{"degree": "Bachelor of Science", "school": "University"}],
            "skills": {"technical": ["Python", "FastAPI"], "soft": ["Communication"]}
        }
        
        mock_vector.create_documents.return_value = [Mock(page_content="Test content")]
        mock_vector.retrieve_documents.return_value = [Mock(page_content="Retrieved content")]
        mock_eval.evaluate_cv_complete = AsyncMock(return_value={
            "overall_score": 8.5,
            "strengths": ["Strong technical skills"],
            "weaknesses": ["Could improve soft skills"],
            "recommendations": ["Add more quantifiable achievements"]
        })
        
        request_data = {
            "cv_text": "John Doe, Software Engineer with 5 years experience in Python and FastAPI",
            "job_description": "Looking for a Senior Software Engineer with Python and FastAPI experience"
        }
        
        # Act
        response = client.post("/ai/cv/tailor", json=request_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "personal" in data
        assert "experience" in data
        assert "education" in data
        assert "skills" in data
        assert "analysis" in data
        assert data["analysis"]["overall_score"] == 8.5

    @patch('app.routes.cv_routes.ai_service')
    @patch('app.routes.cv_routes.vectorstore_service')
    @patch('app.routes.cv_routes.data_transformation_service')
    @patch('app.routes.cv_routes.evaluation_service')
    def test_cv_data_extraction_workflow(self, mock_eval, mock_transform, mock_vector, mock_ai, client):
        """Test CV data extraction workflow."""
        # Arrange
        mock_ai.extract_structured_cv_data = AsyncMock(return_value={
            "personal": {"name": "Jane Smith", "email": "jane@example.com"},
            "experience": [{"title": "Data Scientist", "company": "Data Corp"}],
            "education": [{"degree": "Master of Science", "school": "Tech University"}],
            "skills": {"technical": ["Python", "Machine Learning"], "soft": ["Analytical Thinking"]}
        })
        
        mock_transform.transform_ai_data_to_cv_data.return_value = Mock()
        mock_transform.cv_data_to_dict.return_value = {
            "personal": {"name": "Jane Smith", "email": "jane@example.com"},
            "experience": [{"title": "Data Scientist", "company": "Data Corp"}],
            "education": [{"degree": "Master of Science", "school": "Tech University"}],
            "skills": {"technical": ["Python", "Machine Learning"], "soft": ["Analytical Thinking"]}
        }
        
        mock_vector.create_documents.return_value = [Mock(page_content="Test content")]
        mock_vector.retrieve_documents.return_value = [Mock(page_content="Retrieved content")]
        mock_eval.evaluate_cv_complete = AsyncMock(return_value={
            "overall_score": 9.0,
            "strengths": ["Excellent technical skills", "Strong analytical background"],
            "weaknesses": [],
            "recommendations": ["Consider adding more leadership experience"]
        })
        
        request_data = {
            "cv_text": "Jane Smith, Data Scientist with expertise in Python and Machine Learning",
            "job_description": "Looking for a Data Scientist with Python and ML experience"
        }
        
        # Act
        response = client.post("/ai/cv/extract-cv-data", json=request_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["personal"]["name"] == "Jane Smith"
        assert data["personal"]["email"] == "jane@example.com"
        assert len(data["experience"]) == 1
        assert data["experience"][0]["title"] == "Data Scientist"
        assert "Python" in data["skills"]["technical"]
        assert "Machine Learning" in data["skills"]["technical"]

    @patch('app.routes.cv_routes.ai_service')
    def test_rephrase_section_workflow(self, mock_ai, client):
        """Test CV section rephrasing workflow."""
        # Arrange
        mock_ai.rephrase_cv_section = AsyncMock(return_value="Experienced software engineer with 5+ years of expertise in developing scalable web applications using Python and FastAPI")
        
        request_data = {
            "section_content": "I am a software engineer with 5 years of experience",
            "section_type": "professional_summary",
            "job_description": "Looking for a Senior Software Engineer with Python and FastAPI experience"
        }
        
        # Act
        response = client.post("/ai/cv/rephrase-section", json=request_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["original_content"] == "I am a software engineer with 5 years of experience"
        assert "Experienced software engineer" in data["rephrased_content"]
        assert data["section_type"] == "professional_summary"

    @patch('app.routes.cv_routes.ai_service')
    def test_template_recommendation_workflow(self, mock_ai, client):
        """Test template recommendation workflow."""
        # Arrange
        mock_ai.recommend_template = AsyncMock(return_value={
            "recommended_template": "modern",
            "confidence_score": 0.92,
            "alternatives": ["classic", "functional"],
            "reasoning": "Modern template best suits the technical nature of the role"
        })
        
        request_data = {
            "job_description": "Looking for a Senior Software Engineer with Python and FastAPI experience",
            "cv_data": {
                "personal": {"name": "John Doe"},
                "experience": [{"title": "Software Engineer", "company": "Tech Corp"}],
                "skills": {"technical": ["Python", "FastAPI", "AWS"]}
            }
        }
        
        # Act
        response = client.post("/ai/cv/recommend-template", json=request_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["recommended_template"] == "modern"
        assert data["confidence_score"] == 0.92
        assert "classic" in data["alternatives"]
        assert "functional" in data["alternatives"]

    @patch('app.routes.evaluation_routes.evaluation_service')
    def test_evaluation_workflow(self, mock_eval, client):
        """Test CV evaluation workflow."""
        # Arrange
        mock_eval.evaluate_cv_with_committee = AsyncMock(return_value={
            "committee_analysis": "Strong candidate with excellent technical skills and relevant experience",
            "scores": {
                "technical": 9,
                "experience": 8,
                "communication": 7,
                "overall": 8.5
            },
            "recommendations": [
                "Consider adding more leadership examples",
                "Highlight specific achievements with metrics"
            ]
        })
        
        request_data = {
            "job_description": "Looking for a Senior Software Engineer with Python and FastAPI experience",
            "cv_json": {
                "personal": {"name": "John Doe", "email": "john@example.com"},
                "experience": [{"title": "Software Engineer", "company": "Tech Corp"}],
                "skills": {"technical": ["Python", "FastAPI", "AWS"]}
            }
        }
        
        # Act
        response = client.post("/ai/evaluation/cv", json=request_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "committee_analysis" in data
        assert "scores" in data
        assert data["scores"]["technical"] == 9
        assert data["scores"]["overall"] == 8.5
        assert len(data["recommendations"]) == 2

