# AI API Token Cost Audit

## Executive Summary

This audit identifies redundant LLM API calls and opportunities to optimize token usage. Focus is on **what's being done** and **how many times**, not evaluation quality.

**Key Findings:**
- ⚠️ **Tailor job is NOT wired to UI** - API exists but no frontend calls it (potential dead code)
- **Evaluate job** makes 3 LLM calls (3 committee personas) - **ACTIVELY USED**
- **Extract job** makes 1 LLM call - **ACTIVELY USED**
- **Job descriptions** are sent multiple times in the same operation
- **CV text** is re-extracted even when structured data already exists

---

## Current LLM Call Patterns

### 1. Extract Job (`/ai/jobs/extract`)

**LLM Calls:** 1
- `extract_structured_cv_data(cv_text, job_description?)` → 1 call

**Token Usage:**
- System prompt: ~200 tokens
- User prompt: ~500-2000 tokens (CV text + job description if provided)
- Response: ~500-1500 tokens (structured JSON)
- **Total per call: ~1200-3700 tokens**

**Status:** ✅ Efficient (single call)

---

### 2. Tailor Job (`/ai/jobs/tailor`) ⚠️ **EXPENSIVE BUT NOT USED**

**Status:** ⚠️ **NOT WIRED TO UI** - API method exists but no frontend component calls it

**LLM Calls:** 5 total (if used)
1. `extract_structured_cv_data(user_cv_text, job_description)` → **1 call**
2. `evaluate_cv_complete(job_description, cv_json, [])` → **4 calls**:
   - `evaluate_cv_with_ragas()` → 1 call (if RAGAS available)
   - `evaluate_cv_with_committee()` → 3 calls (one per persona)

**Code Location:**
```python:138:150:cv-app-ng-ai-service/app/worker.py
elif job_type == JobType.tailor.value:
    user_cv_text = validate_cv_text(payload.get("user_cv_text", ""))
    jd = validate_job_description(payload.get("job_description", ""))

    raw_ai_data = _run_async(ai.extract_structured_cv_data(user_cv_text, jd))
    cv_data = transformer.transform_ai_data_to_cv_data(raw_ai_data)
    structured_content = transformer.cv_data_to_dict(cv_data)

    # Attach analysis (can be slow) but worker timeout handles it.
    analysis = _run_async(evaluation.evaluate_cv_complete(jd, json.dumps(structured_content), []))
    structured_content["analysis"] = analysis
```

**Token Usage:**
- Extract call: ~1200-3700 tokens
- RAGAS call: ~800-2000 tokens (job description + CV JSON)
- Committee call #1: ~800-2000 tokens
- Committee call #2: ~800-2000 tokens
- Committee call #3: ~800-2000 tokens
- **Total: ~5200-11700 tokens per tailor operation**

**Issues:**
1. ⚠️ **NOT USED IN UI** - This endpoint may be dead code. Consider removing or documenting why it exists.
2. ❌ **Redundant extraction**: If CV was already extracted, we're re-extracting it
3. ❌ **Job description sent 5 times**: Same JD sent to extract + RAGAS + 3 personas
4. ❌ **CV content sent 4 times**: Once to extract, then 3 times to committee (as JSON string)

---

### 3. Evaluate Job (`/ai/jobs/evaluate`)

**LLM Calls:** 3 total
- `evaluate_cv_with_committee()` → 3 calls (one per persona)

**Code Location:**
```python:151:156:cv-app-ng-ai-service/app/worker.py
elif job_type == JobType.evaluate.value:
    jd = validate_job_description(payload.get("job_description", ""))
    cv_json = payload.get("cv_json") or {}
    cv_content_str = json.dumps(cv_json, indent=2)
    committee_analysis = _run_async(evaluation.evaluate_cv_with_committee(jd, cv_content_str))
```

**Token Usage:**
- Committee call #1: ~800-2000 tokens
- Committee call #2: ~800-2000 tokens
- Committee call #3: ~800-2000 tokens
- **Total: ~2400-6000 tokens per evaluate operation**

