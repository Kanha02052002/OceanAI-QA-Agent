import os
import logging
from typing import List, Optional
from pathlib import Path
import json
import tempfile
import asyncio
import re
from functools import lru_cache

from dotenv import load_dotenv
from openai import AsyncOpenAI
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document as LangChainDocument
from fastapi import UploadFile, HTTPException
import fitz
from bs4 import BeautifulSoup

from .models import TestCase, GenerateScriptRequest

load_dotenv()

logger = logging.getLogger(__name__)

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
FAISS_PERSIST_DIR = os.getenv("FAISS_PERSIST_DIR", "./faiss_index")
FAISS_INDEX_FILE = os.path.join(FAISS_PERSIST_DIR, "faiss_index.pkl")
FAISS_DOCSTORE_FILE = os.path.join(FAISS_PERSIST_DIR, "faiss_docstore.pkl")
FAISS_INDEX2ID_FILE = os.path.join(FAISS_PERSIST_DIR, "faiss_index_to_id.pkl")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL_NAME = os.getenv("OPENROUTER_MODEL_NAME", "openai/gpt-4o")

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

vector_store: Optional[FAISS] = None
embedding_function: Optional[HuggingFaceEmbeddings] = None

@lru_cache(maxsize=1)
def _get_embedding_model_cached(model_name: str):
    logger.info(f"Loading embedding model: {model_name}")
    try:
        model_path = os.path.join("models_cache", model_name.replace("/", "_"))
        os.makedirs("models_cache", exist_ok=True)

        from sentence_transformers import SentenceTransformer
        if os.path.exists(model_path):
             logger.info(f"Loading embedding model from cache: {model_path}")
             hf_model = SentenceTransformer(model_path)
        else:
             logger.info(f"Loading embedding model from HuggingFace Hub: {model_name}")
             hf_model = SentenceTransformer(model_name)
             logger.info(f"Saving embedding model to cache: {model_path}")
             hf_model.save(model_path)

        from langchain_community.embeddings import HuggingFaceEmbeddings
        langchain_model = HuggingFaceEmbeddings(model_name=model_path)
        logger.info(f"Embedding model {model_name} loaded and cached successfully.")
        return langchain_model
    except Exception as e:
        logger.error(f"Error loading embedding model {model_name}: {e}")
        raise

async def initialize_embedding_model():
    global embedding_function
    loop = asyncio.get_event_loop()
    embedding_function = await loop.run_in_executor(None, _get_embedding_model_cached, EMBEDDING_MODEL_NAME)

def _parse_document(file_path: Path) -> str:
    content = ""
    try:
        if file_path.suffix.lower() in ['.md', '.txt']:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        elif file_path.suffix.lower() == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                content = json.dumps(json_data, indent=2)
        elif file_path.suffix.lower() == '.pdf':
            doc = fitz.open(file_path)
            content = ""
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                content += page.get_text()
            doc.close()
        elif file_path.suffix.lower() == '.html':
            with open(file_path, 'r', encoding='utf-8') as f:
                 soup = BeautifulSoup(f.read(), 'html.parser')
                 content = soup.get_text(separator=' ', strip=True)
        else:
            logger.warning(f"Unsupported file type for parsing: {file_path.suffix}")
    except Exception as e:
        logger.error(f"Error parsing file {file_path}: {e}")
    return content

