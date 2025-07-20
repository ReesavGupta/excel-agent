from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Union
import pandas as pd
import json
from datetime import datetime
import logging
from langchain_core.tools import StructuredTool

logger = logging.getLogger(__name__)

# --- Structured Tool: Read Worksheet ---
class ReadWorksheetArgs(BaseModel):
    sheet_name: str = Field(default="Sheet1", description="Name of the worksheet")
    nrows: int = Field(default=1000, description="Number of rows to read")
    file_path: Optional[str] = Field(default=None, description="Path to the Excel file")

def read_worksheet(sheet_name: str = "Sheet1", nrows: int = 1000, file_path: Optional[str] = None) -> str:
    if not file_path:
        return "No file loaded. Please upload a file first."
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=nrows)
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
        return json.dumps({"success": False, "error": str(e)})

read_worksheet_tool = StructuredTool.from_function(
    func=read_worksheet,
    name="read_worksheet",
    description="Read data from an Excel worksheet.",
    args_schema=ReadWorksheetArgs
)

# --- Structured Tool: Filter Data ---
class FilterDataArgs(BaseModel):
    sheet_name: str = Field(default="Sheet1", description="Name of the worksheet")
    column: str = Field(..., description="Column to filter on")
    operator: str = Field(..., description="Filter operator, e.g. >, <, ==, !=, contains")
    value: Any = Field(..., description="Value to filter by")
    file_path: Optional[str] = Field(default=None, description="Path to the Excel file")

def filter_data(sheet_name: str = "Sheet1", column: str = None, operator: str = None, value: Any = None, file_path: Optional[str] = None) -> str:
    if not file_path:
        return "No file loaded. Please upload a file first."
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        # Convert the column to numeric if possible, drop NaNs
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors='coerce')
            df = df.dropna(subset=[column])
            # Try to convert value to float if column is numeric
            if pd.api.types.is_numeric_dtype(df[column]):
                try:
                    value = float(value)
                except Exception:
                    pass  # If conversion fails, keep as is
        original_shape = df.shape
        if column and operator and value is not None:
            if operator == '>':
                df = df[df[column] > value]
            elif operator == '<':
                df = df[df[column] < value]
            elif operator == '>=':
                df = df[df[column] >= value]
            elif operator == '<=':
                df = df[df[column] <= value]
            elif operator == '==':
                df = df[df[column] == value]
            elif operator == '!=':
                df = df[df[column] != value]
            elif operator == 'contains':
                df = df[df[column].astype(str).str.contains(str(value), na=False)]
        result = {
            "success": True,
            "original_shape": original_shape,
            "filtered_shape": df.shape,
            "filter_applied": f"{column} {operator} {value}" if column else "No filter",
            "sample_results": df.head(10).to_dict('records'),
            "summary_stats": df.describe().to_dict() if df.select_dtypes(include='number').shape[1] > 0 else {}
        }
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

filter_data_tool = StructuredTool.from_function(
    func=filter_data,
    name="filter_data",
    description="Filter Excel data based on a column, operator, and value.",
    args_schema=FilterDataArgs
)

# --- Structured Tool: Aggregate Data ---
class AggregateDataArgs(BaseModel):
    sheet_name: str = Field(default="Sheet1", description="Name of the worksheet")
    group_by: Optional[str] = Field(default=None, description="Column to group by (optional)")
    aggregate_column: str = Field(..., description="Column to aggregate")
    function: str = Field(default="sum", description="Aggregation function, e.g. sum, mean, count")
    file_path: Optional[str] = Field(default=None, description="Path to the Excel file")