**Issues:**
1. ❌ **Job description sent 3 times**: Same JD sent to all 3 personas
2. ❌ **CV JSON sent 3 times**: Same CV content serialized and sent 3 times

---

### 4. Rephrase Job (`/ai/jobs/rephrase`)

**LLM Calls:** 1
- `rephrase_cv_section(section_content, section_type, job_description)` → 1 call

**Token Usage:**
- System prompt: ~100 tokens
- User prompt: ~300-800 tokens (section + job description)
- Response: ~200-500 tokens
- **Total: ~600-1400 tokens**

**Status:** ✅ Efficient (single call)

---

### 5. Inject Keyword Job (`/ai/jobs/inject-keyword`)

**LLM Calls:** 1
- `inject_keyword(section_content, section_type, keyword, job_description)` → 1 call

**Token Usage:**
- System prompt: ~150 tokens
- User prompt: ~300-800 tokens
- Response: ~200-500 tokens
- **Total: ~650-1450 tokens**

**Status:** ✅ Efficient (single call)

---

### 6. Elaborate Job (`/ai/jobs/elaborate`)

**LLM Calls:** 1
- `elaborate_with_keyword(section_content, section_type, keyword, user_context, job_description)` → 1 call

**Token Usage:**
- System prompt: ~100 tokens
- User prompt: ~400-1000 tokens
- Response: ~200-500 tokens
- **Total: ~700-1600 tokens**

**Status:** ✅ Efficient (single call)

---

### 7. Recommend Job (`/ai/jobs/recommend`)

**LLM Calls:** 1
- `recommend_template(job_description, cv_data)` → 1 call

**Token Usage:**
- System prompt: ~200 tokens
- User prompt: ~500-1500 tokens (job description + CV analysis summary)
- Response: ~300-800 tokens
- **Total: ~1000-2500 tokens**

**Status:** ✅ Efficient (single call)

---

### 8. Roast (`/ai/roast`) - Synchronous

**LLM Calls:** 1
- Direct `llm.chat_completion()` call

**Token Usage:**
- System prompt: ~100 tokens
- User prompt: ~200-500 tokens (first 2000 chars of CV)
- Response: ~200-300 tokens
- **Total: ~500-900 tokens**

**Status:** ✅ Efficient (single call)

---

### 9. Interview (`/ai/interview/*`)

**LLM Calls:** Variable (streaming)
- `/start`: 1 call
- `/answer`: 1 call per answer (streaming)

**Token Usage:**
- Start: ~300-500 tokens
- Per answer: ~200-400 tokens
- **Total per interview: ~500-900 tokens + (N answers × 200-400 tokens)**

**Status:** ✅ Efficient (streaming reduces latency, not cost)

---

## Redundancy Analysis

### Critical Issues

#### 1. Tailor Job Re-extracts CV Data

**Problem:**
- Tailor job calls `extract_structured_cv_data()` even though the frontend may have already extracted the CV
- If user uploads CV → extracts → then tailors, we're extracting twice

**Current Flow:**
```
User uploads CV
  → extractCVData() → 1 LLM call
User clicks "Tailor"
  → tailorCV() → extract_structured_cv_data() → 1 LLM call (REDUNDANT)
  → evaluate_cv_complete() → 4 LLM calls
Total: 6 LLM calls for one user action
```

**Optimization Opportunity:**
- Accept `cv_json` in tailor job (like evaluate does)
- Skip extraction if structured data already exists
- **Savings: 1 LLM call (~1200-3700 tokens)**

---

#### 2. Job Description Sent Multiple Times

**Problem:**
- In tailor job: JD sent 5 times (extract + RAGAS + 3 personas)
- In evaluate job: JD sent 3 times (3 personas)

**Current:**
- Each LLM call includes full job description in prompt
- Job descriptions can be 500-2000 tokens

**Optimization Opportunity:**
- Cache job description embeddings or summaries
- Use shorter context in follow-up calls
- **Savings: ~2000-8000 tokens per tailor, ~1000-4000 tokens per evaluate**

