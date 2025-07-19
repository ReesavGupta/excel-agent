from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher
import re

class ColumnMapper:
    """Handles column name variations and mapping"""
    
    def __init__(self):
        self.synonym_dict = {
            'quantity': ['qty', 'amount', 'count', 'num', 'number'],
            'price': ['cost', 'rate', 'amount', 'value', 'price_per_unit'],
            'date': ['datetime', 'timestamp', 'created_at', 'updated_at'],
            'customer': ['client', 'buyer', 'purchaser', 'customer_name'],
            'product': ['item', 'goods', 'merchandise', 'product_name'],
            'sales': ['revenue', 'income', 'earnings', 'total_sales'],
            'region': ['area', 'location', 'territory', 'zone'],
            'category': ['type', 'class', 'group', 'segment'],
        }
    
    def normalize_column_name(self, col_name: str) -> str:
        """Normalize column name for comparison"""
        # Convert to lowercase, remove special chars, replace spaces with underscores
        normalized = re.sub(r'[^a-zA-Z0-9\s]', '', str(col_name).lower())
        normalized = re.sub(r'\s+', '_', normalized.strip())
        return normalized
    
    def find_similar_columns(self, target: str, available_columns: List[str], 
                           threshold: float = 0.6) -> List[Tuple[str, float]]:
        """Find columns similar to target using fuzzy matching"""
        target_norm = self.normalize_column_name(target)
        matches = []
        
        for col in available_columns:
            col_norm = self.normalize_column_name(col)
            
            # Exact match
            if target_norm == col_norm:
                matches.append((col, 1.0))
                continue
            
            # Fuzzy match
            similarity = SequenceMatcher(None, target_norm, col_norm).ratio()
            if similarity >= threshold:
                matches.append((col, similarity))
            
            # Synonym match
            for concept, synonyms in self.synonym_dict.items():
                if target_norm in synonyms or target_norm == concept:
                    if col_norm in synonyms or col_norm == concept:
                        matches.append((col, 0.9))
                        break
        
        # Sort by similarity score
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches
    
    def suggest_column_mapping(self, query_columns: List[str], 
                             available_columns: List[str]) -> Dict[str, List[str]]:
        """Suggest mappings for query columns to available columns"""
        mappings = {}
        
        for query_col in query_columns:
            similar = self.find_similar_columns(query_col, available_columns)
            if similar:
                mappings[query_col] = [match[0] for match in similar[:3]]  # Top 3 matches
        
        return mappings