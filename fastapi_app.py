# fastapi_app.py
import os
import time
import json
import logging
import subprocess
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import Response
from pydantic import BaseModel
import yaml
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.cors import CORSMiddleware
from jsonschema import validate, ValidationError

# import orchestrator build function defensively so module import doesn't crash the whole app
try:
    from orchestrator import build_graph
except Exception as e:
    # log the import failure and allow the rest of the app to start.
    logging.exception("Could not import orchestrator.build_graph at module import: %s", e)
    build_graph = None

# load config
CFG_PATH = os.environ.get("MG_CONFIG", "./configs/prompts.yaml")
with open(CFG_PATH, "r") as f:
    CONFIG = yaml.safe_load(f)

# logging + metrics
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fastapi_app")
REQ_COUNTER = Counter("api_requests_total", "Total API requests", ["endpoint", "method"])
REQ_LATENCY = Histogram("api_request_latency_seconds", "Request latency seconds", ["endpoint"])

# JSON schema
from utils.json_schema import FINAL_STRATEGY_SCHEMA

# simple banned phrases
BANNED = ["do illegal", "hack", "kill", "terror"]

app = FastAPI(title="NextGen Marketer API", version="0.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# build workflow
try:
    workflow_app = build_graph()
except Exception as e:
    logger.exception("Failed to build workflow: %s", e)
    workflow_app = None

def record(endpoint: str, t0: float):
    REQ_COUNTER.labels(endpoint=endpoint, method="POST").inc()
    REQ_LATENCY.labels(endpoint=endpoint).observe(time.time() - t0)

def enforce_safety(text: str):
    low = text.lower()
    for b in BANNED:
        if b in low:
            return False, f"banned phrase {b}"
    if len(text) > CONFIG.get("safety", {}).get("max_input_chars", 20000):
        return False, "input too long"
    return True, None

def run_ingest_subproc(campaign, purchase, sentiment, pdf, persist_dir, batch_size=128):
    cmd = ["python", "ingest.py", "--campaign", campaign, "--purchase", purchase, "--sentiment", sentiment, "--pdf", pdf, "--persist-dir", persist_dir, "--batch-size", str(batch_size)]
    subprocess.Popen(cmd)

class StrategyRequest(BaseModel):
    query: str
    thread_id: Optional[str] = None

@app.get("/health")
async def health():
    return {"status": "ok", "workflow_loaded": workflow_app is not None}

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/ingest")
async def ingest(background: BackgroundTasks, campaign: UploadFile = File(...), purchase: UploadFile = File(...), sentiment: UploadFile = File(...), pdf: UploadFile = File(None), persist_dir: str = "./chroma_db"):
    start = time.time()
    os.makedirs("data", exist_ok=True)
    cpath = os.path.join("data", campaign.filename)
    ppath = os.path.join("data", purchase.filename)
    spath = os.path.join("data", sentiment.filename)
    with open(cpath, "wb") as f:
        f.write(await campaign.read())
    with open(ppath, "wb") as f:
        f.write(await purchase.read())
    with open(spath, "wb") as f:
        f.write(await sentiment.read())
    pdf_path = ""
    if pdf:
        pdf_path = os.path.join("data", pdf.filename)
        with open(pdf_path, "wb") as f:
            f.write(await pdf.read())
    background.add_task(run_ingest_subproc, cpath, ppath, spath, pdf_path, persist_dir)
    record("/ingest", start)
    return {"status": "started"}

@app.post("/strategy")
async def strategy(req: StrategyRequest):
    start = time.time()
    ok, reason = enforce_safety(req.query)
    if not ok:
        raise HTTPException(status_code=400, detail=reason)
    if workflow_app is None:
        raise HTTPException(status_code=500, detail="workflow not available")

    final_state = None
    thread_id = None

    # Try to use langgraph_integration manager if available (preferred)
    try:
        from langgraph_integration import manager as graph_manager
        try:
            final_state = graph_manager.invoke(req.thread_id, req.query)
            thread_id = final_state.get("_thread_id") if isinstance(final_state, dict) else req.thread_id
        except Exception as e:
            logger.exception("langgraph_integration.manager.invoke failed, falling back to compiled workflow_app: %s", e)
            final_state = None
    except Exception:
        # langgraph_integration not present — fall back immediately
        final_state = None

    # Fallback to existing compiled workflow invocation if langgraph path didn't produce a result
    if final_state is None:
        try:
            # Pass thread_id inside payload so orchestrator nodes can access it if they want
            payload = {"user_prompt": req.query, "thread_id": req.thread_id}

            # --- Minimal change: supply LangGraph checkpointer `config` with thread_id ---
            config = {"configurable": {"thread_id": req.thread_id}}
            try:
                final_state = workflow_app.invoke(payload, config=config)
            except TypeError:
                # compiled graph might not accept config param; try legacy signature
                final_state = workflow_app.invoke(payload)

            # If the graph returns a thread id inside state, capture it; else prefer request thread_id
            if isinstance(final_state, dict) and "_thread_id" in final_state:
                thread_id = final_state.get("_thread_id")
            else:
                thread_id = req.thread_id
        except Exception as e:
            logger.exception("Workflow invoke failed")
            raise HTTPException(status_code=500, detail=str(e))

    # Ensure final_state is a dict
    if not isinstance(final_state, dict):
        final_state = {"result": final_state}

    final_strategy = final_state.get("final_decision")
    # validation / deterministic enforcement
    valid = True
    schema_err = None
    try:
        validate(instance=final_strategy, schema=FINAL_STRATEGY_SCHEMA)
    except ValidationError as e:
        valid = False
        schema_err = str(e)
        # attempt to salvage: if strategy is string, try extract json
        if isinstance(final_strategy, str):
            s = final_strategy
            start = s.find("{"); end = s.rfind("}")
            if start != -1 and end != -1:
                try:
                    final_strategy = json.loads(s[start:end+1])
                    validate(instance=final_strategy, schema=FINAL_STRATEGY_SCHEMA)
                    valid = True
                    schema_err = None
                except Exception:
                    pass
    record("/strategy", start)
    response = {"final_strategy": final_strategy, "valid_schema": valid, "schema_error": schema_err}
    # include raw per-agent outputs for UI trace
    response["raw_state"] = final_state
    # include thread id so UI can persist it for conversational memory
    response["thread_id"] = thread_id
    return response

@app.get("/")
async def root():
    return {"app":"nextgen-marketer"}
