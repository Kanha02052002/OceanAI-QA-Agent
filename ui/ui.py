import streamlit as st
import requests
import json

BACKEND_URL = "http://127.0.0.1:8000" 

st.set_page_config(page_title="Autonomous QA Agent", layout="wide")
st.title("Autonomous QA Agent")
st.markdown("*Build your testing brain from documentation.*")

if "kb_built" not in st.session_state:
    st.session_state.kb_built = False
if "generated_test_cases" not in st.session_state:
    st.session_state.generated_test_cases = []
if "selected_test_case" not in st.session_state:
    st.session_state.selected_test_case = None
if "generated_script" not in st.session_state:
    st.session_state.generated_script = ""

st.sidebar.header("1. Build Knowledge Base")
uploaded_docs = st.sidebar.file_uploader(
    "Upload Support Documents (.md, .txt, .json, .pdf)",
    type=["md", "txt", "json", "pdf"],
    accept_multiple_files=True
)
uploaded_html = st.sidebar.file_uploader(
    "Upload checkout.html",
    type=["html", "htm"]
)

if st.sidebar.button("Build Knowledge Base", type="primary"):
    if not uploaded_docs or not uploaded_html:
        st.sidebar.error("Please upload both support documents and the HTML file.")
    else:
        try:
            files = []
            for doc in uploaded_docs:
                files.append(("documents", (doc.name, doc.getvalue(), doc.type)))
            files.append(("html_file", (uploaded_html.name, uploaded_html.getvalue(), uploaded_html.type)))

            with st.spinner("Building Knowledge Base... This may take a moment."):
                response = requests.post(f"{BACKEND_URL}/build_knowledge_base", files=files)

            if response.status_code == 200:
                st.session_state.kb_built = True
                st.sidebar.success(response.json()["message"])
            else:
                st.sidebar.error(f"Error: {response.status_code} - {response.text}")

        except requests.exceptions.ConnectionError:
            st.sidebar.error("Could not connect to the backend. Is FastAPI running?")
        except Exception as e:
            st.sidebar.error(f"An error occurred: {e}")

if st.session_state.kb_built:
    st.sidebar.success("Knowledge Base Built!")
else:
    st.sidebar.warning("Please build the knowledge base first.")


if st.session_state.kb_built:
    st.header("2. Generate Test Cases")
    query = st.text_input("Enter your query for test cases (e.g., 'Generate test cases for the discount code feature.')")

    if st.button("Generate Test Cases"):
        if not query:
            st.error("Please enter a query.")
        else:
            try:
                with st.spinner("Generating Test Cases..."):
                    payload = {"query": query}
                    response = requests.post(f"{BACKEND_URL}/generate_test_cases", json=payload)

                if response.status_code == 200:
                    data = response.json()
                    st.session_state.generated_test_cases = data.get("test_cases", [])
                    st.session_state.selected_test_case = None 
                    st.session_state.generated_script = ""
                    st.success(f"Generated {len(st.session_state.generated_test_cases)} test cases!")
                else:
                    st.error(f"Error from backend: {response.status_code} - {response.text}")

            except requests.exceptions.ConnectionError:
                st.error("Could not connect to the backend.")
            except Exception as e:
                st.error(f"An error occurred: {e}")

    if st.session_state.generated_test_cases:
        st.subheader("Generated Test Cases")
        table_data = []
        for tc in st.session_state.generated_test_cases:
            table_data.append({
                    "ID": tc["Test_ID"],
                    "Feature": tc["Feature"],
                    "Scenario": tc["Test_Scenario"],
                    "Expected Result": tc["Expected_Result"],
                    "Grounded In": tc["Grounded_In"]
            })
        st.table(table_data)

        st.header("3. Generate Selenium Script")
        selected_tc_index = st.selectbox(
            "Select a test case to generate a script for:",
            options=range(len(st.session_state.generated_test_cases)),
            format_func=lambda x: f"{st.session_state.generated_test_cases[x]['Test_ID']}: {st.session_state.generated_test_cases[x]['Test_Scenario'][:50]}..."
        )

        if st.button("Generate Selenium Script"):
            if selected_tc_index is not None:
                selected_tc = st.session_state.generated_test_cases[selected_tc_index]
                st.session_state.selected_test_case = selected_tc

                try:
                    with st.spinner("Generating Selenium Script..."):
                        payload = {"test_case": selected_tc}
                        response = requests.post(f"{BACKEND_URL}/generate_selenium_script", json=payload)

                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.generated_script = data.get("script", "")
                        st.success("Selenium script generated!")
                    else:
                        st.error(f"Error from backend: {response.status_code} - {response.text}")

                except requests.exceptions.ConnectionError:
                    st.error("Could not connect to the backend.")
                except Exception as e:
                    st.error(f"An error occurred: {e}")
            else:
                st.error("Please select a test case first.")

        if st.session_state.generated_script:
            st.subheader(f"Selenium Script for '{st.session_state.selected_test_case['Test_ID']}'")
            st.code(st.session_state.generated_script, language='python')

else:
    st.info("Please build the knowledge base in the sidebar to get started.")

st.markdown("---")
