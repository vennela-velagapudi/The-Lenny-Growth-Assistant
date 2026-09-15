import tiktoken
from typing import List

class DocumentChunker:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.encoder = tiktoken.get_encoding("cl100k_base")

    def chunk_text(self, text: str) -> List[str]:
        # Split by double newline to respect paragraphs first, then token size
        paragraphs = text.split("\n\n")
        
        chunks = []
        current_chunk_tokens = []
        
        def commit_chunk(tokens: List[int]):
            if not tokens:
                return
            chunks.append(self.encoder.decode(tokens))
            
        for para in paragraphs:
            para_tokens = self.encoder.encode(para + "\n\n")
            
            # If a single paragraph is too big, we split it forcefully
            if len(para_tokens) > self.chunk_size:
                # Commit what we have so far
                if current_chunk_tokens:
                    commit_chunk(current_chunk_tokens)
                    # Start new chunk with overlap
                    overlap_tokens = current_chunk_tokens[-self.chunk_overlap:] if self.chunk_overlap > 0 else []
                    current_chunk_tokens = overlap_tokens
                
                # Split the large paragraph
                for i in range(0, len(para_tokens), self.chunk_size - self.chunk_overlap):
                    part_tokens = para_tokens[i : i + self.chunk_size]
                    if len(current_chunk_tokens) + len(part_tokens) > self.chunk_size:
                        commit_chunk(current_chunk_tokens)
                        current_chunk_tokens = current_chunk_tokens[-self.chunk_overlap:] if current_chunk_tokens else []
                    
                    current_chunk_tokens.extend(part_tokens)
                    if len(current_chunk_tokens) >= self.chunk_size:
                        commit_chunk(current_chunk_tokens)
                        current_chunk_tokens = current_chunk_tokens[-self.chunk_overlap:]
            else:
                if len(current_chunk_tokens) + len(para_tokens) > self.chunk_size:
                    commit_chunk(current_chunk_tokens)
                    overlap_tokens = current_chunk_tokens[-self.chunk_overlap:] if self.chunk_overlap > 0 else []
                    current_chunk_tokens = overlap_tokens
                
                current_chunk_tokens.extend(para_tokens)
                
        if current_chunk_tokens:
            commit_chunk(current_chunk_tokens)
            
        return [c.strip() for c in chunks if c.strip()]
