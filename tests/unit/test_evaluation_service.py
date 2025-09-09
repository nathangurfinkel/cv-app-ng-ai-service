"""
Unit tests for Evaluation Service.
Follows Single Responsibility Principle - tests only evaluation functionality.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.services.evaluation_service import EvaluationService
from app.services.ai_service import AIService


class TestEvaluationService:
    """Test class for Evaluation Service following Single Responsibility Principle."""

    @pytest.fixture
    def mock_ai_service(self):
        """Create mock AI service for testing."""
        mock = Mock(spec=AIService)
        return mock

    @pytest.fixture
    def evaluation_service(self, mock_ai_service):
        """Create evaluation service instance for testing."""
        return EvaluationService(mock_ai_service)

    @pytest.mark.asyncio
    async def test_evaluate_cv_with_committee_success(self, evaluation_service, mock_ai_service):
        """Test successful committee evaluation."""
        # Arrange
        job_description = "Looking for a software engineer"
        cv_content = '{"personal": {"name": "John Doe"}}'
        
        mock_ai_service.client.chat.completions.create = AsyncMock()
        mock_ai_service.client.chat.completions.create.return_value.choices = [Mock()]
        mock_ai_service.client.chat.completions.create.return_value.choices[0].message.content = '{"committee_analysis": "Strong candidate"}'
        
        # Act
        result = await evaluation_service.evaluate_cv_with_committee(job_description, cv_content)
        
        # Assert
        assert "committee_analysis" in result
        mock_ai_service.client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_evaluate_cv_complete_success(self, evaluation_service, mock_ai_service):
        """Test successful complete CV evaluation."""
        # Arrange
        job_description = "Looking for a software engineer"
        cv_json = '{"personal": {"name": "John Doe"}}'
        retrieved_docs = [Mock(page_content="Relevant experience")]
        
        mock_ai_service.client.chat.completions.create = AsyncMock()
        mock_ai_service.client.chat.completions.create.return_value.choices = [Mock()]
        mock_ai_service.client.chat.completions.create.return_value.choices[0].message.content = '{"overall_score": 8.5}'
        
        # Act
        result = await evaluation_service.evaluate_cv_complete(job_description, cv_json, retrieved_docs)
        
        # Assert
        assert "overall_score" in result
        mock_ai_service.client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_evaluate_cv_with_committee_handles_error(self, evaluation_service, mock_ai_service):
        """Test that committee evaluation handles errors gracefully."""
        # Arrange
        job_description = "Test job"
        cv_content = "Test CV"
        
        mock_ai_service.client.chat.completions.create = AsyncMock()
        mock_ai_service.client.chat.completions.create.side_effect = Exception("API Error")
        
        # Act & Assert
        with pytest.raises(Exception, match="API Error"):
            await evaluation_service.evaluate_cv_with_committee(job_description, cv_content)

    def test_initialization_with_ai_service(self, mock_ai_service):
        """Test that evaluation service initializes with AI service."""
        # Act
        service = EvaluationService(mock_ai_service)
        
        # Assert
        assert service.ai_service == mock_ai_service
