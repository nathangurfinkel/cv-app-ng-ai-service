"""
CV evaluation API routes.
"""
from fastapi import APIRouter, HTTPException, Depends
from ..models.request_models import EvaluationRequest
from ..services.evaluation_service import EvaluationService
from ..services.ai_service import AIService
from ..utils.debug import print_step
from ..utils.tier_validation import require_ai_operations, UserTier

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])

# Services are now instantiated per-request with BYOK support

@router.post("/cv")
async def evaluate_cv(
    request: EvaluationRequest,
    tier: UserTier = Depends(require_ai_operations)
):
    """
    Perform a committee evaluation on a provided CV JSON against a job description.
    """
    print_step("Committee Evaluation Request", {
        "job_description_length": len(request.job_description),
        "cv_keys": list(request.cv_json.keys())
    }, "input")

    try:
        # Convert the CV JSON object back to a string for the LLM prompt
        import json
        cv_content_str = json.dumps(request.cv_json, indent=2)

        # Perform committee evaluation (uses system OPENAI_API_KEY - sync route)
        ai_service = AIService(provider="openai", api_key=None)
        evaluation_service = EvaluationService(ai_service)
        committee_analysis = await evaluation_service.evaluate_cv_with_committee(
            request.job_description,
            cv_content_str
        )
        
        return committee_analysis

    except Exception as e:
        print_step("Committee Evaluation Error", str(e), "error")
        raise HTTPException(status_code=500, detail=f"Error during evaluation: {e}")