---

#### 3. CV Content Serialized Multiple Times

**Problem:**
- In tailor: CV extracted → serialized to JSON → sent to 3 personas
- In evaluate: CV JSON serialized → sent to 3 personas

**Current:**
- `json.dumps(cv_json, indent=2)` creates large strings
- Same content sent 3 times with different persona prompts

**Optimization Opportunity:**
- Batch committee evaluation in single call with structured output
- Or use function calling to get all 3 evaluations in one response
- **Savings: ~1000-3000 tokens per operation**

---

#### 4. Committee Evaluation Makes 3 Separate Calls

**Problem:**
- `evaluate_cv_with_committee()` makes 3 sequential LLM calls
- Each call sends full CV + JD + persona prompt

**Code:**
```python:159:205:cv-app-ng-ai-service/app/services/evaluation_service.py
async def evaluate_cv_with_committee(self, job_description: str, cv_content: str) -> Dict[str, Any]:
    evaluation_tasks = [
        self.ai_service.evaluate_with_persona(p, job_description, cv_content)
        for p in settings.EVALUATION_PERSONAS
    ]
    committee_evaluations = await asyncio.gather(*evaluation_tasks)
```

**Optimization Opportunity:**
- Single LLM call with structured output for all 3 personas
- Use JSON mode or function calling to get all evaluations at once
- **Savings: 2 LLM calls (~1600-4000 tokens)**

---

## Optimization Recommendations

### Priority 0: Clean Up Dead Code

#### 0.1 Remove or Document Tailor Endpoint

**Issue:**
- `/ai/jobs/tailor` endpoint exists but is NOT called from frontend
- `ApiService.tailorCV()` exists but no UI component uses it
- Documentation claims it's "fully integrated" but it's not

**Action:**
- Option A: Remove the endpoint if not needed
- Option B: Wire it to UI if it's intended to be used
- Option C: Document why it exists if it's for future use

**Impact:**
- If removed: Saves maintenance burden
- If wired: Would add 5 LLM calls per use (expensive!)

---

### Priority 1: High Impact, Low Effort

#### 1.1 Skip Extraction in Tailor if CV JSON Provided (IF TAILOR IS USED)

**Change:**
- Modify tailor job to accept optional `cv_json` parameter
- If provided, skip `extract_structured_cv_data()` call
- Use provided structured data directly

**Impact:**
- Saves 1 LLM call per tailor operation
- **Token savings: ~1200-3700 tokens per tailor**
- **Cost savings: ~$0.01-0.03 per tailor (GPT-4 pricing)**

**Implementation:**
```python
# In worker.py
elif job_type == JobType.tailor.value:
    user_cv_text = payload.get("user_cv_text", "")
    cv_json = payload.get("cv_json")  # NEW: optional structured data
    
    if cv_json:
        # Use provided structured data
        cv_data = transformer.transform_ai_data_to_cv_data(cv_json)
    else:
        # Extract from text (fallback)
        raw_ai_data = _run_async(ai.extract_structured_cv_data(user_cv_text, jd))
        cv_data = transformer.transform_ai_data_to_cv_data(raw_ai_data)
    
    structured_content = transformer.cv_data_to_dict(cv_data)
    # ... rest of evaluation
```

---

#### 1.2 Batch Committee Evaluation in Single Call

**Change:**
- Create new method `evaluate_with_all_personas()` that returns all 3 evaluations in one call
- Use structured output (JSON mode) to get all personas' responses

**Impact:**
- Reduces 3 calls to 1 call
- **Token savings: ~1600-4000 tokens per evaluate/tailor**
- **Cost savings: ~$0.01-0.03 per operation**

