from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferMemory
from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from typing import List, Dict, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)

class ExcelAgent:
    """Main agent that orchestrates Excel operations using LangChain"""
    
    def __init__(self, config, file_handler, column_mapper):
        self.config = config
        self.file_handler = file_handler
        self.column_mapper = column_mapper
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model=config.MODEL_NAME,
            temperature=config.TEMPERATURE,
            max_tokens=config.MAX_TOKENS,
            openai_api_key=config.OPENAI_API_KEY
        )
        
        # Initialize memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Initialize tools
        self.tools = self._initialize_tools()
        
        # Initialize agent
        self.agent = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True
        )
        
        self.current_file = None
        self.current_file_info = None
    
    def _initialize_tools(self):
        """Initialize all Excel tools"""
        from ..data_tools.excel_tools import (
            ReadWorksheetTool, FilterDataTool, AggregateDataTool,
            SortDataTool, PivotTableTool
        )
        
        tools = [
            ReadWorksheetTool(self.file_handler),
            FilterDataTool(self.file_handler),
            AggregateDataTool(self.file_handler),
            SortDataTool(self.file_handler),
            PivotTableTool(self.file_handler)
        ]
        
        return tools
    
    def load_file(self, file_path: str) -> Dict[str, Any]:
        """Load Excel file and set context"""
        try:
            self.current_file = file_path
            self.current_file_info = self.file_handler.get_file_info(file_path)
            
            # Set file path for tools
            for tool in self.tools:
                tool._current_file = file_path
            
            # Update agent's context
            context_message = self._build_file_context()
            self.memory.chat_memory.add_message(SystemMessage(content=context_message))
            
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

When the user asks about data analysis, use these tools to provide accurate results.
Always specify the sheet_name when using tools.
"""
        return context
    
    def query(self, user_query: str, sheet_name: Optional[str] = None) -> Dict[str, Any]:
        """Process natural language query"""
        try:
            if not self.current_file:
                return {"success": False, "error": "No file loaded. Please upload a file first."}
            
            # Enhance query with context
            enhanced_query = self._enhance_query(user_query, sheet_name)
            
            # Process with agent
            response = self.agent.run(enhanced_query)
            
            return {
                "success": True,
                "query": user_query,
                "response": response,
                "context": {
                    "file": self.current_file,
                    "available_sheets": self.current_file_info['sheet_names']
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {"success": False, "error": str(e)}
    
    def _enhance_query(self, query: str, sheet_name: Optional[str] = None) -> str:
        """Enhance user query with context and column mapping suggestions"""
        enhanced = f"User Query: {query}\n\n"
        
        if sheet_name:
            enhanced += f"Focus on sheet: {sheet_name}\n"
        elif len(self.current_file_info['sheet_names']) == 1:
            enhanced += f"Use sheet: {self.current_file_info['sheet_names'][0]}\n"
        else:
            enhanced += f"Available sheets: {', '.join(self.current_file_info['sheet_names'])}\n"
        
        # Add column mapping hints
        enhanced += """
IMPORTANT: 
- If the user mentions column names that don't exist, suggest similar columns
- For date queries, look for date/datetime columns
- For sales/revenue queries, look for amount/price/sales columns
- Always provide sample results to verify the operation worked correctly
"""
        
        return enhanced
    
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
            "Create pivot table for sales by month and product",
            "Sort data by date descending",
            "Show top 10 customers by revenue"
        ])
        
        return suggestions[:5]  # Return top 5 suggestions