def aggregate_data(sheet_name: str = "Sheet1", group_by: str = None, aggregate_column: str = None, function: str = "sum", file_path: Optional[str] = None) -> str:
    if not file_path:
        return "No file loaded. Please upload a file first."
    try:
        # Map synonyms to pandas functions
        function_map = {
            "average": "mean",
            "avg": "mean"
        }
        pandas_func = function_map.get(function.lower(), function)
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        if group_by and aggregate_column:
            grouped = df.groupby(group_by)
            agg_dict = {f"{aggregate_column}_{pandas_func}": (aggregate_column, pandas_func)}
            result_df = grouped.agg(agg_dict).round(2)
            result_df = result_df.reset_index()
        elif aggregate_column:
            # No group_by: aggregate the whole column
            result_df = pd.DataFrame([{f"{aggregate_column}_{pandas_func}": getattr(df[aggregate_column], pandas_func)()}])
        else:
            return "Please specify aggregate_column for aggregation."
        result = {
            "success": True,
            "aggregation_summary": {
                "group_by": group_by,
                "aggregate_column": aggregate_column,
                "function": pandas_func,
                "result_shape": result_df.shape
            },
            "results": result_df.to_dict('records')
        }
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

aggregate_data_tool = StructuredTool.from_function(
    func=aggregate_data,
    name="aggregate_data",
    description="Perform aggregation on Excel data by grouping and applying a function to a column.",
    args_schema=AggregateDataArgs
)

# --- Structured Tool: Sort Data ---
class SortDataArgs(BaseModel):
    sheet_name: str = Field(default="Sheet1", description="Name of the worksheet")
    sort_column: str = Field(..., description="Column to sort by")
    ascending: bool = Field(default=True, description="Sort ascending (True) or descending (False)")
    file_path: Optional[str] = Field(default=None, description="Path to the Excel file")

def sort_data(sheet_name: str = "Sheet1", sort_column: str = None, ascending: bool = True, file_path: Optional[str] = None) -> str:
    if not file_path:
        return "No file loaded. Please upload a file first."
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        # Convert the sort column to numeric if possible, drop NaNs
        if sort_column in df.columns:
            df[sort_column] = pd.to_numeric(df[sort_column], errors='coerce')
            df = df.dropna(subset=[sort_column])
        if sort_column:
            df_sorted = df.sort_values(by=sort_column, ascending=ascending)
        else:
            df_sorted = df
        result = {
            "success": True,
            "sort_criteria": f"{sort_column} {'ascending' if ascending else 'descending'}" if sort_column else "No sorting",
            "shape": df_sorted.shape,
            "sample_data": df_sorted.head(10).to_dict('records')
        }
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

sort_data_tool = StructuredTool.from_function(
    func=sort_data,
    name="sort_data",
    description="Sort Excel data by a column, ascending or descending.",
    args_schema=SortDataArgs
)

# --- Structured Tool: Pivot Table ---
class PivotTableArgs(BaseModel):
    sheet_name: str = Field(default="Sheet1", description="Name of the worksheet")
    index: list[str] = Field(..., description="List of columns to use as index (rows) in the pivot table")
    columns: list[str] = Field(..., description="List of columns to use as columns in the pivot table")
    values: list[str] = Field(..., description="List of columns to aggregate in the pivot table")
    aggfunc: str = Field(default="sum", description="Aggregation function, e.g. sum, mean, count")
    file_path: Optional[str] = Field(default=None, description="Path to the Excel file")

def pivot_table(sheet_name: str = "Sheet1", index: list[str] = None, columns: list[str] = None, values: list[str] = None, aggfunc: str = "sum", file_path: Optional[str] = None) -> str:
    if not file_path:
        return "No file loaded. Please upload a file first."
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        pivot = pd.pivot_table(
            df,
            index=index if index else None,
            columns=columns if columns else None,
            values=values if values else None,
            aggfunc=aggfunc,
            fill_value=0
        )
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
        return json.dumps({"success": False, "error": str(e)})

pivot_table_tool = StructuredTool.from_function(
    func=pivot_table,
    name="pivot_table",
    description="Create a pivot table from Excel data.",
    args_schema=PivotTableArgs
)

# --- Structured Tool: Merge Worksheets ---
from typing import List

