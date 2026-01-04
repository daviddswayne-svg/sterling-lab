import os
import uuid
import asyncio
import threading
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Optional
import processor

app = FastAPI(title="VoxSure API")

# Enable CORS for frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Jobs store (in-memory for now, simple for portfolio)
jobs: Dict[str, dict] = {}
# Single worker lock to protect RAM
processing_lock = asyncio.Lock()

UPLOAD_DIR = "uploads"
PROCESSED_DIR = "processed"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

@app.post("/upload")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    file_ext = os.path.splitext(file.filename)[1].lower()
    file_path = os.path.join(UPLOAD_DIR, f"{job_id}{file_ext}")
    
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    jobs[job_id] = {"status": "queued", "filename": file.filename}
    background_tasks.add_task(process_job, job_id, file_path, file_ext)
    
    return {"job_id": job_id}

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]

async def process_job(job_id: str, file_path: str, ext: str):
    # The 'One-at-a-time' gate
    async with processing_lock:
        jobs[job_id]["status"] = "processing"
        try:
            # Offload heavy CPU work to a thread to not block the event loop
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, processor.voxelize, file_path, ext)
            
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["result"] = result
        except Exception as e:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = str(e)
            print(f"Error processing {job_id}: {e}")

@app.get("/voxels/{job_id}")
async def get_voxels(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]["result"]

@app.get("/compare/{job_a}/{job_b}")
async def run_comparison(job_a: str, job_b: str):
    if job_a not in jobs or job_b not in jobs:
        raise HTTPException(status_code=404, detail="One or both jobs not found")
    
    if jobs[job_a]["status"] != "completed" or jobs[job_b]["status"] != "completed":
        raise HTTPException(status_code=400, detail="Jobs must both be completed")

    comp_id = f"comp_{job_a}_{job_b}"
    
    try:
        # result is inside jobs[job_id]["result"]
        res_a = jobs[job_a]["result"]
        res_b = jobs[job_b]["result"]
        
        comparison = processor.compare_voxels(res_a["voxels"], res_b["voxels"])
        
        jobs[comp_id] = {
            "status": "completed",
            "result": comparison
        }
        
        return {"comparison_id": comp_id, "metrics": comparison["metrics"]}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=12346)
