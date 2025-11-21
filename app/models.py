from pydantic import BaseModel
from typing import List, Optional

class QueryRequest(BaseModel):
    query:str
    
class BuildKBRequest(BaseModel):
    pass

class TestCase(BaseModel):
    Test_ID:str
    Feature:str
    Test_Scenario:str
    Expected_Result:str
    Grounded_In:List[str]

class GenerateTestCasesRequest(BaseModel):
    query: str

class GenerateTestCasesResponse(BaseModel):
    test_cases: List[TestCase]

class GenerateScriptRequest(BaseModel):
    test_case: TestCase
    
class GenerateScriptResponse(BaseModel):
    script: str

class QAProcessResponse(BaseModel):
    test_cases: Optional[List[TestCase]] = None
    generated_script: Optional[str] = None
    message: Optional[str] = None