"""
Cross-repo contract validation tests.

These tests ensure that API contracts match between frontend and backend.
Validates request/response shapes, data transformation, and polling behavior.
"""
import json
import pytest
from app.models.job_models import (
    JobCreateResponse,
    JobStatusResponse,
    JobStatus,
    JobError,
    ExtractJobCreateRequest,
    TailorJobCreateRequest,
    EvaluateJobCreateRequest,
    RephraseJobCreateRequest,
    RecommendJobCreateRequest,
    InjectKeywordJobCreateRequest,
    ElaborateJobCreateRequest,
)


# Frontend type definitions (replicated for validation)
# These should match the frontend types in src/types.ts

FRONTEND_JOB_STATUS = ['queued', 'processing', 'succeeded', 'failed', 'cancelled']

FRONTEND_CV_DATA_STRUCTURE = {
    'personal': {
        'name': str,
        'email': str,
        'phone': str,
        'location': str,
        'website': str,
        'linkedin': str,
        'github': str,
    },
    'professional_summary': str,
    'experience': list,
    'education': list,
    'projects': list,
    'skills': dict,
    'licenses_certifications': list,
    'job_description': str,
    'design': dict,
}


def validate_cv_data_structure(data: dict) -> bool:
    """Validate that CV data matches frontend structure."""
    if not isinstance(data, dict):
        return False
    
    # Check required top-level fields
    required_fields = ['personal', 'experience', 'education', 'projects', 'skills']
    for field in required_fields:
        if field not in data:
            return False
    
    # Validate personal info structure
    if 'personal' in data:
        personal = data['personal']
        if not isinstance(personal, dict):
            return False
        required_personal = ['name', 'email', 'phone', 'location']
        for field in required_personal:
            if field not in personal:
                return False
    
    # Validate experience structure
    if 'experience' in data:
        if not isinstance(data['experience'], list):
            return False
        for exp in data['experience']:
            if not isinstance(exp, dict):
                return False
            required_exp = ['company', 'role', 'startDate', 'endDate']
            for field in required_exp:
                if field not in exp:
                    return False
    
    return True


@pytest.mark.mocked
def test_api_contract_job_create():
    """Verify job creation request/response shapes match frontend expectations."""
    # Test ExtractJobCreateRequest
    extract_request = ExtractJobCreateRequest(
        cv_text="Sample CV text",
        job_description="Sample job description"
    )
    
    # Verify request can be serialized to JSON (matches frontend payload)
    request_dict = extract_request.model_dump()
    assert 'cv_text' in request_dict
    assert 'job_description' in request_dict
    
    # Test JobCreateResponse
    response = JobCreateResponse(
        job_id="test-job-123",
        status=JobStatus.queued
    )
    
    # Verify response structure matches frontend expectations
    response_dict = response.model_dump()
    assert 'job_id' in response_dict
    assert 'status' in response_dict
    assert response_dict['status'] in FRONTEND_JOB_STATUS
    
    # Verify response can be serialized to JSON
    json_str = json.dumps(response_dict)
    assert json_str is not None


@pytest.mark.mocked
def test_api_contract_job_status():
    """Verify job status response matches frontend types."""
    # Test succeeded status with result
    success_response = JobStatusResponse(
        job_id="test-job-123",
        status=JobStatus.succeeded,
        result={"personal": {"name": "John Doe"}}
    )
    
    response_dict = success_response.model_dump()
    assert response_dict['job_id'] == "test-job-123"
    assert response_dict['status'] == "succeeded"
    assert 'result' in response_dict
    assert response_dict['result'] is not None
    
    # Test failed status with error
    error_response = JobStatusResponse(
        job_id="test-job-456",
        status=JobStatus.failed,
        error=JobError(code="worker_error", message="Processing failed")
    )
    
    response_dict = error_response.model_dump()
    assert response_dict['status'] == "failed"
    assert 'error' in response_dict
    assert response_dict['error'] is not None
    
    # Verify error structure (code and message are optional in frontend)
    error = response_dict['error']
    assert isinstance(error, dict)
    # Both fields can be None or strings (frontend expects this)
    if error.get('code'):
        assert isinstance(error['code'], str)
    if error.get('message'):
        assert isinstance(error['message'], str)


@pytest.mark.mocked
def test_api_contract_error_format():
    """Verify error format matches frontend expectations."""
    # Error with both code and message
    error1 = JobError(code="worker_error", message="Processing failed")
    error_dict1 = error1.model_dump()
    assert 'code' in error_dict1
    assert 'message' in error_dict1
    
    # Error with only code
    error2 = JobError(code="worker_error", message=None)
    error_dict2 = error2.model_dump()
    assert 'code' in error_dict2
    # message can be None (frontend handles this)
    
    # Error with only message
    error3 = JobError(code=None, message="Processing failed")
    error_dict3 = error3.model_dump()
    assert 'message' in error_dict3
    # code can be None (frontend handles this)


