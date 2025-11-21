import logging
import os
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.rag import load_and_ingest_documents, generate_test_cases, generate_selenium_script, is_knowledge_base_built
from app.models import GenerateTestCasesRequest, GenerateTestCasesResponse, GenerateScriptRequest, GenerateScriptResponse, TestCase
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__) 

app = FastAPI(
    title="Autonomous QA Agent API",
    description="API for ingesting documents, generating test cases, and generating Selenium scripts.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Autonomous QA Agent API!"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/build_knowledge_base", status_code=200)
async def build_knowledge_base(
    documents: List[UploadFile] = File(..., description="Support documents (e.g., .md, .txt, .json)"),
    html_file: UploadFile = File(..., description="The target checkout.html file")
):
    logger.info("Received request to build knowledge base.")
    try:
        valid_doc_types = {".md", ".txt", ".json"}
        valid_html_types = {".html", ".htm"}

        for doc in documents:
            if doc.filename and Path(doc.filename).suffix.lower() not in valid_doc_types:
                raise HTTPException(status_code=400, detail=f"Unsupported document type: {doc.filename}")

        if html_file.filename and Path(html_file.filename).suffix.lower() not in valid_html_types:
            raise HTTPException(status_code=400, detail=f"Unsupported HTML type: {html_file.filename}")

        await load_and_ingest_documents(documents, html_file)
        logger.info("Knowledge base built successfully.")
        return JSONResponse(content={"message": "Knowledge Base Built Successfully!"}, status_code=200)

    except HTTPException as he:
        logger.error(f"HTTPException caught in main.py during KB building: {he.detail} (status_code: {he.status_code})")
        import traceback
        logger.error(traceback.format_exc())
        raise 
    except Exception as e:
        logger.error(f"Unexpected error during KB building in main.py: {e}")
        import traceback
        logger.error(traceback.format_exc()) 
        raise HTTPException(status_code=500, detail="Internal server error during knowledge base building.")

@app.post("/generate_test_cases", response_model=GenerateTestCasesResponse)
async def api_generate_test_cases(request: GenerateTestCasesRequest):
    logger.info(f"Received request to generate test cases for query: {request.query}")
    if not is_knowledge_base_built():
        logger.error("Knowledge base not built.")
        raise HTTPException(status_code=400, detail="Knowledge base is not built yet. Please upload documents and build it first.")
    try:
        test_cases = await generate_test_cases(request.query)
        logger.info(f"Successfully generated {len(test_cases)} test cases.")
        return GenerateTestCasesResponse(test_cases=test_cases)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during test case generation: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error during test case generation.")

@app.post("/generate_selenium_script", response_model=GenerateScriptResponse)
async def api_generate_selenium_script(request: GenerateScriptRequest):
    logger.info(f"Received request to generate Selenium script for test case ID: {request.test_case.Test_ID}")
    if not is_knowledge_base_built():
        logger.error("Knowledge base not built.")
        raise HTTPException(status_code=400, detail="Knowledge base is not built yet. Please upload documents and build it first.")

    try:
        script_content = await generate_selenium_script(request)
        logger.info("Successfully generated Selenium script.")
        return GenerateScriptResponse(script=script_content)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during script generation: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error during script generation.")
