#!/usr/bin/env python3
"""LLM Gateway — FastAPI service for cyber range intelligence layer."""
import json, time, re, hashlib, os
from functools import lru_cache
from openai import OpenAI
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Cyber Range LLM Gateway")
client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY", "sk-0963c2376243414989300815d3c1472b"),
    base_url="https://api.deepseek.com"
)

SIMPLE_CACHE = {}

def cache_key(state_desc, actions_tuple):
    h = hashlib.md5(f"{state_desc}|{actions_tuple}".encode()).hexdigest()
    return h

class PriorRequest(BaseModel):
    state_description: str
    available_actions: list[str]
    context: str = ""          # additional context (previous steps, findings)
    temperature: float = 0.3

class PriorResponse(BaseModel):
    probabilities: dict       # {"A": 0.45, "B": 0.23, "C": 0.12, ...}
    top_action: str
    top_probability: float
    model: str
    cached: bool

class AttackPlanRequest(BaseModel):
    state_description: str
    available_actions: list[str]
    objective: str = "Capture the flag"

class AttackPlanResponse(BaseModel):
    next_action: str
    rationale: str
    confidence: float

class EvaluateRequest(BaseModel):
    state_description: str
    action_taken: str
    result_description: str

class EvaluateResponse(BaseModel):
    assessment: str           # "good", "neutral", "bad"
    explanation: str


@app.post("/v1/prior", response_model=PriorResponse)
async def get_prior(req: PriorRequest):
    """Get LLM action probability distribution for a state."""
    ck = cache_key(req.state_description, tuple(req.available_actions))
    if ck in SIMPLE_CACHE:
        cached = SIMPLE_CACHE[ck]
        cached["cached"] = True
        return cached

    labels = [chr(65+i) for i in range(len(req.available_actions))]
    action_text = "\n".join(f"{l}. {a}" for l, a in zip(labels, req.available_actions))
    prompt = (
        f"You are a senior penetration tester.\n"
        f"Context: {req.context}\n\n"
        f"Current state:\n{req.state_description}\n\n"
        f"Available actions:\n{action_text}\n\n"
        f"Rate each action 1(worst)-10(best) for the next step.\n"
        f"Respond ONLY with JSON: {{\"" + '", "'.join(f'{l}": score' for l in labels) + "}}"
    )

    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=req.temperature,
            max_tokens=150
        )
        content = resp.choices[0].message.content.strip()
        m = re.search(r'\{[^}]+\}', content)
        if m:
            scores = json.loads(m.group())
            probs = {}
            for l in labels:
                probs[l] = max(scores.get(l, 5), 1)
            total = sum(probs.values())
            probs = {k: v/total for k, v in probs.items()}
        else:
            probs = {l: 1.0/len(labels) for l in labels}
    except Exception as e:
        print(f"LLM API error: {e}")
        probs = {l: 1.0/len(labels) for l in labels}

    top = max(probs, key=probs.get)
    result = {
        "probabilities": probs,
        "top_action": top,
        "top_probability": probs[top],
        "model": "deepseek-chat",
        "cached": False
    }
    SIMPLE_CACHE[ck] = result.copy()
    SIMPLE_CACHE[ck]["cached"] = False
    return result


@app.post("/v1/attack_plan", response_model=AttackPlanResponse)
async def get_attack_plan(req: AttackPlanRequest):
    """Get LLM's recommended next action with rationale."""
    action_text = "\n".join(f"{chr(65+i)}. {a}" for i, a in enumerate(req.available_actions))
    prompt = (
        f"Penetration tester. Objective: {req.objective}.\n\n"
        f"Current state:\n{req.state_description}\n\n"
        f"Actions:\n{action_text}\n\n"
        f"Pick ONE best action. Respond JSON: "
        f'{{"action": "A", "rationale": "why this action", "confidence": 0.8}}'
    )
    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=200
        )
        content = resp.choices[0].message.content.strip()
        m = re.search(r'\{[^}]+\}', content)
        if m:
            data = json.loads(m.group())
            return AttackPlanResponse(
                next_action=data.get("action", "A"),
                rationale=data.get("rationale", "No rationale provided"),
                confidence=data.get("confidence", 0.5)
            )
    except Exception as e:
        return AttackPlanResponse(
            next_action="A", rationale=f"Fallback (error: {e})", confidence=0.3
        )


@app.post("/v1/evaluate", response_model=EvaluateResponse)
async def evaluate_action(req: EvaluateRequest):
    """Evaluate whether an action was effective."""
    prompt = (
        f"Penetration test result analysis.\n\n"
        f"State: {req.state_description}\n"
        f"Action taken: {req.action_taken}\n"
        f"Result: {req.result_description}\n\n"
        f"Rate: good (progress made), neutral (info gathered), or bad (wasted/detected). "
        f'Respond JSON: {{"rating": "good", "explanation": "..."}}'
    )
    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=150
        )
        content = resp.choices[0].message.content.strip()
        m = re.search(r'\{[^}]+\}', content)
        if m:
            data = json.loads(m.group())
            return EvaluateResponse(
                assessment=data.get("rating", "neutral"),
                explanation=data.get("explanation", "")
            )
    except:
        pass
    return EvaluateResponse(assessment="neutral", explanation="Could not evaluate")


@app.get("/health")
async def health():
    return {"status": "ok", "cache_size": len(SIMPLE_CACHE)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
