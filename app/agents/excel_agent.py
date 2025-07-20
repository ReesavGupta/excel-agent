from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from typing import List, Dict, Any, Optional
import json
import logging
from data_tools.excel_tools import (
    read_worksheet_tool,
    filter_data_tool,
    aggregate_data_tool,
    sort_data_tool,
    pivot_table_tool,
    merge_worksheets_tool,
    split_worksheet_tool
)

logger = logging.getLogger(__name__)

class ExcelAgent:
    """Main agent that orchestrates Excel operations using LangChain"""
    
    def __init__(self, config, file_handler, column_mapper):
        self.config = config
        self.file_handler = file_handler
        self.column_mapper = column_mapper
        self.current_file = None
        self.current_file_info = None
        self.memory = []

        # Define tools first!
        self.tools = [
            read_worksheet_tool,
            filter_data_tool,
            aggregate_data_tool,
            sort_data_tool,
            pivot_table_tool,
            merge_worksheets_tool,
            split_worksheet_tool
        ]
        # Now bind tools to the LLM
        self.llm = ChatGroq(
            model_name=config.MODEL_NAME,
            temperature=config.TEMPERATURE,
            max_tokens=config.MAX_TOKENS,
            groq_api_key=config.GROQ_API_KEY
        ).bind_tools(self.tools)
    
    def load_file(self, file_path: str) -> Dict[str, Any]:
        """Load Excel file and set context"""
        try:
            self.current_file = file_path
            self.current_file_info = self.file_handler.get_file_info(file_path)
            
            # Set current file for tools
            self.current_file = file_path
            
            # Update memory with file context
            context_message = self._build_file_context()
            self.memory.append(SystemMessage(content=context_message))
            
            return {
                "success": True,
                "message": f"File loaded successfully: {self.current_file_info['file_size_mb']:.1f}MB, {len(self.current_file_info['sheet_names'])} sheets",
                "file_info": self.current_file_info
            }
            
        except Exception as e:
            logger.error(f"Error loading file: {e}")
            return {"success": False, "error": str(e)}
    
    def _build_file_context(self) -> str:
        """Build context message about the current file"""
        if not self.current_file_info:
            return ""
        
        context = f"""
CURRENT EXCEL FILE CONTEXT:
- File: {self.current_file}
- Size: {self.current_file_info['file_size_mb']:.1f} MB
- Sheets: {', '.join(self.current_file_info['sheet_names'])}

Sheet Details:
"""
        for sheet_name, info in self.current_file_info['sheet_info'].items():
            context += f"- {sheet_name}: {info['max_row']:,} rows × {info['max_column']} columns\n"
        
        context += """
AVAILABLE OPERATIONS:
- read_worksheet: Read data from a specific sheet
- filter_data: Apply filters to data
- aggregate_data: Perform groupby and aggregations
- sort_data: Sort data by columns
- pivot_table: Create pivot tables
- merge_worksheets: Merge multiple sheets
- split_worksheet: Split a worksheet into multiple files based on unique values in a column

When the user asks about data analysis, use these tools to provide accurate results.
Always specify the sheet_name when using tools.
"""
        return context
    
    def query(self, user_query: str, sheet_name: Optional[str] = None) -> Dict[str, Any]:
        """Process natural language query using LLM-driven tool calling and file_path injection"""
        try:
            if not self.current_file:
                return {"success": False, "error": "No file loaded. Please upload a file first."}

            from langchain_core.messages import HumanMessage, SystemMessage
            # Build context for the LLM
            system_message = SystemMessage(content=f"""
You are an Excel data analysis assistant. Use the available tools to answer user queries.
The current file is: {self.current_file}
IMPORTANT: If the user says 'first column', use the actual first column name from the sheet (e.g., 'MD' for Sheet2). If the column name is not found, use the first column.
""")
            user_message = HumanMessage(content=user_query)
            messages = [system_message, user_message]

            # Get LLM response (may include tool calls)
            response = self.llm.invoke(messages)

            # If the LLM called a tool, execute it with file_path injected
            if hasattr(response, 'tool_calls') and response.tool_calls:
                tool_results = []
                for tool_call in response.tool_calls:
                    tool_name = tool_call['name']
                    tool_args = tool_call['args']
                    # Inject file_path if the tool expects it
                    tool_args['file_path'] = self.current_file
                    for tool in self.tools:
                        if tool.name == tool_name:
                            try:
                                result = tool.invoke(tool_args)
                                tool_results.append(f"Tool {tool_name} result: {result}")
                            except Exception as e:
                                tool_results.append(f"Tool {tool_name} error: {str(e)}")
                            break
                final_response = f"Based on your query '{user_query}', here are the results:\n\n" + "\n\n".join(tool_results)
                return {
                    "success": True,
                    "query": user_query,
                    "response": final_response,
                    "tool_calls": response.tool_calls,
                    "context": {
                        "file": self.current_file,
                        "available_sheets": self.current_file_info['sheet_names'] if self.current_file_info else []
                    }
                }
            else:
                # No tool calls, just return the LLM's response
                return {
                    "success": True,
                    "query": user_query,
                    "response": getattr(response, 'content', str(response)),
                    "context": {
                        "file": self.current_file,
                        "available_sheets": self.current_file_info['sheet_names'] if self.current_file_info else []
                    }
                }
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {"success": False, "error": str(e)}
    
    def get_suggestions(self, partial_query: str) -> List[str]:
        """Get query suggestions based on current file"""
        if not self.current_file_info:
            return []
        
        suggestions = [
            f"Show me data from {sheet}" for sheet in self.current_file_info['sheet_names']
        ]
        
        # Add more contextual suggestions based on common patterns
        suggestions.extend([
            "Filter data where sales > 1000",
            "Show total sales by region",
            "Sort data by date descending",
            "Show top 10 customers by revenue"
        ])
        
        return suggestions[:5]  # Return top 5 suggestions
