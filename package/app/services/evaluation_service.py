"""
Evaluation service for CV assessment.
"""
import asyncio
import numpy as np
from typing import Dict, Any, List
from ..core.config import settings
from ..utils.debug import print_step

# RAGAS evaluation framework removed for cloud deployment
# Using simplified evaluation approach
RAGAS_AVAILABLE = False

class EvaluationService:
    """Service for CV evaluation operations."""
    
    def __init__(self, ai_service):
        """
        Initialize the evaluation service.
        
        Args:
            ai_service: AI service instance
        """
        self.ai_service = ai_service
    
    async def evaluate_cv_with_ragas(self, job_description: str, cv_content: str, retrieved_docs: List) -> Dict[str, float]:
        """
        Evaluate CV using RAGAS metrics.
        
        Args:
            job_description: Job description
            cv_content: CV content as JSON string
            retrieved_docs: Retrieved documents from vectorstore
            
        Returns:
            RAGAS evaluation scores
        """
        print_step("RAGAS Evaluation Setup", {
            "ragas_available": RAGAS_AVAILABLE
        }, "input")
        
        if not RAGAS_AVAILABLE:
            print_step("RAGAS Evaluation", 
                      "RAGAS not available, using default scores", "info")
            return {
                "faithfulness": 0.0,
                "answer_relevancy": 0.0,
                "context_precision": 0.0,
                "context_recall": 0.0
            }
        
        try:
            print_step("RAGAS Dataset Creation", {
                "question_length": len(job_description),
                "contexts_count": len(retrieved_docs),
                "answer_length": len(cv_content)
            }, "input")
            
            # Validate that we have contexts to evaluate
            if not retrieved_docs:
                print_step("RAGAS Dataset Creation", 
                          "No retrieved documents - skipping RAGAS evaluation", "error")
                return {
                    "faithfulness": 0.0,
                    "answer_relevancy": 0.0,
                    "context_precision": 0.0,
                    "context_recall": 0.0
                }
            
            # Create a proper reference answer for context_precision metric
            reference_answer = f"Based on the job description: {job_description}, the CV should highlight relevant skills and experience."
            
            dataset = Dataset.from_dict({
                'question': [job_description],
                'contexts': [doc.page_content for doc in retrieved_docs],
                'answer': [cv_content],
                'ground_truths': [reference_answer]
            })
            print_step("RAGAS Dataset Creation", "Dataset created successfully", "output")
            
            print_step("RAGAS Evaluation Execution", {
                "metrics": ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
            }, "input")
            
            ragas_result = await asyncio.to_thread(
                evaluate, 
                dataset, 
                metrics=[faithfulness, answer_relevancy, context_precision, context_recall]
            )
            ragas_scores = ragas_result.to_pandas().to_dict('records')[0]
            print_step("RAGAS Evaluation Execution", "Evaluation completed", "output")
            
            # Handle NaN values in RAGAS scores
            print_step("RAGAS Score Processing", ragas_scores, "input")
            for key, value in ragas_scores.items():
                if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
                    ragas_scores[key] = 0.0
            print_step("RAGAS Score Processing", "NaN values handled", "output")
            
            return ragas_scores
            
        except Exception as e:
            print_step("RAGAS Evaluation", str(e), "error")
            return {
                "faithfulness": 0.0,
                "answer_relevancy": 0.0,
                "context_precision": 0.0,
                "context_recall": 0.0
            }
    
    async def evaluate_cv_with_committee(self, job_description: str, cv_content: str) -> Dict[str, Any]:
        """
        Evaluate CV using committee of personas.
        
        Args:
            job_description: Job description
            cv_content: CV content as JSON string
            
        Returns:
            Committee evaluation results
        """
        print_step("Committee Evaluation Setup", {
            "personas": settings.EVALUATION_PERSONAS,
            "cv_content_length": len(cv_content)
        }, "input")
        
        evaluation_tasks = [
            self.ai_service.evaluate_with_persona(p, job_description, cv_content)
            for p in settings.EVALUATION_PERSONAS
        ]
        
        print_step("Committee Evaluation Execution", {
            "task_count": len(evaluation_tasks)
        }, "input")
        
        committee_evaluations = await asyncio.gather(*evaluation_tasks)
        print_step("Committee Evaluation Execution", {
            "completed_evaluations": len(committee_evaluations)
        }, "output")
        
        # Handle potential NaN values in committee scores
        print_step("Committee Score Processing", committee_evaluations, "input")
        scores = []
        for e in committee_evaluations:
            score = e.get('score', 0)
            if isinstance(score, (int, float)) and not (np.isnan(score) or np.isinf(score)):
                scores.append(score)
            else:
                scores.append(0)
        
        committee_analysis = {
            "individual_evaluations": committee_evaluations,
            "average_score": round(np.mean(scores), 2) if scores else 0.0
        }
        print_step("Committee Score Processing", committee_analysis, "output")
        
        return committee_analysis
    
    async def evaluate_cv_complete(self, job_description: str, cv_content: str, retrieved_docs: List) -> Dict[str, Any]:
        """
        Perform complete CV evaluation with both RAGAS and committee evaluation.
        
        Args:
            job_description: Job description
            cv_content: CV content as JSON string
            retrieved_docs: Retrieved documents from vectorstore
            
        Returns:
            Complete evaluation results
        """
        # Run RAGAS and committee evaluation in parallel
        ragas_task = self.evaluate_cv_with_ragas(job_description, cv_content, retrieved_docs)
        committee_task = self.evaluate_cv_with_committee(job_description, cv_content)
        
        ragas_scores, committee_analysis = await asyncio.gather(ragas_task, committee_task)
        
        print_step("Final Analysis Assembly", {
            "ragas_scores": ragas_scores,
            "committee_analysis": committee_analysis
        }, "input")
        
        return {
            "ragas_scores": ragas_scores,
            "committee_evaluation": committee_analysis
        }
