# app/main.py (Phase 2 - Enhanced with LangChain)
import streamlit as st
import pandas as pd
import sys
from pathlib import Path
import logging
import json
from datetime import datetime
from dotenv import load_dotenv
import base64
from io import BytesIO

load_dotenv()

# Add app directory to path
sys.path.append(str(Path(__file__).parent))

# Import components
from config import Config
from data_tools.file_handler import ExcelFileHandler
from data_tools.column_mapper import ColumnMapper
from agents.excel_agent import ExcelAgent
from utils.query_parser import QueryParser
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Intelligent Excel Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize components
@st.cache_resource
def get_components():
    config = Config()
    file_handler = ExcelFileHandler(config)
    column_mapper = ColumnMapper()
    agent = ExcelAgent(config, file_handler, column_mapper)
    query_parser = QueryParser(column_mapper)
    return config, file_handler, column_mapper, agent, query_parser

def display_file_info(file_info):
    """Display comprehensive file information"""
    st.subheader("📋 File Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("File Size", f"{file_info['file_size_mb']:.1f} MB")
    with col2:
        st.metric("Worksheets", file_info['total_sheets'])
    with col3:
        largest_sheet = max(sheet['max_row'] for sheet in file_info['sheet_info'].values())
        st.metric("Max Rows", f"{largest_sheet:,}")
    with col4:
        total_rows = sum(sheet['max_row'] for sheet in file_info['sheet_info'].values())
        st.metric("Total Rows", f"{total_rows:,}")
    
    # Sheet details
    st.subheader("📊 Worksheet Details")
    sheet_data = []
    for name, info in file_info['sheet_info'].items():
        sheet_data.append({
            "Sheet Name": name,
            "Rows": f"{info['max_row']:,}",
            "Columns": info['max_column'],
            "Has Data": "✅" if info['has_data'] else "❌"
        })
    
    st.dataframe(pd.DataFrame(sheet_data), use_container_width=True)

def display_query_examples():
    """Display example queries"""
    st.subheader("💡 Example Queries")
    
    examples = [
        "Show me all data from Sheet1",
        "Filter sales data where revenue > 50000",
        "Show total sales by region",
        "Create a pivot table showing sales by product and month",
        "Sort customers by revenue in descending order",
        "Find all orders from the last 6 months",
        "Show average price by category",
        "List top 10 products by sales volume"
    ]
    
    cols = st.columns(2)
    for i, example in enumerate(examples):
        with cols[i % 2]:
            if st.button(example, key=f"example_{i}"):
                st.session_state.query_input = example

def make_arrow_compatible(df):
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str)
    return df