class MergeWorksheetsArgs(BaseModel):
    sheet_names: Optional[List[str]] = Field(None, description="List of sheet names to merge (default: all)")
    mode: str = Field("stack", description="Merge mode: 'stack' (vertical) or 'key' (horizontal join)")
    key: Optional[str] = Field(None, description="Column name to join on if mode is 'key'")
    how: str = Field("outer", description="Type of join for key-based merge: 'outer', 'inner', 'left', or 'right'")
    file_path: Optional[str] = Field(None, description="Path to the Excel file")

def merge_worksheets(sheet_names: Optional[List[str]] = None, mode: str = "stack", key: Optional[str] = None, how: str = "outer", file_path: Optional[str] = None) -> str:
    import pandas as pd
    import json
    if not file_path:
        return "No file loaded."
    try:
        xl = pd.ExcelFile(file_path)
        sheets = sheet_names or xl.sheet_names
        dfs = [xl.parse(sheet) for sheet in sheets]
        if mode == "stack":
            merged = pd.concat(dfs, ignore_index=True)
        elif mode == "key" and key:
            merged = dfs[0]
            for df in dfs[1:]:
                merged = pd.merge(merged, df, on=key, how=how)
        else:
            return json.dumps({"success": False, "error": "Invalid mode or missing key for key-based merge."})
        merged = merged.reset_index(drop=True)
        for col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors='coerce')
            if merged[col].dtype == 'object':
                merged[col] = merged[col].astype(str)
        merged = merged.dropna(how='all')
        result = {
            "success": True,
            "mode": mode,
            "how": how,
            "sheets": sheets,
            "shape": merged.shape,
            "sample_data": merged.head(10).to_dict('records')
        }
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

merge_worksheets_tool = StructuredTool.from_function(
    func=merge_worksheets,
    name="merge_worksheets",
    description="Merge multiple worksheets by stacking rows or joining on a key column. For key-based merges, you can specify the join type: 'outer', 'inner', 'left', or 'right'.",
    args_schema=MergeWorksheetsArgs
)

# --- Structured Tool: Split Worksheet ---
from pydantic import BaseModel, Field
from typing import Optional, List

class SplitWorksheetArgs(BaseModel):
    sheet_name: str = Field(..., description="Name of the worksheet to split")
    column: str = Field(..., description="Column to split by (each unique value becomes a new sheet)")
    file_path: Optional[str] = Field(None, description="Path to the Excel file")

def split_worksheet(sheet_name: str, column: str, file_path: Optional[str] = None) -> str:
    import pandas as pd
    import os
    import json
    if not file_path:
        return "No file loaded."
    try:
        xl = pd.ExcelFile(file_path)
        if sheet_name not in xl.sheet_names:
            return json.dumps({"success": False, "error": f"Sheet {sheet_name} not found."})
        df = xl.parse(sheet_name)
        if column not in df.columns:
            return json.dumps({"success": False, "error": f"Column {column} not found in {sheet_name}."})
        unique_values = df[column].dropna().unique()
        split_files = []
        summary = []
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        for val in unique_values:
            sub_df = df[df[column] == val]
            out_path = os.path.join("uploads", f"{base_name}_{sheet_name}_{str(val)}.xlsx")
            sub_df.to_excel(out_path, index=False)
            split_files.append(out_path)
            summary.append({
                "value": str(val),
                "rows": len(sub_df),
                "file": out_path,
                "sample_data": sub_df.head(5).to_dict('records')
            })
        result = {
            "success": True,
            "sheet": sheet_name,
            "column": column,
            "unique_values": [str(v) for v in unique_values],
            "split_files": split_files,
            "summary": summary
        }
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

split_worksheet_tool = StructuredTool.from_function(
    func=split_worksheet,
    name="split_worksheet",
    description="Split a worksheet into multiple sheets/files based on unique values in a selected column. Each unique value becomes a new Excel file in the uploads/ directory.",
    args_schema=SplitWorksheetArgs
)