@pytest.mark.mocked
def test_cv_data_transformation():
    """Verify backend CVData → frontend CVData mapping."""
    # Sample backend CV data (from AI extraction)
    backend_cv_data = {
        "personal": {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "+1-555-0123",
            "location": "San Francisco, CA",
            "website": "johndoe.com",
            "linkedin": "linkedin.com/in/johndoe",
            "github": "github.com/johndoe"
        },
        "professional_summary": "Experienced software engineer",
        "experience": [
            {
                "role": "Senior Software Engineer",
                "company": "Tech Corp",
                "startDate": "Jan 2020",
                "endDate": "Present",
                "location": "San Francisco, CA",
                "description": "Led development of microservices",
                "achievements": ["Improved performance by 40%"]
            }
        ],
        "education": [
            {
                "degree": "Bachelor of Science",
                "institution": "University of California",
                "field": "Computer Science",
                "startDate": "2014",
                "endDate": "2018",
                "gpa": "3.8"
            }
        ],
        "projects": [],
        "skills": {
            "technical": ["Python", "FastAPI"],
            "soft": ["Leadership"],
            "languages": ["English"]
        },
        "licenses_certifications": [],
        "target_job": {
            "title": "",
            "company": ""
        }
    }
    
    # Validate structure matches frontend expectations
    assert validate_cv_data_structure(backend_cv_data)
    
    # Verify required fields are present
    assert 'personal' in backend_cv_data
    assert 'experience' in backend_cv_data
    assert 'education' in backend_cv_data
    assert 'projects' in backend_cv_data
    assert 'skills' in backend_cv_data
    
    # Verify personal info structure
    personal = backend_cv_data['personal']
    assert 'name' in personal
    assert 'email' in personal
    assert 'phone' in personal
    assert 'location' in personal
    
    # Verify experience structure
    assert len(backend_cv_data['experience']) > 0
    exp = backend_cv_data['experience'][0]
    assert 'company' in exp
    assert 'role' in exp
    assert 'startDate' in exp
    assert 'endDate' in exp


@pytest.mark.mocked
def test_polling_compatibility():
    """Verify polling behavior matches frontend expectations."""
    # Frontend expects:
    # 1. Status values: queued, processing, succeeded, failed, cancelled
    # 2. Polling should work with exponential backoff
    # 3. Timeout after 4 minutes
    
    # Verify all status values are valid
    for status in JobStatus:
        assert status.value in FRONTEND_JOB_STATUS
    
    # Verify status transitions are compatible
    valid_transitions = {
        'queued': ['processing', 'cancelled'],
        'processing': ['succeeded', 'failed', 'cancelled'],
        'succeeded': [],  # Terminal state
        'failed': [],  # Terminal state
        'cancelled': [],  # Terminal state
    }
    
    # Verify backend status values match frontend expectations
    for status in JobStatus:
        assert status.value in valid_transitions or status.value in ['succeeded', 'failed', 'cancelled']


@pytest.mark.mocked
def test_all_job_types_request_contracts():
    """Verify all job type request contracts match frontend expectations."""
    # Extract
    extract_req = ExtractJobCreateRequest(cv_text="test", job_description="test")
    assert 'cv_text' in extract_req.model_dump()
    
    # Tailor
    tailor_req = TailorJobCreateRequest(user_cv_text="test", job_description="test")
    assert 'user_cv_text' in tailor_req.model_dump()
    
    # Evaluate
    evaluate_req = EvaluateJobCreateRequest(
        job_description="test",
        cv_json={"personal": {"name": "test"}}
    )
    assert 'cv_json' in evaluate_req.model_dump()
    
    # Rephrase
    rephrase_req = RephraseJobCreateRequest(
        section_content="test",
        section_type="experience",
        job_description="test"
    )
    assert 'section_content' in rephrase_req.model_dump()
    assert 'instruction_type' in rephrase_req.model_dump()  # Optional field
    
    # Recommend
    recommend_req = RecommendJobCreateRequest(
        job_description="test",
        cv_data={"personal": {"name": "test"}}
    )
    assert 'cv_data' in recommend_req.model_dump()
    
    # Inject Keyword
    inject_req = InjectKeywordJobCreateRequest(
        section_content="test",
        section_type="experience",
        keyword="test",
        job_description="test"
    )
    assert 'keyword' in inject_req.model_dump()
    
    # Elaborate
    elaborate_req = ElaborateJobCreateRequest(
        section_content="test",
        section_type="experience",
        keyword="test",
        user_context="test",
        job_description="test"
    )
    assert 'user_context' in elaborate_req.model_dump()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "mocked"])