def process_query_response(response):
    """Process and display query response in a presentable format"""
    if response['success']:
        st.success("✅ Query processed successfully!")
        st.subheader("🎯 Results")
        try:
            if isinstance(response['response'], str) and 'Tool ' in response['response']:
                tool_blocks = response['response'].split('Tool ')
                for block in tool_blocks:
                    block = block.strip()
                    if not block:
                        continue
                    if 'result:' in block:
                        tool_name, json_part = block.split('result:', 1)
                        tool_name = tool_name.strip()
                        st.markdown(f"#### 🛠️ {tool_name}")
                        try:
                            parsed = json.loads(json_part)
                            if isinstance(parsed, dict):
                                # --- Chart preview image display ---
                                if 'preview_base64' in parsed and parsed['preview_base64']:
                                    st.write("**Chart Preview:**")
                                    img_bytes = base64.b64decode(parsed['preview_base64'])
                                    st.image(BytesIO(img_bytes))
                                # --- Special handling for split_worksheet ---
                                if tool_name == 'split_worksheet' and 'summary' in parsed:
                                    st.write("**Split Summary:**")
                                    for item in parsed['summary']:
                                        st.write(f"Value: {item['value']} | Rows: {item['rows']} | File: {item['file']}")
                                        df = pd.DataFrame(item['sample_data'])
                                        df = make_arrow_compatible(df)
                                        st.dataframe(df)
                                        import os
                                        if os.path.exists(item['file']):
                                            with open(item['file'], "rb") as f:
                                                st.download_button(f"Download {os.path.basename(item['file'])}", f, file_name=os.path.basename(item['file']))
                                # --- End special handling ---
                                if 'sample_results' in parsed and parsed['sample_results']:
                                    st.write("**Sample Results:**")
                                    df = pd.DataFrame(parsed['sample_results'])
                                    df = make_arrow_compatible(df)
                                    st.dataframe(df)
                                if 'sample_data' in parsed and parsed['sample_data']:
                                    st.write("**Sample Data:**")
                                    df = pd.DataFrame(parsed['sample_data'])
                                    df = make_arrow_compatible(df)
                                    st.dataframe(df)
                                if 'results' in parsed and parsed['results']:
                                    st.write("**Results:**")
                                    df = pd.DataFrame(parsed['results'])
                                    df = make_arrow_compatible(df)
                                    st.dataframe(df)
                                if 'summary_stats' in parsed and parsed['summary_stats']:
                                    st.write("**Summary Statistics:**")
                                    st.json(parsed['summary_stats'])
                                if 'error' in parsed:
                                    st.error(parsed['error'])
                                with st.expander("🔍 Full Tool Output"):
                                    st.json(parsed)
                            else:
                                st.write(parsed)
                        except Exception as e:
                            st.error(f"Could not parse tool output: {e}")
                            st.write(json_part)
                    else:
                        st.write(block)
            else:
                if isinstance(response['response'], str) and response['response'].startswith('{'):
                    parsed_response = json.loads(response['response'])
                    # --- Chart preview image display ---
                    if 'preview_base64' in parsed_response and parsed_response['preview_base64']:
                        st.write("**Chart Preview:**")
                        img_bytes = base64.b64decode(parsed_response['preview_base64'])
                        st.image(BytesIO(img_bytes))
                    # --- Special handling for split_worksheet ---
                    if 'summary' in parsed_response:
                        st.write("**Split Summary:**")
                        for item in parsed_response['summary']:
                            st.write(f"Value: {item['value']} | Rows: {item['rows']} | File: {item['file']}")
                            df = pd.DataFrame(item['sample_data'])
                            df = make_arrow_compatible(df)
                            st.dataframe(df)
                            import os
                            if os.path.exists(item['file']):
                                with open(item['file'], "rb") as f:
                                    st.download_button(f"Download {os.path.basename(item['file'])}", f, file_name=os.path.basename(item['file']))
                    # --- End special handling ---
                    if 'sample_data' in parsed_response:
                        st.write("**Sample Data:**")
                        df = pd.DataFrame(parsed_response['sample_data'])
                        df = make_arrow_compatible(df)
                        st.dataframe(df)
                    if 'results' in parsed_response:
                        st.write("**Results:**")
                        df = pd.DataFrame(parsed_response['results'])
                        df = make_arrow_compatible(df)
                        st.dataframe(df)
                    if 'summary_stats' in parsed_response and parsed_response['summary_stats']:
                        st.write("**Summary Statistics:**")
                        st.json(parsed_response['summary_stats'])
                    if 'shape' in parsed_response:
                        st.info(f"Result shape: {parsed_response['shape'][0]:,} rows × {parsed_response['shape'][1]} columns")
                    with st.expander("🔍 Full Response Details"):
                        st.json(parsed_response)
                else:
                    st.write(response['response'])
        except json.JSONDecodeError:
            st.write(response['response'])
    else:
        st.error(f"❌ Query failed: {response.get('error', 'Unknown error')}")

