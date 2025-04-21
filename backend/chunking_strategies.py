import re
from typing import List

def markdown_header_chunks(text: str) -> List[str]:
        """
        Chunk text based on markdown headers.
        
        Args:
            text: The markdown text to chunk.
            
        Returns:
            List of text chunks with headers as separation points.
        """
        # Regular expression to find markdown headers
        header_pattern = re.compile(r'^(#{1,6})\s+(.*)', re.MULTILINE)
        
        # Find all headers and their positions
        headers = [(match.start(), match.group()) for match in header_pattern.finditer(text)]
        
        # If no headers found, return whole text as one chunk
        if not headers:
            return [text.strip()]
        
        chunks = []
        
        # First chunk includes everything before the first header
        if headers[0][0] > 0:
            chunks.append(text[:headers[0][0]].strip())
        
        # Process chunks between headers
        for i in range(len(headers)):
            start_pos = headers[i][0]
            # If this is the last header, end position is the end of text
            if i == len(headers) - 1:
                end_pos = len(text)
            else:
                end_pos = headers[i+1][0]
            
            # Add the chunk, including the header
            chunk = text[start_pos:end_pos].strip()
            if chunk:
                chunks.append(chunk)
        
        return [chunk for chunk in chunks if chunk]  # Remove any empty chunks