**Implementation:**
```python
# In ai_service.py
async def evaluate_with_all_personas(self, job_description: str, cv_content: str) -> Dict[str, Any]:
    system_prompt = "You are an expert CV evaluator. Provide evaluations from 3 personas."
    user_prompt = f"""
    Evaluate this CV from 3 perspectives:
    1. Technical Recruiter
    2. HR Manager  
    3. Hiring Manager
    
    Job Description: {job_description}
    CV Content: {cv_content}
    
    Return JSON:
    {{
        "technical_recruiter": {{"score": ..., "strengths": ..., ...}},
        "hr_manager": {{"score": ..., ...}},
        "hiring_manager": {{"score": ..., ...}}
    }}
    """
    # Use JSON mode for structured output
    response = await llm.chat_completion(..., response_format={"type": "json_object"})
```

---

### Priority 2: Medium Impact, Medium Effort

#### 2.1 Summarize Job Description for Follow-up Calls

**Change:**
- First call: Send full job description
- Subsequent calls: Send summary or key requirements only

**Impact:**
- Reduces token count in committee evaluation calls
- **Token savings: ~1000-4000 tokens per operation**

---

#### 2.2 Cache Job Description Embeddings

**Change:**
- Generate job description summary/embedding once
- Reuse in all follow-up calls

**Impact:**
- Reduces repeated JD tokens
- **Token savings: ~2000-8000 tokens per tailor operation**

---

### Priority 3: Lower Priority

#### 3.1 Make RAGAS Evaluation Optional in Tailor

**Change:**
- Make RAGAS evaluation optional (flag in request)
- Skip if not needed

**Impact:**
- Saves 1 LLM call when RAGAS not needed
- **Token savings: ~800-2000 tokens**

---

## Cost Estimates (GPT-4 Pricing)

**Assumptions:**
- Input: $0.03 per 1K tokens
- Output: $0.06 per 1K tokens
- Average: 70% input, 30% output

### Current Costs Per Operation

| Operation | LLM Calls | Est. Tokens | Est. Cost | Status |
|-----------|-----------|-------------|-----------|--------|
| Extract | 1 | 1,200-3,700 | $0.04-0.12 | ✅ **USED** |
| **Tailor** | **5** | **5,200-11,700** | **$0.17-0.38** | ⚠️ **NOT USED** |
| **Evaluate** | **3** | **2,400-6,000** | **$0.08-0.20** | ✅ **USED** |
| Rephrase | 1 | 600-1,400 | $0.02-0.05 | ✅ **USED** |
| Inject Keyword | 1 | 650-1,450 | $0.02-0.05 | ✅ **USED** |
| Elaborate | 1 | 700-1,600 | $0.02-0.05 | ✅ **USED** |
| Recommend | 1 | 1,000-2,500 | $0.03-0.08 | ✅ **USED** |
| Roast | 1 | 500-900 | $0.02-0.03 | ✅ **USED** |

### Potential Savings (After Optimizations)

| Optimization | Savings Per Operation | Annual Savings* |
|-------------|----------------------|-----------------|
| Skip extraction in tailor | 1 call, ~2,500 tokens | $0.02-0.08 |
| Batch committee evaluation | 2 calls, ~2,800 tokens | $0.09-0.28 |
| JD summarization | ~2,000 tokens | $0.06-0.20 |
| **Total per tailor** | **~7,300 tokens** | **$0.24-0.76** |

*Assuming 100 tailor operations per month

---

## Implementation Priority

1. **Immediate (Week 1):**
   - Skip extraction in tailor if `cv_json` provided
   - Batch committee evaluation in single call

2. **Short-term (Week 2-3):**
   - Job description summarization
   - Make RAGAS optional in tailor

3. **Long-term (Month 2+):**
   - Caching layer for job descriptions
   - Embedding-based context reduction

---

## Metrics to Track

After implementing optimizations, track:
- Average tokens per operation (by type)
- LLM calls per operation (by type)
- Cost per operation (by type)
- User experience (latency, quality)

---

## Notes

- This audit focuses on **token costs**, not quality
- Some redundancies may be intentional for quality (e.g., multiple personas)
- Balance cost optimization with user experience
- Consider A/B testing to validate quality doesn't degrade