async def load_and_ingest_documents(files: List[UploadFile], html_file: UploadFile):
    global vector_store, embedding_function

    if embedding_function is None:
        await initialize_embedding_model()

    documents = []

    for file in files:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_path = Path(temp_file.name)

            loop = asyncio.get_event_loop()
            content_str = await loop.run_in_executor(None, _parse_document, temp_path)
            if content_str:
                doc = LangChainDocument(page_content=content_str, metadata={"source": file.filename})
                documents.append(doc)
                logger.info(f"Parsed support document: {file.filename}")

            os.unlink(temp_path)
        except Exception as e:
            logger.error(f"Error processing support document {file.filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Error processing file: {file.filename}")

    if html_file:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as temp_html_file:
                content = await html_file.read()
                temp_html_file.write(content)
                temp_html_path = Path(temp_html_file.name)

            with open(temp_html_path, 'r', encoding='utf-8') as f:
                 full_html_content = f.read()

            soup = BeautifulSoup(full_html_content, 'html.parser')
            text_content = soup.get_text(separator=' ', strip=True)

            html_doc_full = LangChainDocument(page_content=full_html_content, metadata={"source": html_file.filename, "type": "html_full"})
            documents.append(html_doc_full)

            html_doc_text = LangChainDocument(page_content=text_content, metadata={"source": html_file.filename, "type": "html_text"})
            documents.append(html_doc_text)

            logger.info(f"Parsed HTML file: {html_file.filename}")

            os.unlink(temp_html_path)
        except Exception as e:
            logger.error(f"Error processing HTML file {html_file.filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Error processing HTML file: {html_file.filename}")


    if not documents:
        logger.error("No documents were successfully loaded for ingestion.")
        raise HTTPException(status_code=400, detail="No valid documents were provided.")

    loop = asyncio.get_event_loop()
    text_splitter = CharacterTextSplitter(
        separator="\n\n",
        chunk_size=1000,
        chunk_overlap=200
    )
    split_docs = await loop.run_in_executor(None, text_splitter.split_documents, documents)

    filtered_docs = [doc for doc in split_docs if doc.page_content.strip()]
    logger.info(f"Filtered {len(split_docs)} documents to {len(filtered_docs)} after removing empty chunks.")

    if not filtered_docs:
        logger.error("No documents with content remain after chunking and filtering.")
        raise HTTPException(status_code=400, detail="No documents with content remain after processing.")

    try:
        texts = [doc.page_content for doc in filtered_docs]
        metadatas = [doc.metadata for doc in filtered_docs]

        if embedding_function is None:
             raise RuntimeError("Embedding function was not initialized correctly before vector store creation.")

        vector_store = await loop.run_in_executor(
            None,
            FAISS.from_texts,
            texts,
            embedding_function,
            metadatas,
        )

        os.makedirs(FAISS_PERSIST_DIR, exist_ok=True)
        vector_store.save_local(FAISS_PERSIST_DIR, index_name="faiss_index")
        logger.info(f"FAISS index saved to {FAISS_PERSIST_DIR}")

        logger.info("Knowledge Base built and persisted successfully using LangChain and FAISS.")
    except Exception as e:
        logger.error(f"Error creating or updating FAISS vector store: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error building the knowledge base: {e}")

async def retrieve_context(query: str, k: int = 4) -> List[str]:
    global vector_store, embedding_function
    if vector_store is None:
        if os.path.exists(FAISS_PERSIST_DIR):
            try:
                loop = asyncio.get_event_loop()
                loaded_store = await loop.run_in_executor(
                    None,
                    FAISS.load_local,
                    FAISS_PERSIST_DIR,
                    embedding_function,
                    "faiss_index",
                    allow_dangerous_deserialization=True
                )
                vector_store = loaded_store
                logger.info(f"FAISS index loaded from {FAISS_PERSIST_DIR}")
            except Exception as e:
                logger.error(f"Error loading FAISS index from {FAISS_PERSIST_DIR}: {e}")
                raise HTTPException(status_code=500, detail="Error loading knowledge base.")
        else:
            logger.error("FAISS index directory does not exist, and vector_store is not initialized.")
            raise HTTPException(status_code=500, detail="Knowledge base is not built yet.")

    if vector_store is None or embedding_function is None:
        logger.error("Vector store or embedding function is not initialized.")
        raise HTTPException(status_code=500, detail="Knowledge base is not built yet.")

    try:
        loop = asyncio.get_event_loop()
        docs = await loop.run_in_executor(None, vector_store.similarity_search, query, k)
        context_texts = [doc.page_content for doc in docs]
        logger.info(f"Retrieved {len(context_texts)} context chunks for query: {query[:50]}...")
        return context_texts
    except Exception as e:
        logger.error(f"Error retrieving context: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error retrieving context from knowledge base.")

