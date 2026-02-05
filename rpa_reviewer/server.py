from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
import os
from .analyzer import ProjectAnalyzer

app = FastAPI(title="RPA Reviewer API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    path: str
    active_rules: Optional[List[str]] = None
    include_framework: bool = True

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/analyze")
def analyze_project(request: AnalyzeRequest):
    project_path = request.path
    if not os.path.exists(project_path):
        raise HTTPException(status_code=404, detail="Project path not found")
    
    print(f"Analyzing: {project_path} with rules: {request.active_rules}")
    
    try:
        analyzer = ProjectAnalyzer(
            project_path, 
            active_rules=request.active_rules,
            include_framework=request.include_framework
        )
        area_results = analyzer.analyze()
        
        # Calculate Overall Stats
        pass_count = 0
        fail_count = 0
        
        for area in area_results:
            for cp in area['checkpoints']:
                if cp['status'] == 'PASS':
                    pass_count += 1
                elif cp['status'] == 'FAIL':
                    fail_count += 1
        
        total_valid = pass_count + fail_count
        percentage = "N/A"
        if total_valid > 0:
            percentage = round((pass_count / total_valid) * 100, 1)
            
        stats = {
            "pass_count": pass_count,
            "fail_count": fail_count,
            "overall_percentage": percentage
        }
        
        return {
            "success": True,
            "stats": stats,
            "areas": area_results
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
