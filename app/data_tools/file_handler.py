import pandas as pd
import openpyxl
from typing import Dict, List, Any, Optional, Union
import os
from pathlib import Path
import logging

class ExcelFileHandler:
    """Handles Excel file operations with memory-efficient processing"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def validate_file(self, file_path: str) -> bool:
        """Validate file size, format, and accessibility"""
        try:
            path = Path(file_path)
            
            # Check file exists
            if not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Check file size
            file_size_mb = path.stat().st_size / (1024 * 1024)
            if file_size_mb > self.config.MAX_FILE_SIZE_MB:
                raise ValueError(f"File too large: {file_size_mb:.1f}MB > {self.config.MAX_FILE_SIZE_MB}MB")
            
            # Check file format
            if path.suffix.lower() not in self.config.SUPPORTED_FORMATS:
                raise ValueError(f"Unsupported format: {path.suffix}")
                
            return True
            
        except Exception as e:
            self.logger.error(f"File validation failed: {e}")
            raise
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get comprehensive file information"""
        try:
            self.validate_file(file_path)
            
            # Use openpyxl for metadata without loading data
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            
            sheet_info = {}
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                sheet_info[sheet_name] = {
                    'max_row': ws.max_row,
                    'max_column': ws.max_column,
                    'has_data': ws.max_row > 1
                }
            
            wb.close()
            
            return {
                'file_path': file_path,
                'file_size_mb': Path(file_path).stat().st_size / (1024 * 1024),
                'sheet_names': list(sheet_info.keys()),
                'sheet_info': sheet_info,
                'total_sheets': len(sheet_info)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting file info: {e}")
            raise
    
    def read_sheet_chunked(self, file_path: str, sheet_name: str, 
                          chunk_size: Optional[int] = None) -> List[pd.DataFrame]:
        """Read large sheets in chunks to manage memory"""
        chunk_size = chunk_size or self.config.CHUNK_SIZE
        chunks = []
        
        try:
            # Get total rows first
            wb = openpyxl.load_workbook(file_path, read_only=True)
            total_rows = wb[sheet_name].max_row
            wb.close()
            
            # Read in chunks
            for start_row in range(1, total_rows + 1, chunk_size):
                end_row = min(start_row + chunk_size - 1, total_rows)
                
                # Skip if we're past header and this would be empty
                if start_row > 1 and start_row >= total_rows:
                    break
                
                # Read chunk
                if start_row == 1:
                    # First chunk includes headers
                    df_chunk = pd.read_excel(file_path, sheet_name=sheet_name, 
                                           nrows=chunk_size)
                else:
                    # Subsequent chunks skip headers
                    df_chunk = pd.read_excel(file_path, sheet_name=sheet_name, 
                                           skiprows=start_row-1, nrows=chunk_size)
                    # Use first chunk's columns
                    if chunks:
                        df_chunk.columns = chunks[0].columns
                
                chunks.append(df_chunk)
                self.logger.info(f"Loaded chunk {len(chunks)}: rows {start_row}-{end_row}")
        
        except Exception as e:
            self.logger.error(f"Error reading sheet in chunks: {e}")
            raise
            
        return chunks
    
    def read_sheet_sample(self, file_path: str, sheet_name: str, 
                         sample_size: int = 100) -> pd.DataFrame:
        """Read a sample of the sheet for analysis"""
        try:
            return pd.read_excel(file_path, sheet_name=sheet_name, nrows=sample_size)
        except Exception as e:
            self.logger.error(f"Error reading sheet sample: {e}")
            raise