async def retrieve_context_with_sources(query: str, k: int = 4) -> tuple[List[str], List[str]]:
    """Retrieves context chunks and their corresponding source filenames."""
    global vector_store, embedding_function
    if vector_store is None:
        if os.path.exists(FAISS_PERSIST_DIR):
            try:
                loop = asyncio.get_event_loop()
                loaded_store = await loop.run_in_executor(
                    None,
                    FAISS.load_local,
                    FAISS_PERSIST_DIR,
                    embedding_function,
                    "faiss_index",
                    allow_dangerous_deserialization=True
                )
                vector_store = loaded_store
                logger.info(f"FAISS index loaded from {FAISS_PERSIST_DIR}")
            except Exception as e:
                logger.error(f"Error loading FAISS index from {FAISS_PERSIST_DIR}: {e}")
                raise HTTPException(status_code=500, detail="Error loading knowledge base.")
        else:
            logger.error("FAISS index directory does not exist, and vector_store is not initialized.")
            raise HTTPException(status_code=500, detail="Knowledge base is not built yet.")

    if vector_store is None or embedding_function is None:
        logger.error("Vector store or embedding function is not initialized.")
        raise HTTPException(status_code=500, detail="Knowledge base is not built yet.")

    try:
        loop = asyncio.get_event_loop()
        docs = await loop.run_in_executor(None, vector_store.similarity_search, query, k)
        context_texts = [doc.page_content for doc in docs]
        source_files = [doc.metadata.get("source", "unknown_source") for doc in docs]
        logger.info(f"Retrieved {len(context_texts)} context chunks with sources for query: {query[:50]}...")
        return context_texts, source_files
    except Exception as e:
        logger.error(f"Error retrieving context with sources: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error retrieving context from knowledge base.")

async def generate_test_cases(query: str) -> List[TestCase]:
    context_texts, source_files = await retrieve_context_with_sources(query) # Use the new function
    context_str = "\n\n".join(context_texts)

    # Use the retrieved source files to build a more specific context description for the LLM
    # This might help it understand which documents are relevant.
    unique_sources = list(set(source_files)) # Get unique sources
    sources_str = ", ".join(unique_sources)

    prompt = f"""
    You are an expert QA engineer. Your task is to generate test cases based strictly on the provided project documentation and HTML structure.
    DO NOT hallucinate or create features not described in the context.
    Use the following context (from documents: {sources_str}) to understand the features and rules:
    <context>
    {context_str}
    </context>

    Based on the user's query: "{query}", generate a list of comprehensive test cases.
    Each test case must be structured as a JSON object with the following keys:
    - "Test_ID": A unique identifier like "TC-XXX".
    - "Feature": The feature being tested (e.g., "Discount Code", "Cart Summary").
    - "Test_Scenario": A detailed description of the test action.
    - "Expected_Result": The expected outcome of the test.
    - "Grounded_In": A LIST of strings containing the name(s) of the document(s) from the context that justify this test case (e.g., ["product_specs.md"], ["ui_ux_guide.txt", "api_endpoints.json"]).

    Provide ONLY the output as a valid JSON array of these test case objects.
    Do not include any other text, explanations, or markdown formatting like ```json before or after the array.
    The response must start with [ and end with ].
    Example format:
    [
      {{
        "Test_ID": "TC-001",
        "Feature": "Discount Code",
        "Test_Scenario": "Apply a valid discount code 'SAVE15'.",
        "Expected_Result": "Total price is reduced by 15%.",
        "Grounded_In": ["product_specs.md"]
      }},
      {{
        "Test_ID": "TC-002",
        "Feature": "Form Validation",
        "Test_Scenario": "Submit the user details form with an invalid email address.",
        "Expected_Result": "An error message 'Invalid email format' is displayed in red.",
        "Grounded_In": ["ui_ux_guide.txt", "product_specs.md"]
      }}
    ]
    """

    try:
        response = await client.chat.completions.create(
            model=OPENROUTER_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )

        content_str = response.choices[0].message.content
        logger.info(f"OpenRouter response for test cases: {content_str[:200]}...")

        try:
            parsed_response = json.loads(content_str)
        except json.JSONDecodeError:
            logger.warning("Initial JSON parse failed. Attempting to extract JSON from response...")
            json_match = re.search(r'\[.*\]', content_str, re.DOTALL)
            if json_match:
                extracted_json_str = json_match.group(0)
                logger.info(f"Extracted potential JSON: {extracted_json_str[:200]}...")
                try:
                    parsed_response = json.loads(extracted_json_str)
                    logger.info("Successfully parsed extracted JSON.")
                except json.JSONDecodeError as je_extracted:
                    logger.error(f"Failed to parse extracted JSON: {je_extracted}")
                    logger.debug(f"Extracted string: {extracted_json_str}")
                    raise HTTPException(status_code=500, detail="LLM returned invalid JSON for test cases (extraction failed).")
            else:
                logger.error("No JSON array found in LLM response.")
                logger.debug(f"LLM Response Content: {content_str}")
                raise HTTPException(status_code=500, detail="LLM returned invalid JSON for test cases (no array found).")

        test_cases_data = parsed_response
        if isinstance(test_cases_data, dict):
             test_cases_data = test_cases_data.get("test_cases", test_cases_data)

        processed_test_cases = []
        for tc in test_cases_data:
            # Process Grounded_In if it's a string (as before)
            if isinstance(tc.get("Grounded_In"), str):
                grounded_in_str = tc["Grounded_In"]
                grounded_in_list = [item.strip() for item in grounded_in_str.split(",") if item.strip()]
                tc["Grounded_In"] = grounded_in_list
                logger.debug(f"Converted Grounded_In from string to list: {grounded_in_list}")
            # --- NEW LOGIC: Use retrieved sources if LLM returned ["context"] or similar generic term ---
            elif isinstance(tc.get("Grounded_In"), list) and tc["Grounded_In"] == ["context"]:
                 # In this case, use the unique sources found during retrieval
                 tc["Grounded_In"] = unique_sources
                 logger.debug(f"Replaced ['context'] with retrieved sources: {unique_sources}")
            # Create the TestCase object with the (potentially modified) Grounded_In
            processed_tc = TestCase(**tc)
            processed_test_cases.append(processed_tc)

        logger.info(f"Generated {len(processed_test_cases)} test cases.")
        return processed_test_cases
    except json.JSONDecodeError as je:
        logger.error(f"Failed to decode JSON from LLM response after extraction attempts: {je}")
        logger.debug(f"LLM Response Content: {content_str}")
        raise HTTPException(status_code=500, detail="LLM returned invalid JSON for test cases.")
    except Exception as ve:
        logger.error(f"Error validating test case  {ve}")
        logger.debug(f"LLM Response Content: {content_str}")
        if "validation error" in str(ve).lower():
            import traceback
            logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="LLM returned incorrectly formatted test case data.")

