from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Union
import pandas as pd
import json
from datetime import datetime
import logging
from langchain_core.tools import StructuredTool

logger = logging.getLogger(__name__)

def handle_excel_load_error(e):
    msg = str(e).lower()
    if 'password' in msg or 'protected' in msg:
        return json.dumps({"success": False, "error": "This Excel file is password-protected. Please remove the password and upload again."})
    return json.dumps({"success": False, "error": "The uploaded file appears to be corrupted or unreadable. Please check the file and try again."})

# --- Structured Tool: Read Worksheet ---
class ReadWorksheetArgs(BaseModel):
    sheet_name: Optional[str] = Field(default="Sheet1", description="Name of the worksheet")
    nrows: Optional[int] = Field(default=1000, description="Number of rows to read")
    file_path: Optional[str] = Field(default=None, description="Path to the Excel file")

def read_worksheet(sheet_name: str = "Sheet1", nrows: int = 1000, file_path: Optional[str] = None) -> str:
    import os
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"read_worksheet called with: sheet_name={sheet_name}, nrows={nrows}, file_path={file_path}")
    if nrows is None:
        nrows = 1000
    if not file_path:
        return "No file loaded. Please upload a file first."
    file_path = os.path.normpath(file_path)
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
        logger.error(f"read_worksheet error: {e}")
        return handle_excel_load_error(e)

read_worksheet_tool = StructuredTool.from_function(
    func=read_worksheet,
    name="read_worksheet",
    description="Read data from an Excel worksheet.",
    args_schema=ReadWorksheetArgs
)

# --- Structured Tool: Filter Data ---
class FilterDataArgs(BaseModel):
    sheet_name: Optional[str] = Field(default="Sheet1", description="Name of the worksheet")
    column: Optional[str] = Field(default=None, description="Column to filter on")
    operator: Optional[str] = Field(default=None, description="Filter operator, e.g. >, <, ==, !=, contains")
    value: Optional[Any] = Field(default=None, description="Value to filter by")
    file_path: Optional[str] = Field(default=None, description="Path to the Excel file")

def filter_data(sheet_name: str = "Sheet1", column: str = None, operator: str = None, value: Any = None, file_path: Optional[str] = None) -> str:
    import os
    if not file_path:
        return "No file loaded. Please upload a file first."
    file_path = os.path.normpath(file_path)
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
        return handle_excel_load_error(e)

filter_data_tool = StructuredTool.from_function(
    func=filter_data,
    name="filter_data",
    description="Filter Excel data based on a column, operator, and value.",
    args_schema=FilterDataArgs
)

# --- Structured Tool: Aggregate Data ---
class AggregateDataArgs(BaseModel):
    sheet_name: Optional[str] = Field(default="Sheet1", description="Name of the worksheet")
    group_by: Optional[str] = Field(default=None, description="Column to group by (optional)")
    aggregate_column: Optional[str] = Field(default=None, description="Column to aggregate")
    function: Optional[str] = Field(default="sum", description="Aggregation function, e.g. sum, mean, count")
    file_path: Optional[str] = Field(default=None, description="Path to the Excel file")

def aggregate_data(sheet_name: str = "Sheet1", group_by: str = None, aggregate_column: str = None, function: str = "sum", file_path: Optional[str] = None) -> str:
    import os
    if not file_path:
        return "No file loaded. Please upload a file first."
    file_path = os.path.normpath(file_path)
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
        return handle_excel_load_error(e)

aggregate_data_tool = StructuredTool.from_function(
    func=aggregate_data,
    name="aggregate_data",
    description="Perform aggregation on Excel data by grouping and applying a function to a column.",
    args_schema=AggregateDataArgs
)

# --- Structured Tool: Sort Data ---
class SortDataArgs(BaseModel):
    sheet_name: Optional[str] = Field(default="Sheet1", description="Name of the worksheet")
    sort_column: Optional[str] = Field(default=None, description="Column to sort by")
    ascending: Optional[bool] = Field(default=True, description="Sort ascending (True) or descending (False)")
    file_path: Optional[str] = Field(default=None, description="Path to the Excel file")

