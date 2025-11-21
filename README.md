
# Autonomous QA Agent

This project implements an intelligent, autonomous QA agent capable of constructing a "testing brain" from project documentation and HTML structure. It ingests support documents and the target HTML, then generates documentation-grounded test cases and converts them into executable Python Selenium scripts.

## Table of Contents

*   [Features](#features)
*   [Prerequisites](#prerequisites)
*   [Project Structure](#project-structure)
*   [Setup Instructions](#setup-instructions)
    *   [1. Clone the Repository](#1-clone-the-repository)
    *   [2. Install `uv` (if not already installed)](#2-install-uv-if-not-already-installed)
    *   [3. Set up Virtual Environment and Dependencies](#3-set-up-virtual-environment-and-dependencies)
    *   [4. Configure Environment Variables](#4-configure-environment-variables)
*   [How to Run](#how-to-run)
    *   [1. Start the FastAPI Backend](#1-start-the-fastapi-backend)
    *   [2. Start the Streamlit UI](#2-start-the-streamlit-ui)
*   [Usage Examples](#usage-examples)
*   [Evaluation Criteria Compliance](#evaluation-criteria-compliance)
*   [Project Assets Explanation](#project-assets-explanation)
    *   [1. `checkout.html` (Target File)](#1-checkouthtml-target-file)
    *   [2. `product_specs.md` (Example)](#2-product_specsmd-example)
    *   [3. `ui_ux_guide.txt` (Example)](#3-ui_ux_guidetxt-example)
    *   [4. `api_endpoints.json` (Example - Optional)](#4-api_endpointsjson-example---optional)
*   [Demo Video](#demo-video)
*   [Dependencies](#dependencies)
*   [Contributing](#contributing) (Optional)
*   [License](#license) (Optional)

## Features

*   **Knowledge Base Ingestion:** Accepts support documents (`.md`, `.txt`, `.json`, `.pdf`) and a target HTML file (e.g., `checkout.html`).
*   **Test Case Generation:** Generates comprehensive test cases based on user queries, strictly grounded in the provided documentation.
*   **Selenium Script Generation:** Converts selected test cases into runnable Python Selenium scripts tailored to the specific HTML structure.
*   **User-Friendly UI:** Provides an intuitive Streamlit interface for interaction.
*   **Persistence:** Uses FAISS for vector storage, allowing the knowledge base to persist between runs.
*   **Asynchronous Operations:** Backend operations (like model loading, vector store interactions) are handled asynchronously where appropriate for better performance.
*   **Embedding Model Caching:** Downloads and caches the HuggingFace embedding model locally for faster subsequent startups.

## Prerequisites

*   **Python:** Version 3.10 or higher is recommended.
*   **`uv` Package Manager:** Used for project setup, virtual environment management, and dependency installation. [Installation guide](https://github.com/astral-sh/uv#installation).
*   **OpenRouter API Key:** You need an API key for OpenRouter to use the LLM for test case and script generation.

## Project Structure

```
OceanAI-QA-Agent/
│
├── app/
│   ├── main.py             # FastAPI backend entry point
│   ├── rag.py              # RAG logic (ingestion, retrieval, agents)
│   └── models.py           # Pydantic models for request/response
│
├── ui/
│   └── ui.py               # Streamlit application entry point
│
├── assets/                 # (Optional) Store your example checkout.html and support docs here for reference
│   ├── checkout.html       # The target HTML file (example)
│   ├── product_specs.md    # Example support document (example)
│   ├── ui_ux_guide.txt     # Example support document (example)
│   └── api_endpoints.json  # Example support document (example)
│
├── models_cache/           # (Optional) Directory where embedding models are cached (created automatically)
│
├── faiss_index/            # (Optional) Directory where FAISS index is persisted (created automatically)
│
├── .env                    # Environment variables file (user needs to create this)
├── README.md               # This file
└── uv.lock                 # uv lock file (auto-generated, defines exact dependency versions)
```

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd OceanAI-QA-Agent
```

### 2. Install `uv` (if not already installed)

If you haven't installed `uv`, follow the instructions on the [official repository](https://github.com/astral-sh/uv#installation).

### 3. Set up Virtual Environment and Dependencies

Navigate to the project directory and use `uv` to create a virtual environment and install dependencies:

```bash
# Create and activate virtual environment, install dependencies from uv.lock (recommended)
uv sync

# Alternatively, if you want to install from a requirements.txt file instead of uv.lock:
# uv pip install -r requirements.txt
# (Note: This might install slightly different versions than locked in uv.lock)
```

This command will:
*   Create a new virtual environment within the project (`.venv` folder).
*   Install all necessary Python packages listed in `uv.lock` into this environment.

### 4. Configure Environment Variables

1.  Create a file named `.env` in the root directory of the project (`OceanAI-QA-Agent/`).
2.  Add your OpenRouter API key and other configuration details to the `.env` file:

    ```ini
    OPENROUTER_API_KEY=your_openrouter_api_key_here
    OPENROUTER_MODEL_NAME=openai/gpt-4o # Or another model you prefer from OpenRouter
    EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2 # Or another HuggingFace embedding model
    FAISS_PERSIST_DIR=./faiss_index # Directory to save the FAISS index (optional, default is ./faiss_index)
    ```

    Replace `your_openrouter_api_key_here` with your actual OpenRouter API key.

## How to Run

### 1. Start the FastAPI Backend

Open a terminal, navigate to your project directory (`OceanAI-QA-Agent/`), ensure your `uv` virtual environment is active (it should be if you used `uv sync`), and run:

```bash
uv run uvicorn app.main:app --reload
```

The backend will start, typically on `http://127.0.0.1:8000`. The `--reload` flag enables auto-reloading when code changes.

### 2. Start the Streamlit UI

Open *another* terminal, navigate to the same project directory (`OceanAI-QA-Agent/`), ensure your `uv` virtual environment is active, and run:

```bash
uv run streamlit run ui/ui.py
```

The Streamlit UI will open in your default web browser, typically on `http://localhost:8501`.

## Usage Examples

1.  **Prepare Project Assets:**
    *   Create or gather your support documents (e.g., `product_specs.md`, `ui_ux_guide.txt`, `api_endpoints.json`). These should define the rules and guidelines for your target HTML page (e.g., `checkout.html`). Example content is provided in the [Project Assets Explanation](#project-assets-explanation) section below.
    *   Ensure you have the target HTML file (`checkout.html`) ready.

2.  **Build the Knowledge Base:**
    *   In the Streamlit UI, go to the sidebar.
    *   Upload your support documents using the "Upload Support Documents" uploader.
    *   Upload the `checkout.html` file using the "Upload checkout.html" uploader.
    *   Click the "Build Knowledge Base" button. The system will process the files, chunk the text, generate embeddings, and store them in the FAISS vector database. You should see a success message.

3.  **Generate Test Cases:**
    *   Once the knowledge base is built, go to the main UI area.
    *   Enter a query in the text input field (e.g., "Generate all positive and negative test cases for the discount code feature.").
    *   Click the "Generate Test Cases" button.
    *   The generated test cases will be displayed in a table, showing `ID`, `Feature`, `Scenario`, `Expected Result`, and `Grounded In` (the source document).

4.  **Generate Selenium Script:**
    *   From the generated test cases, select one using the dropdown menu.
    *   Click the "Generate Selenium Script" button.
    *   The corresponding Python Selenium script will be generated and displayed in a code block, ready for copying.

## Evaluation Criteria Compliance

This project addresses the assignment's evaluation criteria as follows:

1.  **Functionality:** The system successfully completes all required phases: ingesting documents/HTML, building the knowledge base, generating test cases, and generating Selenium scripts.
2.  **Knowledge Grounding:** The RAG (Retrieval-Augmented Generation) pipeline ensures that both test case generation and script generation are strictly based on the content retrieved from the vector database, which is populated only from the uploaded documents and HTML. The prompt engineering emphasizes grounding in the provided context.
3.  **Script Quality:** The script generation prompt explicitly instructs the LLM to act as a Selenium expert, use selectors matching the provided HTML structure, and produce clean, executable Python code.
4.  **Code Quality:** The code is modular, separating concerns into `app/` (backend), `ui/` (frontend), and `models/`. It uses FastAPI for the backend and Streamlit for the UI as required. Asynchronous operations are used where appropriate. Pydantic models ensure data validation.
5.  **User Experience:** The Streamlit UI provides a simple, step-by-step workflow with clear buttons and feedback messages (e.g., success/error messages, loading spinners).
6.  **Documentation:** This `README.md` file provides detailed instructions for setup, running, usage, and explains the project assets.

## Project Assets Explanation

The agent requires 3-5 support documents to understand the features and rules of the target HTML page. Based on the assignment example, here are the types of documents you should provide:

### 1. `checkout.html` (Target File)

*   The single-page HTML file representing the e-shop checkout page. The agent uses this to understand the structure and generate accurate Selenium selectors.
*   Example features it might contain (as per assignment):
    *   Add to Cart buttons
    *   Cart summary
    *   Discount code input
    *   User Details form
    *   Form validation
    *   Shipping/Payment radio buttons
    *   Pay Now button

### 2. `product_specs.md` (Example)

*   Defines the core business logic and feature behavior.
*   Example content:
    ```markdown
    # Product Specifications

    ## Discount Code
    - The discount code `SAVE15` applies a 15% discount to the total cart value.
    - Only one discount code can be applied at a time.
    - Discount codes are case-insensitive.

    ## Shipping
    - Express shipping costs $10.
    - Standard shipping is free.

    ## Cart
    - Items can be added to the cart using the "Add to Cart" buttons.
    - Item quantities in the cart can be adjusted.
    ```

### 3. `ui_ux_guide.txt` (Example)

*   Defines the visual appearance, user experience, and UI element behavior.
*   Example content:
    ```
    UI/UX Guidelines

    Form Validation:
    - Form validation errors must be displayed in red text below the relevant input field.
    - Required fields should have an asterisk (*) next to their label.

    Buttons:
    - The "Pay Now" button should be green.
    - Disabled buttons should appear grayed out.
    ```

### 4. `api_endpoints.json` (Example - Optional)

*   Defines the API endpoints the frontend might interact with.
*   Example content:
    ```json
    {
      "POST /apply_coupon": {
        "request_body": {
          "code": "string"
        },
        "response": {
          "success": "boolean",
          "message": "string",
          "new_total": "number"
        }
      },
      "POST /submit_order": {
        "request_body": {
          "name": "string",
          "email": "string",
          "address": "string",
          "shipping_method": "string",
          "payment_method": "string"
        },
        "response": {
          "success": "boolean",
          "message": "string"
        }
      }
    }
    ```

Ensure these files accurately describe the features and rules of your `checkout.html` file for the best results.

## Demo Video

A 5-10 minute demo video demonstrating the following steps is available [here](link_to_your_demo_video.mp4):

1.  Uploading documents and HTML.
2.  Building the knowledge base.
3.  Generating test cases.
4.  Selecting a test case.
5.  Generating a Selenium script.

## Dependencies

This project relies on the following key dependencies, managed by `uv`:

*   `fastapi`: Web framework for the backend API.
*   `uvicorn`: ASGI server for running the FastAPI app.
*   `streamlit`: Framework for the user interface.
*   `python-dotenv`: For loading environment variables from `.env`.
*   `openai`: Async client for interacting with OpenRouter API.
*   `langchain`: Framework for RAG.
*   `langchain-text-splitters`: For text chunking.
*   `langchain-community`: Provides vector stores (FAISS) and embeddings (HuggingFace).
*   `faiss-cpu`: Vector database library.
*   `pymupdf`: For PDF parsing.
*   `beautifulsoup4`: For HTML parsing.
*   `sentence-transformers`: For the embedding model.

A full list of dependencies and their exact versions is locked in the `uv.lock` file.

## Contributing

OceanAI (MariApps Marine Solutions Private Limited) - Assignment by ```Kanha Khantaal``` 

## License

MIT — free to use, modify, and deploy.