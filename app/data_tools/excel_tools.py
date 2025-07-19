from langchain.tools import BaseTool
from langchain.pydantic_v1 import BaseModel, Field
from typing import Dict, List, Any, Optional, Union
import pandas as pd
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ExcelToolInput(BaseModel):
    """Input schema for Excel tools"""
    sheet_name: str = Field(description="Name of the Excel worksheet")
    operation: str = Field(description="Operation to perform")
    parameters: Dict[str, Any] = Field(default={}, description="Operation parameters")

class ReadWorksheetTool(BaseTool):
    name: str = "read_worksheet"
    description: str = """
    Read data from an Excel worksheet. 
    Input: sheet_name (string), parameters (dict with optional: nrows, skiprows, columns)
    Returns: DataFrame info and sample data
    """
    
    def __init__(self, file_handler):
        super().__init__()
        self.file_handler = file_handler
    
    def _run(self, sheet_name: str, parameters: Dict[str, Any]| None = None) -> str:
        try:
            if not hasattr(self, '_current_file'):
                return "No file currently loaded. Please upload a file first."
            
            params = parameters or {}
            nrows = params.get('nrows', 1000)
            
            # Read the worksheet
            df = pd.read_excel(self._current_file, sheet_name=sheet_name, nrows=nrows)
            
            result = {
                "success": True,
                "sheet_name": sheet_name,
                "shape": df.shape,
                "columns": list(df.columns),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "sample_data": df.head(5).to_dict('records'),
                "null_counts": df.isnull().sum().to_dict(),
                "memory_usage": f"{df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB"
            }
            
            return json.dumps(result, indent=2, default=str)
            
        except Exception as e:
            logger.error(f"Error reading worksheet: {e}")
            return json.dumps({"success": False, "error": str(e)})
    
    def _arun(self, sheet_name: str, parameters: Dict[str, Any]|None = None):
        raise NotImplementedError("Async not implemented")

class FilterDataTool(BaseTool):
    name: str = "filter_data"
    description: str = """
    Filter Excel data based on conditions.
    Input: sheet_name (string), parameters (dict with: conditions, columns)
    conditions format: [{"column": "sales", "operator": ">", "value": 1000}]
    Returns: Filtered data summary
    """
    
    def __init__(self, file_handler):
        super().__init__()
        self.file_handler = file_handler
    
    def _run(self, sheet_name: str, parameters: Dict[str, Any]|None = None) -> str:
        try:
            if not hasattr(self, '_current_file'):
                return "No file currently loaded."
            
            params = parameters or {}
            conditions = params.get('conditions', [])
            columns = params.get('columns', None)
            
            # Read data
            df = pd.read_excel(self._current_file, sheet_name=sheet_name)
            original_shape = df.shape
            
            # Apply filters
            for condition in conditions:
                col = condition['column']
                operator = condition['operator']
                value = condition['value']
                
                # Handle different operators
                if operator == '>':
                    df = df[df[col] > value]
                elif operator == '<':
                    df = df[df[col] < value]
                elif operator == '>=':
                    df = df[df[col] >= value]
                elif operator == '<=':
                    df = df[df[col] <= value]
                elif operator == '==':
                    df = df[df[col] == value]
                elif operator == '!=':
                    df = df[df[col] != value]
                elif operator == 'contains':
                    df = df[df[col].str.contains(str(value), na=False)]
                elif operator == 'in':
                    df = df[df[col].isin(value if isinstance(value, list) else [value])]
            
            # Select columns if specified
            if columns:
                df = df[columns]
            
            result = {
                "success": True,
                "original_shape": original_shape,
                "filtered_shape": df.shape,
                "conditions_applied": conditions,
                "sample_results": df.head(10).to_dict('records'),
                "summary_stats": df.describe().to_dict() if df.select_dtypes(include='number').shape[1] > 0 else {}
            }
            
            return json.dumps(result, indent=2, default=str)
            
        except Exception as e:
            logger.error(f"Error filtering data: {e}")
            return json.dumps({"success": False, "error": str(e)})
    
    def _arun(self, sheet_name: str, parameters: Dict[str, Any]|None = None):
        raise NotImplementedError("Async not implemented")