async def generate_selenium_script(request: GenerateScriptRequest) -> str:
    test_case = request.test_case

    global vector_store, embedding_function
    if vector_store is None:
        await retrieve_context("dummy_query_to_load")

    if vector_store is None or embedding_function is None:
        logger.error("Vector store or embedding function is not initialized.")
        raise HTTPException(status_code=500, detail="Knowledge base is not built yet.")

    try:
        loop = asyncio.get_event_loop()
        html_docs = await loop.run_in_executor(None, vector_store.similarity_search, "checkout.html", 10)
        html_content = ""
        for doc in html_docs:
            if doc.metadata.get("source") == "checkout.html" and doc.metadata.get("type") == "html_full":
                 html_content = doc.page_content
                 break

        if not html_content:
             logger.error("checkout.html content not found in vector store.")
             raise HTTPException(status_code=500, detail="Target HTML file content not found in knowledge base.")

        context_texts = await retrieve_context(test_case.Test_Scenario, k=2)
        context_str = "\n\n".join(context_texts)

        prompt = f"""
        You are an expert Python Selenium developer.
        Your task is to generate a complete, executable Python script for the given test case scenario.
        You must use selectors that accurately match the elements in the provided HTML structure.
        Use the following HTML structure to identify the correct selectors:
        <html_structure>
        {html_content}
        </html_structure>

        Use the following context (from documentation) which might be relevant:
        <context>
        {context_str}
        </context>

        The test case to automate is:
        Test Scenario: {test_case.Test_Scenario}
        Expected Result: {test_case.Expected_Result}

        Generate a Python script using Selenium WebDriver that performs the steps described in the 'Test_Scenario'.
        The script should:
        1. Initialize the WebDriver (e.g., Chrome).
        2. Navigate to the page (you can assume the HTML file is served locally or use file:// protocol for demo).
        3. Perform the actions described in the scenario using correct selectors.
        4. Include basic error handling (e.g., WebDriverWait for dynamic elements if applicable, though this is a static HTML).
        5. Print a success message if the test passes according to the 'Expected_Result'.
        6. Quit the driver at the end.
        7. Use standard Python imports (e.g., from selenium import webdriver, from selenium.webdriver.common.by import By).

        Output only the Python code, nothing else. Ensure it's valid Python syntax.
        """

        response = await client.chat.completions.create(
            model=OPENROUTER_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )

        script_content = response.choices[0].message.content
        logger.info(f"Generated Selenium script (first 200 chars): {script_content[:200]}...")
        return script_content

    except Exception as e:
        logger.error(f"Error calling OpenRouter API for Selenium script: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error generating Selenium script.")

def is_knowledge_base_built() -> bool:
    global vector_store
    return vector_store is not None or os.path.exists(FAISS_PERSIST_DIR)