def sort_data(sheet_name: str = "Sheet1", sort_column: str = None, ascending: bool = True, file_path: Optional[str] = None) -> str:
    import os
    if not file_path:
        return "No file loaded. Please upload a file first."
    file_path = os.path.normpath(file_path)
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
        return handle_excel_load_error(e)

sort_data_tool = StructuredTool.from_function(
    func=sort_data,
    name="sort_data",
    description="Sort Excel data by a column, ascending or descending.",
    args_schema=SortDataArgs
)

# --- Structured Tool: Pivot Table ---
class PivotTableArgs(BaseModel):
    sheet_name: Optional[str] = Field(default="Sheet1", description="Name of the worksheet")
    index: Optional[list[str]] = Field(default=None, description="List of columns to use as index (rows) in the pivot table")
    columns: Optional[list[str]] = Field(default=None, description="List of columns to use as columns in the pivot table")
    values: Optional[list[str]] = Field(default=None, description="List of columns to aggregate in the pivot table")
    aggfunc: Optional[str] = Field(default="sum", description="Aggregation function, e.g. sum, mean, count")
    file_path: Optional[str] = Field(default=None, description="Path to the Excel file")

def pivot_table(sheet_name: str = "Sheet1", index: list[str] = None, columns: list[str] = None, values: list[str] = None, aggfunc: str = "sum", file_path: Optional[str] = None) -> str:
    import os
    if not file_path:
        return "No file loaded. Please upload a file first."
    file_path = os.path.normpath(file_path)
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
        return handle_excel_load_error(e)

pivot_table_tool = StructuredTool.from_function(
    func=pivot_table,
    name="pivot_table",
    description="Create a pivot table from Excel data.",
    args_schema=PivotTableArgs
)

# --- Structured Tool: Merge Worksheets ---
from typing import List

class MergeWorksheetsArgs(BaseModel):
    sheet_names: Optional[List[str]] = Field(default=None, description="List of sheet names to merge (default: all)")
    mode: Optional[str] = Field(default="stack", description="Merge mode: 'stack' (vertical) or 'key' (horizontal join)")
    key: Optional[str] = Field(default=None, description="Column name to join on if mode is 'key'")
    how: Optional[str] = Field(default="outer", description="Type of join for key-based merge: 'outer', 'inner', 'left', or 'right'")
    file_path: Optional[str] = Field(default=None, description="Path to the Excel file")

def merge_worksheets(sheet_names: Optional[List[str]] = None, mode: str = "stack", key: Optional[str] = None, how: str = "outer", file_path: Optional[str] = None) -> str:
    import pandas as pd
    import json
    import os
    if not file_path:
        return "No file loaded."
    file_path = os.path.normpath(file_path)
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
        return handle_excel_load_error(e)

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
    sheet_name: Optional[str] = Field(default=None, description="Name of the worksheet to split")
    column: Optional[str] = Field(default=None, description="Column to split by (each unique value becomes a new sheet)")
    file_path: Optional[str] = Field(default=None, description="Path to the Excel file")

def split_worksheet(sheet_name: str, column: str, file_path: Optional[str] = None) -> str:
    import pandas as pd
    import os
    import json
    import os
    if not file_path:
        return "No file loaded."
    file_path = os.path.normpath(file_path)
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
        return handle_excel_load_error(e)

split_worksheet_tool = StructuredTool.from_function(
    func=split_worksheet,
    name="split_worksheet",
    description="Split a worksheet into multiple sheets/files based on unique values in a selected column. Each unique value becomes a new Excel file in the uploads/ directory.",
    args_schema=SplitWorksheetArgs
)

# --- Structured Tool: Data Validation ---
from pydantic import BaseModel, Field
from typing import Optional

class DataValidationArgs(BaseModel):
    sheet_name: Optional[str] = Field(default=None, description="Name of the worksheet to validate")
    file_path: Optional[str] = Field(default=None, description="Path to the Excel file")

