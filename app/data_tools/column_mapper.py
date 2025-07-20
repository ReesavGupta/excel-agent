from typing import Dict, List, Tuple, Optional
from rapidfuzz import fuzz, process
import re
import unicodedata

class ColumnMapper:
    """Handles column name variations and mapping, with robust fuzzy, synonym, and LLM-assisted support"""
    
    def __init__(self):
        self.synonym_dict = {
            'quantity': ['qty', 'amount', 'count', 'num', 'number', 'quantité', 'quantidad', 'quantita'],
            'price': ['cost', 'rate', 'amount', 'value', 'price_per_unit', 'prix', 'precio', 'prezzo'],
            'date': ['datetime', 'timestamp', 'created_at', 'updated_at', 'fecha', 'data', 'date'],
            'customer': ['client', 'buyer', 'purchaser', 'customer_name', 'cliente', 'acheteur'],
            'product': ['item', 'goods', 'merchandise', 'product_name', 'producto', 'prodotto', 'article'],
            'sales': ['revenue', 'income', 'earnings', 'total_sales', 'ventes', 'ventas', 'ricavi'],
            'region': ['area', 'location', 'territory', 'zone', 'région', 'región', 'regione'],
            'category': ['type', 'class', 'group', 'segment', 'catégorie', 'categoría', 'categoria'],
        }
    
    def normalize_column_name(self, col_name: str) -> str:
        """Normalize column name for comparison (lowercase, remove accents, special chars, spaces)"""
        col_name = str(col_name).lower()
        col_name = unicodedata.normalize('NFKD', col_name)
        col_name = ''.join([c for c in col_name if not unicodedata.combining(c)])
        col_name = re.sub(r'[^a-z0-9\s]', '', col_name)
        col_name = re.sub(r'\s+', '_', col_name.strip())
        return col_name
    
    def find_similar_columns(self, target: str, available_columns: List[str], 
                           threshold: float = 70) -> List[Tuple[str, float, str]]:
        """Find columns similar to target using robust fuzzy, synonym, and normalization"""
        target_norm = self.normalize_column_name(target)
        matches = []
        # Fuzzy match using rapidfuzz
        for col in available_columns:
            col_norm = self.normalize_column_name(col)
            # Exact match
            if target_norm == col_norm:
                matches.append((col, 100.0, 'exact'))
                continue
            # Fuzzy match
            score = fuzz.ratio(target_norm, col_norm)
            if score >= threshold:
                matches.append((col, score, 'fuzzy'))
            # Synonym match
            for concept, synonyms in self.synonym_dict.items():
                if target_norm in synonyms or target_norm == concept:
                    if col_norm in synonyms or col_norm == concept:
                        matches.append((col, 90.0, 'synonym'))
                        break
        # Sort by score
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches
    
    def suggest_column_mapping(self, query_columns: List[str], 
                             available_columns: List[str]) -> Dict[str, List[str]]:
        """Suggest mappings for query columns to available columns (top 3)"""
        mappings = {}
        for query_col in query_columns:
            similar = self.find_similar_columns(query_col, available_columns)
            if similar:
                mappings[query_col] = [match[0] for match in similar[:3]]
        return mappings

    def best_column_match(self, query_col: str, available_columns: List[str]) -> Tuple[Optional[str], str, float]:
        """Return best match, reason, and score for a single query column"""
        matches = self.find_similar_columns(query_col, available_columns)
        if matches:
            best = matches[0]
            return best[0], best[2], best[1]
        return None, 'none', 0.0

    def llm_prompt_for_mapping(self, query_col: str, available_columns: List[str]) -> str:
        """Generate a prompt for the LLM to suggest a column mapping if confidence is low"""
        prompt = (
            f"The user referred to a column as '{query_col}'. "
            f"Available columns are: {', '.join(available_columns)}. "
            "Suggest the best match, considering synonyms, fuzzy matches, and business context. "
            "If no good match, ask the user for clarification."
        )
        return prompt