def main():
    st.title("🤖 Intelligent Excel Agent - Phase 2")
    st.markdown("*Powered by LangChain & Groq LLM*")
    
    # Get components
    config, file_handler, column_mapper, agent, query_parser = get_components()
    
    # Sidebar
    with st.sidebar:
        st.title("🎛️ Control Panel")
        
        # API Key input
        api_key = st.text_input(
            "Groq API Key", 
            type="password", 
            value=config.GROQ_API_KEY or "",
            help="Enter your Groq API key"
        )
        import os
        if api_key:
            config.GROQ_API_KEY = api_key
            os.environ["GROQ_API_KEY"] = api_key
        
        # Model selection
        model = st.selectbox(
            "LLM Model",
            ["llama3-8b-8192", "llama3-70b-8192", "mixtral-8x7b-32768", "gemma2-9b-it"],
            index=0
        )
        config.MODEL_NAME = model
        
        # Advanced settings
        with st.expander("⚙️ Advanced Settings"):
            config.TEMPERATURE = st.slider("Temperature", 0.0, 1.0, 0.1, 0.1)
            config.MAX_TOKENS = st.slider("Max Tokens", 500, 4000, 2000, 100)
            config.CHUNK_SIZE = st.slider("Chunk Size", 100, 5000, 1000, 100)
    
    # Main content area
    tab1, tab2, tab3 = st.tabs(["📁 File Upload", "🤖 AI Assistant", "📊 Data Explorer"])
    
    with tab1:
        st.header("📁 File Upload & Analysis")
        
        # File upload
        uploaded_file = st.file_uploader(
            f"Upload Excel file (max {config.MAX_FILE_SIZE_MB}MB)", 
            type=["xlsx", "xls"],
            help="Supported formats: .xlsx, .xls"
        )
        
        if uploaded_file is not None:
            try:
                # Save uploaded file
                upload_dir = Path("uploads")
                upload_dir.mkdir(exist_ok=True)
                file_path = upload_dir / uploaded_file.name
                
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                st.success(f"✅ File '{uploaded_file.name}' uploaded successfully!")
                
                # Load file into agent
                with st.spinner("🔄 Loading file into AI agent..."):
                    load_result = agent.load_file(str(file_path))
                
                if load_result['success']:
                    st.success("🤖 File loaded into AI agent!")
                    
                    # Store file info in session state
                    st.session_state['file_loaded'] = True
                    st.session_state['file_info'] = load_result['file_info']
                    st.session_state['agent'] = agent
                    
                    # Display file information
                    display_file_info(load_result['file_info'])
                    
                else:
                    st.error(f"❌ Failed to load file: {load_result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                st.error(f"❌ Error processing file: {str(e)}")
                logger.error(f"File processing error: {e}")
    
    with tab2:
        st.header("🤖 AI Assistant")
        
        if not st.session_state.get('file_loaded', False):
            st.warning("⚠️ Please upload and load a file first in the File Upload tab.")
            return
        
        if not config.GROQ_API_KEY:
            st.warning("⚠️ Please enter your Groq API key in the sidebar.")
            return
        
        # Query examples
        display_query_examples()
        
        # Query input
        st.subheader("💬 Ask Questions About Your Data")
        
        # Text input with session state
        if 'query_input' not in st.session_state:
            st.session_state.query_input = ""
        
        query = st.text_area(
            "Enter your question:",
            value=st.session_state.query_input,
            height=100,
            placeholder="e.g., Show me sales data where revenue > 50000"
        )
        
        col1, col2 = st.columns([1, 4])
        
        with col1:
            submit_query = st.button("🚀 Submit Query", type="primary")
        
        with col2:
            clear_query = st.button("🗑️ Clear")
            if clear_query:
                st.session_state.query_input = ""
                st.rerun()
        
        # Process query
        if submit_query and query.strip():
            with st.spinner("🤖 AI is analyzing your request..."):
                try:
                    # Get the agent from session state
                    current_agent = st.session_state.get('agent')
                    if current_agent:
                        response = current_agent.query(query)
                        process_query_response(response)
                        
                        # Store in query history
                        if 'query_history' not in st.session_state:
                            st.session_state.query_history = []
                        
                        st.session_state.query_history.append({
                            'timestamp': datetime.now().strftime("%H:%M:%S"),
                            'query': query,
                            'response': response
                        })
                    else:
                        st.error("❌ Agent not available. Please reload the file.")
                        
                except Exception as e:
                    st.error(f"❌ Error processing query: {str(e)}")
                    logger.error(f"Query processing error: {e}")
        
        # Query history
        if st.session_state.get('query_history'):
            st.subheader("📚 Query History")
            
            for i, item in enumerate(reversed(st.session_state.query_history[-5:])):  # Show last 5
                with st.expander(f"[{item['timestamp']}] {item['query'][:50]}..."):
                    st.write(f"**Query:** {item['query']}")
                    if item['response']['success']:
                        st.write(f"**Response:** {item['response']['response'][:200]}...")
                    else:
                        st.error(f"**Error:** {item['response'].get('error', 'Unknown error')}")
    
    with tab3:
        st.header("📊 Data Explorer")
        if not st.session_state.get('file_loaded', False):
            st.warning("⚠️ Please upload and load a file first in the File Upload tab.")
            return
        file_info = st.session_state.get('file_info', {})
        # --- Split Worksheet UI ---
        st.subheader("✂️ Split Worksheet by Column")
        columns = []
        if file_info.get('sheet_names'):
            selected_sheet_split = st.selectbox(
                "Select Worksheet (Split):",
                file_info['sheet_names'],
                key="split_sheet_selector"
            )
            if selected_sheet_split:
                sheet_info_split = file_info['sheet_info'][selected_sheet_split]
                st.info(f"**{selected_sheet_split}**: {sheet_info_split['max_row']:,} rows × {sheet_info_split['max_column']} columns")
                load_columns = st.button("🔄 Load Columns", key="load_columns_btn")
                if load_columns:
                    try:
                        current_agent = st.session_state.get('agent')
                        response = current_agent.query(f"Show me the first 1 rows from {selected_sheet_split}")
                        if response['success']:
                            try:
                                parsed = json.loads(response['response'].split('result:',1)[1])
                                if 'sample_data' in parsed and parsed['sample_data']:
                                    columns = list(parsed['sample_data'][0].keys())
                            except Exception:
                                pass
                        if not columns:
                            columns = [f"Column {i+1}" for i in range(sheet_info_split['max_column'])]
                    except Exception:
                        columns = []
                split_column = st.selectbox("Select column to split by:", columns, key="split_column_selector")
                split_btn = st.button("✂️ Split Worksheet", key="split_btn")
                if split_btn and split_column:
                    with st.spinner(f"Splitting {selected_sheet_split} by '{split_column}'..."):
                        try:
                            current_agent = st.session_state.get('agent')
                            split_response = current_agent.query(f"Split {selected_sheet_split} by the '{split_column}' column, so each value gets its own Excel file.")
                            if split_response['success']:
                                st.success("Worksheet split successfully!")
                                try:
                                    parsed = json.loads(split_response['response'].split('result:',1)[1])
                                    if 'summary' in parsed:
                                        st.write("**Split Summary:**")
                                        for item in parsed['summary']:
                                            st.write(f"Value: {item['value']} | Rows: {item['rows']} | File: {item['file']}")
                                            df = pd.DataFrame(item['sample_data'])
                                            df = make_arrow_compatible(df)
                                            st.dataframe(df)
                                            if os.path.exists(item['file']):
                                                with open(item['file'], "rb") as f:
                                                    st.download_button(f"Download {os.path.basename(item['file'])}", f, file_name=os.path.basename(item['file']))
                                except Exception as e:
                                    st.error(f"Could not parse split summary: {e}")
                                    st.write(split_response['response'])
                            else:
                                st.error(f"Split failed: {split_response.get('error', 'Unknown error')}")
                        except Exception as e:
                            st.error(f"Error splitting worksheet: {e}")
                st.markdown("---")
        # --- Write Results UI ---
        st.subheader("💾 Save Worksheet or Data to Excel File")
        if file_info.get('sheet_names'):
            save_sheet = st.selectbox(
                "Select Worksheet to Save:",
                file_info['sheet_names'],
                key="save_sheet_selector"
            )
            output_file_name = st.text_input("Output File Name (optional):", value="")
            save_btn = st.button("💾 Save Worksheet", key="save_btn")
            if save_btn and save_sheet:
                with st.spinner(f"Saving {save_sheet} to Excel file..."):
                    try:
                        current_agent = st.session_state.get('agent')
                        query = f"Save {save_sheet} as a new Excel file"
                        if output_file_name.strip():
                            query += f" named '{output_file_name.strip()}'"
                        response = current_agent.query(query)
                        if response['success']:
                            st.success("Worksheet saved successfully!")
                            try:
                                parsed = json.loads(response['response'].split('result:',1)[1])
                                st.write(f"**File:** {parsed['output_file']}")
                                st.write(f"**Rows:** {parsed['rows']}")
                                st.write(f"**Columns:** {', '.join(parsed['columns'])}")
                                df = pd.DataFrame(parsed['sample_data'])
                                df = make_arrow_compatible(df)
                                st.dataframe(df)
                                import os
                                if os.path.exists(parsed['output_file']):
                                    with open(parsed['output_file'], "rb") as f:
                                        st.download_button(f"Download {os.path.basename(parsed['output_file'])}", f, file_name=os.path.basename(parsed['output_file']))
                            except Exception as e:
                                st.error(f"Could not parse save result: {e}")
                                st.write(response['response'])
                        else:
                            st.error(f"Save failed: {response.get('error', 'Unknown error')}")
                    except Exception as e:
                        st.error(f"Error saving worksheet: {e}")
        st.markdown("---")
        # --- Sample Data Loader ---
        if file_info.get('sheet_names'):
            selected_sheet_sample = st.selectbox(
                "Select Worksheet (Sample):",
                file_info['sheet_names'],
                key="sample_sheet_selector"
            )
            if selected_sheet_sample:
                sheet_info_sample = file_info['sheet_info'][selected_sheet_sample]
                st.info(f"**{selected_sheet_sample}**: {sheet_info_sample['max_row']:,} rows × {sheet_info_sample['max_column']} columns")
                col1, col2 = st.columns(2)
                with col1:
                    sample_size = st.slider("Sample Size", 10, 1000, 100)
                with col2:
                    load_sample = st.button("📥 Load Sample Data")
                if load_sample:
                    with st.spinner("Loading sample data..."):
                        try:
                            current_agent = st.session_state.get('agent')
                            if current_agent:
                                response = current_agent.query(f"Show me the first {sample_size} rows from {selected_sheet_sample}")
                                process_query_response(response)
                        except Exception as e:
                            st.error(f"❌ Error loading sample: {str(e)}")

if __name__ == "__main__":
    main()