def data_validation(sheet_name: str, file_path: Optional[str] = None) -> str:
    import pandas as pd
    import json
    import os
    if not file_path:
        return "No file loaded."
    file_path = os.path.normpath(file_path)
    try:
        xl = pd.ExcelFile(file_path)
        if sheet_name not in xl.sheet_names:
            return json.dumps({"success": False, "error": f"Sheet {sheet_name} not found."})
        df = xl.parse(sheet_name)
        result = {"success": True, "sheet": sheet_name, "issues": []}
        # Check if empty
        if df.empty:
            result["issues"].append({"type": "empty_sheet", "message": f"Sheet {sheet_name} is empty."})
            return json.dumps(result, indent=2)
        # Missing values per column
        missing = df.isnull().sum()
        missing_cols = {col: int(count) for col, count in missing.items() if count > 0}
        if missing_cols:
            result["issues"].append({"type": "missing_values", "columns": missing_cols})
        # Type mismatches (mixed types)
        mixed_type_cols = {}
        for col in df.columns:
            types = set(df[col].dropna().map(type))
            if len(types) > 1:
                mixed_type_cols[col] = [t.__name__ for t in types]
        if mixed_type_cols:
            result["issues"].append({"type": "mixed_types", "columns": mixed_type_cols})
        # Summary stats
        result["summary"] = {
            "rows": len(df),
            "columns": len(df.columns),
            "missing_values": sum(missing_cols.values()),
            "columns_with_missing": list(missing_cols.keys()),
            "columns_with_mixed_types": list(mixed_type_cols.keys())
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return handle_excel_load_error(e)

data_validation_tool = StructuredTool.from_function(
    func=data_validation,
    name="data_validation",
    description="Validate a worksheet for missing values, type mismatches, and empty sheets. Returns a summary of issues found.",
    args_schema=DataValidationArgs
)

class WriteResultsArgs(BaseModel):
    sheet_name: Optional[str] = Field(default=None, description="Name of the worksheet to save (if saving an existing sheet)")
    data: Optional[List[Dict[str, Any]]] = Field(default=None, description="Data to save (as list of dicts, e.g., from a previous operation)")
    output_file_name: Optional[str] = Field(default=None, description="Name for the output Excel file (default: auto-generated)")
    file_path: Optional[str] = Field(default=None, description="Path to the Excel file (required if using sheet_name)")

def write_results(sheet_name: Optional[str] = None, data: Optional[List[Dict[str, Any]]] = None, output_file_name: Optional[str] = None, file_path: Optional[str] = None) -> str:
    import pandas as pd
    import os
    import json
    import os
    if sheet_name and file_path:
        file_path = os.path.normpath(file_path)
    try:
        if sheet_name:
            if not file_path:
                return json.dumps({"success": False, "error": "file_path is required when saving a worksheet."})
            xl = pd.ExcelFile(file_path)
            if sheet_name not in xl.sheet_names:
                return json.dumps({"success": False, "error": f"Sheet {sheet_name} not found."})
            df = xl.parse(sheet_name)
        else:
            df = pd.DataFrame(data)
        # Determine output file name
        if not output_file_name:
            base = os.path.splitext(os.path.basename(file_path))[0] if file_path else "results"
            output_file_name = f"{base}_output_{sheet_name or 'data'}.xlsx"
        out_path = os.path.join("uploads", output_file_name)
        df.to_excel(out_path, index=False)
        result = {
            "success": True,
            "output_file": out_path,
            "rows": len(df),
            "columns": list(df.columns),
            "sample_data": df.head(10).to_dict('records')
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        return handle_excel_load_error(e)

write_results_tool = StructuredTool.from_function(
    func=write_results,
    name="write_results",
    description="Save a worksheet or provided data (list of dicts) to a new Excel file. Optionally specify output file name. Returns file path and sample data.",
    args_schema=WriteResultsArgs
)

class FormulaEvaluationArgs(BaseModel):
    sheet_name: Optional[str] = Field(default=None, description="Name of the worksheet to evaluate the formula on")
    formula: Optional[str] = Field(default=None, description="Formula to evaluate (e.g., 'Profit = Revenue - Cost' or 'Total = ColA * ColB / ColC')")
    new_column_name: Optional[str] = Field(default=None, description="Name for the new column (if not specified in formula)")
    file_path: Optional[str] = Field(default=None, description="Path to the Excel file")
    output_file_name: Optional[str] = Field(default=None, description="Name for the output Excel file (if saving result)")
    save_result: Optional[bool] = Field(default=False, description="Whether to save the updated sheet as a new file")

def formula_evaluation(sheet_name: str, formula: str, new_column_name: Optional[str] = None, file_path: Optional[str] = None, output_file_name: Optional[str] = None, save_result: bool = False) -> str:
    import pandas as pd
    import json
    import re
    import os
    if not file_path:
        return json.dumps({"success": False, "error": "No file loaded."})
    file_path = os.path.normpath(file_path)
    try:
        xl = pd.ExcelFile(file_path)
        if sheet_name not in xl.sheet_names:
            return json.dumps({"success": False, "error": f"Sheet {sheet_name} not found."})
        df = xl.parse(sheet_name)
        # Parse formula: try to extract new column name and expression
        col, expr = None, None
        match = re.match(r"\s*([\w\s]+)\s*=\s*(.+)", formula)
        if match:
            col, expr = match.group(1).strip(), match.group(2).strip()
        else:
            expr = formula.strip()
            col = new_column_name or "Result"
        # Evaluate the expression using pandas eval
        try:
            df[col] = df.eval(expr)
        except Exception:
            # Try with apply for more complex expressions
            try:
                df[col] = df.apply(lambda row: eval(expr, {}, row.to_dict()), axis=1)
            except Exception as e:
                return json.dumps({"success": False, "error": f"Formula evaluation failed: {str(e)}"})
        result = {
            "success": True,
            "new_column": col,
            "sample_data": df.head(10).to_dict('records')
        }
        if save_result:
            if not output_file_name:
                base = os.path.splitext(os.path.basename(file_path))[0]
                output_file_name = f"{base}_{sheet_name}_{col}_formula.xlsx"
            out_path = os.path.join("uploads", output_file_name)
            df.to_excel(out_path, index=False)
            result["output_file"] = out_path
        return json.dumps(result, indent=2)
    except Exception as e:
        return handle_excel_load_error(e)

formula_evaluation_tool = StructuredTool.from_function(
    func=formula_evaluation,
    name="formula_evaluation",
    description="Evaluate a formula on a worksheet (supports simple and complex pandas expressions). Optionally save the result as a new file if requested.",
    args_schema=FormulaEvaluationArgs
)

class ChartGenerationArgs(BaseModel):
    sheet_name: Optional[str] = Field(default=None, description="Name of the worksheet to generate the chart from")
    chart_type: Optional[str] = Field(default=None, description="Type of chart: 'bar', 'line', 'pie', 'scatter'")
    x_column: Optional[str] = Field(default=None, description="Column for x-axis (not needed for pie)")
    y_column: Optional[str] = Field(default=None, description="Column for y-axis (not needed for pie)")
    label_column: Optional[str] = Field(default=None, description="Column for labels (for pie chart)")
    title: Optional[str] = Field(default=None, description="Chart title")
    x_label: Optional[str] = Field(default=None, description="X-axis label")
    y_label: Optional[str] = Field(default=None, description="Y-axis label")
    file_path: Optional[str] = Field(default=None, description="Path to the Excel file")
    output_file_name: Optional[str] = Field(default=None, description="Name for the output image file (if saving)")
    save_chart: Optional[bool] = Field(default=False, description="Whether to save the chart as an image file")

def chart_generation(sheet_name: str, chart_type: str, x_column: Optional[str] = None, y_column: Optional[str] = None, label_column: Optional[str] = None, title: Optional[str] = None, x_label: Optional[str] = None, y_label: Optional[str] = None, file_path: Optional[str] = None, output_file_name: Optional[str] = None, save_chart: bool = False) -> str:
    import pandas as pd
    import matplotlib.pyplot as plt
    import os
    import json
    import io
    if not file_path:
        return json.dumps({"success": False, "error": "No file loaded."})
    file_path = os.path.normpath(file_path)
    try:
        xl = pd.ExcelFile(file_path)
        if sheet_name not in xl.sheet_names:
            return json.dumps({"success": False, "error": f"Sheet {sheet_name} not found."})
        df = xl.parse(sheet_name)
        plt.figure(figsize=(8, 5))
        img_bytes = None
        chart_type = chart_type.lower()
        if chart_type == 'bar':
            # Most defensive fallback for value counts
            if x_column and y_column and x_column == y_column:
                value_counts = df[x_column].value_counts()
                plt.bar(value_counts.index.astype(str), value_counts.values)
            elif x_column and not y_column:
                value_counts = df[x_column].value_counts()
                plt.bar(value_counts.index.astype(str), value_counts.values)
            elif x_column and y_column:
                if pd.api.types.is_numeric_dtype(df[y_column]):
                    plt.bar(df[x_column].astype(str), df[y_column])
                else:
                    value_counts = df[x_column].value_counts()
                    plt.bar(value_counts.index.astype(str), value_counts.values)
            else:
                return json.dumps({"success": False, "error": "x_column (and optionally y_column) are required for bar chart. If only x_column is provided, value counts will be plotted."})
        elif chart_type == 'line':
            if not x_column or not y_column:
                return json.dumps({"success": False, "error": "x_column and y_column are required for line chart."})
            plt.plot(df[x_column], df[y_column], marker='o')
        elif chart_type == 'scatter':
            if not x_column or not y_column:
                return json.dumps({"success": False, "error": "x_column and y_column are required for scatter chart."})
            plt.scatter(df[x_column], df[y_column])
        elif chart_type == 'pie':
            # Most robust fallback for value counts
            if label_column and y_column and label_column == y_column:
                value_counts = df[label_column].value_counts()
                plt.pie(value_counts.values, labels=value_counts.index, autopct='%1.1f%%')
            elif label_column and not y_column:
                value_counts = df[label_column].value_counts()
                plt.pie(value_counts.values, labels=value_counts.index, autopct='%1.1f%%')
            elif label_column and y_column:
                if pd.api.types.is_numeric_dtype(df[y_column]):
                    plt.pie(df[y_column], labels=df[label_column], autopct='%1.1f%%')
                else:
                    value_counts = df[label_column].value_counts()
                    plt.pie(value_counts.values, labels=value_counts.index, autopct='%1.1f%%')
            else:
                return json.dumps({"success": False, "error": "label_column (and optionally y_column) are required for pie chart. If only label_column is provided, value counts will be plotted."})
        else:
            return json.dumps({"success": False, "error": f"Unsupported chart type: {chart_type}"})
        if title:
            plt.title(title)
        if x_label:
            plt.xlabel(x_label)
        if y_label:
            plt.ylabel(y_label)
        plt.tight_layout()
        result = {"success": True}
        if save_chart:
            if not output_file_name:
                base = os.path.splitext(os.path.basename(file_path))[0]
                output_file_name = f"{base}_{sheet_name}_{chart_type}_chart.png"
            out_path = os.path.join("uploads", output_file_name)
            plt.savefig(out_path)
            result["output_file"] = out_path
        # Always return a preview as bytes (base64)
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        import base64
        img_bytes = base64.b64encode(buf.read()).decode('utf-8')
        result["preview_base64"] = img_bytes
        plt.close()
        return json.dumps(result, indent=2)
    except Exception as e:
        return handle_excel_load_error(e)

chart_generation_tool = StructuredTool.from_function(
    func=chart_generation,
    name="chart_generation",
    description="Generate a chart (bar, line, pie, scatter) from worksheet data. Supports custom titles/labels and optional image saving. Returns a preview and file path if saved.",
    args_schema=ChartGenerationArgs
)

class EchoArgs(BaseModel):
    message: Optional[str] = Field(default=None, description="Message to echo back.")

def echo(message: Optional[str] = None) -> str:
    return json.dumps({"success": True, "echo": message})

echo_tool = StructuredTool.from_function(
    func=echo,
    name="echo",
    description="Echoes back the provided message.",
    args_schema=EchoArgs
)