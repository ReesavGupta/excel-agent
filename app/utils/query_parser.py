import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

class QueryParser:
    """Parse natural language queries into structured operations"""
    
    def __init__(self, column_mapper):
        self.column_mapper = column_mapper
        
        # Query patterns
        self.patterns = {
            'filter': [
                r'show.*where\s+(\w+)\s*([><=!]+)\s*(\w+)',
                r'filter.*(\w+)\s*([><=!]+)\s*(\w+)',
                r'(\w+)\s*(greater|less|equal)\s*than\s*(\w+)'
            ],
            'aggregate': [
                r'total\s+(\w+)\s+by\s+(\w+)',
                r'sum\s+of\s+(\w+)\s+by\s+(\w+)',
                r'average\s+(\w+)\s+by\s+(\w+)'
            ],
            'sort': [
                r'sort\s+by\s+(\w+)\s*(desc|asc|descending|ascending)?',
                r'order\s+by\s+(\w+)\s*(desc|asc|descending|ascending)?'
            ],
            'pivot': [
                r'pivot.*(\w+)\s+by\s+(\w+)\s+and\s+(\w+)',
                r'create.*pivot.*table'
            ]
        }
    
    def parse_query(self, query: str, available_columns: List[str]) -> Dict[str, Any]:
        """Parse natural language query into structured format"""
        query_lower = query.lower()
        
        # Detect operation type
        operation = self._detect_operation(query_lower)
        
        # Extract parameters based on operation
        if operation == 'filter':
            return self._parse_filter_query(query_lower, available_columns)
        elif operation == 'aggregate':
            return self._parse_aggregate_query(query_lower, available_columns)
        elif operation == 'sort':
            return self._parse_sort_query(query_lower, available_columns)
        elif operation == 'pivot':
            return self._parse_pivot_query(query_lower, available_columns)
        else:
            return self._parse_general_query(query_lower, available_columns)
    
    def _detect_operation(self, query: str) -> str:
        """Detect the type of operation from query"""
        if any(word in query for word in ['filter', 'where', 'show']):
            return 'filter'
        elif any(word in query for word in ['total', 'sum', 'average', 'count', 'by']):
            return 'aggregate'
        elif any(word in query for word in ['sort', 'order']):
            return 'sort'
        elif any(word in query for word in ['pivot', 'table']):
            return 'pivot'
        else:
            return 'general'
    
    def _parse_filter_query(self, query: str, columns: List[str]) -> Dict[str, Any]:
        """Parse filter queries"""
        conditions = []
        
        # Extract conditions using regex
        operators = {
            '>': '>', '<': '<', '>=': '>=', '<=': '<=', 
            '=': '==', '!=': '!=', 'equal': '==',
            'greater than': '>', 'less than': '<'
        }
        
        # Simple pattern matching
        for pattern in self.patterns['filter']:
            match = re.search(pattern, query)
            if match:
                column = match.group(1)
                operator = match.group(2)
                value = match.group(3)
                
                # Map column name
                mapped_cols = self.column_mapper.find_similar_columns(column, columns)
                if mapped_cols:
                    actual_column = mapped_cols[0][0]
                    
                    # Try to convert value to appropriate type
                    try:
                        if value.isdigit():
                            value = int(value)
                        else:
                            value = float(value)
                    except:
                        pass  # Keep as string
                    
                    conditions.append({
                        'column': actual_column,
                        'operator': operators.get(operator, operator),
                        'value': value
                    })
        
        return {
            'operation': 'filter_data',
            'parameters': {'conditions': conditions}
        }
    
    def _parse_aggregate_query(self, query: str, columns: List[str]) -> Dict[str, Any]:
        """Parse aggregation queries"""
        group_by = []
        aggregations = {}
        
        # Extract aggregation type and columns
        if 'total' in query or 'sum' in query:
            func = 'sum'
        elif 'average' in query or 'mean' in query:
            func = 'mean'
        elif 'count' in query:
            func = 'count'
        else:
            func = 'sum'
        
        # Extract column names
        words = query.split()
        for i, word in enumerate(words):
            if word == 'by' and i + 1 < len(words):
                group_col = words[i + 1]
                mapped_cols = self.column_mapper.find_similar_columns(group_col, columns)
                if mapped_cols:
                    group_by.append(mapped_cols[0][0])
        
        # Find value column (typically numeric columns)
        numeric_indicators = ['sales', 'revenue', 'amount', 'price', 'total', 'value']
        for indicator in numeric_indicators:
            if indicator in query:
                mapped_cols = self.column_mapper.find_similar_columns(indicator, columns)
                if mapped_cols:
                    aggregations[mapped_cols[0][0]] = [func]
                    break
        
        return {
            'operation': 'aggregate_data',
            'parameters': {
                'group_by': group_by,
                'aggregations': aggregations
            }
        }
    
    def _parse_sort_query(self, query: str, columns: List[str]) -> Dict[str, Any]:
        """Parse sort queries"""
        sort_by = []
        
        # Extract sort column and direction
        words = query.split()
        ascending = True
        
        if any(word in query for word in ['desc', 'descending']):
            ascending = False
        
        for i, word in enumerate(words):
            if word in ['by', 'sort', 'order'] and i + 1 < len(words):
                col_word = words[i + 1]
                mapped_cols = self.column_mapper.find_similar_columns(col_word, columns)
                if mapped_cols:
                    sort_by.append({
                        'column': mapped_cols[0][0],
                        'ascending': ascending
                    })
        
        return {
            'operation': 'sort_data',
            'parameters': {'sort_by': sort_by}
        }
    
    def _parse_pivot_query(self, query: str, columns: List[str]) -> Dict[str, Any]:
        """Parse pivot table queries"""
        # This is a simplified version - in production, you'd want more sophisticated parsing
        return {
            'operation': 'pivot_table',
            'parameters': {
                'index': [],
                'columns': [],
                'values': [],
                'aggfunc': 'sum'
            }
        }
    
    def _parse_general_query(self, query: str, columns: List[str]) -> Dict[str, Any]:
        """Parse general queries"""
        return {
            'operation': 'read_worksheet',
            'parameters': {'nrows': 100}
        }