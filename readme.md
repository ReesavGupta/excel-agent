# Intelligent Excel Agent

An advanced, production-ready Excel agent built with LangChain, pandas, openpyxl, and Streamlit. This agent processes large Excel files, understands natural language queries, and robustly handles real-world edge cases—including inconsistent column naming, multilingual headers, and concurrent users.

---

## 🚀 Features

### 1. Large File & Multi-Tab Handling
- **Supports 10,000+ rows and multiple worksheets** per file.
- **Memory-efficient chunking**: Reads large sheets in manageable chunks to avoid memory exhaustion.
- **Handles all data types**: Numeric, string, date, and mixed-type columns.
- **Worksheet navigation**: Users can select, list, and switch between sheets in the UI.

### 2. Natural Language Processing
- **LLM-powered query interpretation**: Users can ask questions in plain English.
- **Automatic tool selection**: The agent chooses the right tool (filter, aggregate, pivot, etc.) based on the query.
- **Supports complex analysis**: Filtering, aggregation, sorting, pivot tables, and more.

### 3. LangChain Tools
- **Core tools**: `read_worksheet`, `filter_data`, `aggregate_data`, `sort_data`, `pivot_table`, `write_results`
- **Advanced tools**: `merge_worksheets`, `data_validation`, `formula_evaluation`, `chart_generation`
- **All tools are LLM-driven and robust to edge cases.**

### 4. LLM Integration
- **Groq LLM (Llama3, Mixtral, etc.)** via LangChain for fast, accurate inference.
- **Prompt engineering**: Custom system prompts guide the LLM to use the correct tools and handle ambiguous queries.
- **Error handling and context management**: User-friendly error messages and session memory.

### 5. Column Name Mapping
- **Fuzzy matching**: Handles snake_case, camelCase, Proper Case, special characters, and multilingual headers.
- **Synonym dictionary**: Maps business terms and common synonyms (e.g., "qty" → "quantity").
- **LLM-assisted suggestions**: If confidence is low, the agent can prompt the user for clarification.

### 6. Production Edge Cases
- **File issues**: Detects and reports corrupted files, password protection, merged cells, and memory limits.
- **Data issues**: Handles empty sheets, inconsistent data types, missing values, and date format inconsistencies.
- **User input**: Robust to ambiguous queries, non-existent columns, and conflicting conditions.
- **System issues**: File size and row count checks prevent memory exhaustion; per-user file isolation for concurrency.

### 7. Technical Specs
- **Handles files up to 100MB** (configurable).
- **Processes queries within 10 seconds** (with chunking and size checks).
- **Supports concurrent users**: Each user/session has isolated uploads and results.
- **Follows coding standards**: Modular, type-annotated, and well-documented code.
- **Security**: Input validation, file size/type checks, and per-user file isolation.

### 8. UI/UX
- **Streamlit web interface**: File upload, query input, and results display.
- **Progress indicators**: Spinners and status messages for long-running operations.
- **Results in tables and charts**: DataFrames, summary stats, and chart previews (bar, pie, etc.).
- **Downloadable results and charts**.

---

## 🏗️ Design Choices

### Technology Stack
- **Python**: Chosen for its rich data ecosystem and LLM integration.
- **pandas + openpyxl**: For robust Excel file handling and data analysis.
- **LangChain**: For LLM-driven tool calling and prompt management.
- **Streamlit**: For rapid, interactive web UI development.
- **file_handler**: Centralizes file validation, chunked reading, and info extraction.
- **column_mapper**: Handles fuzzy, synonym, and multilingual column mapping.

### Concurrency & Isolation
- **Per-user file isolation**: Each user/session gets a unique directory for uploads, preventing collisions and data leakage.
- **No file locking**: File locking was tested but removed for simplicity and to avoid deadlocks; per-user isolation is safer for Streamlit.

### Error Handling
- **User-friendly messages**: All errors (file issues, tool errors, ambiguous queries) are caught and shown to the user.
- **Edge case detection**: Corrupted files, password protection, and oversized files are detected before processing.

### Security
- **Input validation**: File size/type checks, row count limits.
- **No global state**: All user data is session-scoped.
- **No sensitive data in logs/UI**: API keys and user files are never exposed.

### Extensibility
- **Modular tools**: New Excel tools can be added easily.
- **LLM-agnostic**: Can switch to OpenAI, Claude, Gemini, or Ollama with minimal changes.
- **Easy deployment**: Can be run locally or on any cloud VM with Python and Streamlit.

---

## 💡 Example Queries

- "Show sales data for Q3 2024 where revenue > 50000"
- "Create pivot table showing total sales by region and product"
- "Find customers who haven't ordered in 6 months"
- "Plot a pie chart of the count of each value in column MD in Sheet1"
- "Merge Sheet1 and Sheet2 using MD as the key, only keeping rows where MD exists in both sheets"

---

## 🛠️ How to Run

1. **Clone the repository**
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
3. **Set your Groq API key** (or other LLM provider) in `.env` or via the UI.
4. **Run the app**
   ```bash
   streamlit run app/main.py
   ```
5. **Open in your browser** at [http://localhost:8501](http://localhost:8501)

---

## 📁 Directory Structure

```
excel-agent/
  app/
    main.py                # Streamlit UI
    data_tools/
      file_handler.py      # File validation, chunking, info
      column_mapper.py     # Fuzzy/synonym column mapping
      excel_tools.py       # All Excel tool functions
    agents/
      excel_agent.py       # LLM agent logic
    utils/
      query_parser.py      # Query parsing helpers
    config.py              # App configuration
  uploads/                 # Per-user uploaded files
  requirements.txt
  README.md
```

---

## 📝 Technical Documentation

- **All core and advanced tools are documented in `excel_tools.py` and `column_mapper.py`.**
- **Configuration options** (max file size, chunk size, etc.) are in `config.py`.
- **Session/user isolation** is handled in `main.py` using `st.session_state`.
- **Error handling and logging** are present in all major modules.

---

## ✅ Deliverables

- [x] GitHub repository with all source code
- [x] Technical documentation (this README and in-code docstrings)
- [x] Fully working, production-ready Excel agent as described above

---

## 📣 Contact & Support

For questions, issues, or feature requests, please open an issue on the repository or contact the maintainer.