class AggregateDataTool(BaseTool):
    name: str = "aggregate_data"
    description: str = """
    Perform aggregations on Excel data.
    Input: sheet_name (string), parameters (dict with: group_by, aggregations, filters)
    aggregations format: {"column": "sales", "functions": ["sum", "mean", "count"]}
    Returns: Aggregated results
    """
    
    def __init__(self, file_handler):
        super().__init__()
        self.file_handler = file_handler
    
    def _run(self, sheet_name: str, parameters: Dict[str, Any] |None= None) -> str:
        try:
            if not hasattr(self, '_current_file'):
                return "No file currently loaded."
            
            params = parameters or {}
            group_by = params.get('group_by', [])
            aggregations = params.get('aggregations', {})
            
            # Read data
            df = pd.read_excel(self._current_file, sheet_name=sheet_name)
            
            if group_by:
                # Group by aggregation
                grouped = df.groupby(group_by)
                agg_dict = {}
                
                for col, functions in aggregations.items():
                    if isinstance(functions, str):
                        functions = [functions]
                    for func in functions:
                        agg_dict[f"{col}_{func}"] = (col, func)
                
                result_df = grouped.agg(agg_dict).round(2)
                result_df.columns = [col for col in result_df.columns]
                result_df = result_df.reset_index()
            else:
                # Simple aggregation
                agg_results = {}
                for col, functions in aggregations.items():
                    if isinstance(functions, str):
                        functions = [functions]
                    for func in functions:
                        agg_results[f"{col}_{func}"] = getattr(df[col], func)()
                
                result_df = pd.DataFrame([agg_results])
            
            result = {
                "success": True,
                "aggregation_summary": {
                    "group_by": group_by,
                    "aggregations": aggregations,
                    "result_shape": result_df.shape
                },
                "results": result_df.to_dict('records')
            }
            
            return json.dumps(result, indent=2, default=str)
            
        except Exception as e:
            logger.error(f"Error aggregating data: {e}")
            return json.dumps({"success": False, "error": str(e)})
    
    def _arun(self, sheet_name: str, parameters: Dict[str, Any]|None = None):
        raise NotImplementedError("Async not implemented")

class SortDataTool(BaseTool):
    name: str = "sort_data"
    description: str = """
    Sort Excel data by one or more columns.
    Input: sheet_name (string), parameters (dict with: sort_by, ascending)
    sort_by format: [{"column": "date", "ascending": False}, {"column": "sales", "ascending": True}]
    Returns: Sorted data summary
    """
    
    def __init__(self, file_handler):
        super().__init__()
        self.file_handler = file_handler
    
    def _run(self, sheet_name: str, parameters: Dict[str, Any] |None= None) -> str:
        try:
            if not hasattr(self, '_current_file'):
                return "No file currently loaded."
            
            params = parameters or {}
            sort_by = params.get('sort_by', [])
            
            # Read data
            df = pd.read_excel(self._current_file, sheet_name=sheet_name)
            
            if sort_by:
                columns = [item['column'] for item in sort_by]
                ascending = [item.get('ascending', True) for item in sort_by]
                
                df_sorted = df.sort_values(by=columns, ascending=ascending)
            else:
                df_sorted = df
            
            result = {
                "success": True,
                "sort_criteria": sort_by,
                "shape": df_sorted.shape,
                "sample_data": df_sorted.head(10).to_dict('records')
            }
            
            return json.dumps(result, indent=2, default=str)
            
        except Exception as e:
            logger.error(f"Error sorting data: {e}")
            return json.dumps({"success": False, "error": str(e)})
    
    def _arun(self, sheet_name: str, parameters: Dict[str, Any]|None = None):
        raise NotImplementedError("Async not implemented")

class PivotTableTool(BaseTool):
    name: str = "pivot_table"
    description: str = """
    Create pivot tables from Excel data.
    Input: sheet_name (string), parameters (dict with: index, columns, values, aggfunc)
    Returns: Pivot table results
    """
    
    def __init__(self, file_handler):
        super().__init__()
        self.file_handler = file_handler
    
    def _run(self, sheet_name: str, parameters: Dict[str, Any] |None= None) -> str:
        try:
            if not hasattr(self, '_current_file'):
                return "No file currently loaded."
            
            params = parameters or {}
            index = params.get('index', [])
            columns = params.get('columns', [])
            values = params.get('values', [])
            aggfunc = params.get('aggfunc', 'sum')
            
            # Read data
            df = pd.read_excel(self._current_file, sheet_name=sheet_name)
            
            # Create pivot table
            pivot = pd.pivot_table(
                df, 
                index=index if index else None,
                columns=columns if columns else None,
                values=values if values else None,
                aggfunc=aggfunc,
                fill_value=0
            )
            
            # Convert to regular dataframe for serialization
            pivot_df = pivot.reset_index()
            
            result = {
                "success": True,
                "pivot_config": {
                    "index": index,
                    "columns": columns,
                    "values": values,
                    "aggfunc": aggfunc
                },
                "shape": pivot_df.shape,
                "results": pivot_df.to_dict('records')
            }
            
            return json.dumps(result, indent=2, default=str)
            
        except Exception as e:
            logger.error(f"Error creating pivot table: {e}")
            return json.dumps({"success": False, "error": str(e)})
    
    def _arun(self, sheet_name: str, parameters: Dict[str, Any]|None = None):
        raise NotImplementedError("Async not implemented")