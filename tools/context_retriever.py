"""
Context Retriever Agent - Timeline Stitching

Automatically stitches split context files together to preserve progression
intelligence across file boundaries.

Philosophy: "Hope in knowledge" - preserve complete progression timeline
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .evidence_monitor import EvidenceEntry

logger = logging.getLogger(__name__)


@dataclass
class ContextChain:
    """Represents a chain of linked context files"""
    primary_file: str
    chain_files: List[str]  # Ordered from oldest to newest
    total_entries: int
    context_type: str
    date_range: tuple[str, str]  # (earliest, latest)


@dataclass
class ContextMetadata:
    """Metadata for a context file (in file or separate .json)"""
    context_file: str
    previous_context_file: Optional[str] = None
    next_context_file: Optional[str] = None
    entry_range: tuple[int, int] = (0, 0)  # First and last entry numbers
    split_reason: Optional[str] = None  # "token_limit" or None
    context_type: str = ""
    primary_context: str = ""
    secondary_contexts: List[str] = None
    
    def __post_init__(self):
        if self.secondary_contexts is None:
            self.secondary_contexts = []


class ContextRetriever:
    """
    Retrieves and stitches context files to preserve progression timeline.
    
    Features:
    - Detect context file chains (file-1, file-2, file-3)
    - Stitch files together in memory
    - Preserve complete progression timeline
    - Handle multi-context linking
    """
    
    def __init__(self):
        self._metadata_cache: dict[str, ContextMetadata] = {}
    
    async def get_full_context(
        self,
        context_file: str,
        ticket_id: str = None
    ) -> tuple[str, ContextChain]:
        """
        Get complete context including all chained files.
        
        Args:
            context_file: Current context file path
            ticket_id: Optional ticket ID for scoping
            
        Returns:
            (stitched_content, context_chain)
        """
        # Build the chain
        chain = await self._build_context_chain(context_file)
        
        # Read and stitch all files
        stitched_content = await self._stitch_files(chain.chain_files)
        
        return stitched_content, chain
    
    async def _build_context_chain(self, context_file: str) -> ContextChain:
        """
        Build the complete chain of context files.
        
        Follows chain links forward and backward to find all related files.
        """
        file_path = Path(context_file)
        
        # Find all files in chain
        chain_files = []
        
        # Check for numbered sequence pattern
        # e.g., database-performance.md, database-performance-1.md, database-performance-2.md
        base_name = file_path.stem
        parent_dir = file_path.parent
        
        # Remove trailing number if exists
        base_name_clean = re.sub(r'-\d+$', '', base_name)
        
        # Find all files matching pattern
        pattern = f"{base_name_clean}*.md"
        matching_files = sorted(parent_dir.glob(pattern))
        
        if not matching_files:
            # Single file, no chain
            return ContextChain(
                primary_file=context_file,
                chain_files=[context_file],
                total_entries=0,
                context_type=base_name_clean,
                date_range=("", "")
            )
        
        # Sort by number suffix
        def get_file_number(filepath: Path) -> int:
            match = re.search(r'-(\d+)\.md$', str(filepath))
            return int(match.group(1)) if match else 0
        
        sorted_files = sorted(matching_files, key=get_file_number)
        chain_files = [str(f) for f in sorted_files]
        
        # Get metadata from each file
        total_entries = 0
        earliest_date = ""
        latest_date = ""
        
        for file_path_str in chain_files:
            metadata = await self._read_metadata(file_path_str)
            if metadata:
                total_entries += metadata.entry_range[1] - metadata.entry_range[0] + 1
                
                # Track date range (simplified - would parse from entries in real impl)
                if not earliest_date:
                    earliest_date = metadata.context_file
                latest_date = metadata.context_file
        
        return ContextChain(
            primary_file=chain_files[0],
            chain_files=chain_files,
            total_entries=total_entries,
            context_type=base_name_clean,
            date_range=(earliest_date, latest_date)
        )
    
    async def _stitch_files(self, file_paths: List[str]) -> str:
        """
        Stitch multiple context files together.
        
        Adds navigation headers between files for clarity.
        """
        stitched = []
        
        for i, file_path in enumerate(file_paths):
            path = Path(file_path)
            
            if not path.exists():
                continue
            
            content = path.read_text()
            
            # Add file navigation header
            if i > 0:
                stitched.append(f"\n\n{'='*80}\n")
                stitched.append(f"## Continuation from: {path.name}\n")
                stitched.append(f"{'='*80}\n\n")
            
            stitched.append(content)
        
        return "".join(stitched)
    
    async def _read_metadata(self, file_path: str) -> Optional[ContextMetadata]:
        """
        Read metadata from file (YAML frontmatter or HTML comments).
        
        Checks cache first for performance.
        """
        if file_path in self._metadata_cache:
            return self._metadata_cache[file_path]
        
        path = Path(file_path)
        if not path.exists():
            return None
        
        content = path.read_text()
        
        # Try to extract metadata from HTML comments (Guardian's lightweight metadata)
        metadata = ContextMetadata(context_file=file_path)
        
        # Extract previous/next file links
        prev_match = re.search(r'<!-- previous_context_file:\s*(.+?)\s*-->', content)
        if prev_match:
            metadata.previous_context_file = prev_match.group(1)
        
        next_match = re.search(r'<!-- next_context_file:\s*(.+?)\s*-->', content)
        if next_match:
            metadata.next_context_file = next_match.group(1)
        
        # Extract entry range
        entry_range_match = re.search(r'<!-- entry_range:\s*(\d+),\s*(\d+)\s*-->', content)
        if entry_range_match:
            metadata.entry_range = (int(entry_range_match.group(1)), int(entry_range_match.group(2)))
        
        # Extract primary context
        primary_match = re.search(r'<!-- primary_context:\s*(.+?)\s*-->', content)
        if primary_match:
            metadata.primary_context = primary_match.group(1)
        
        # Extract secondary contexts
        secondary_match = re.search(r'<!-- secondary_contexts:\s*(.+?)\s*-->', content)
        if secondary_match:
            metadata.secondary_contexts = [c.strip() for c in secondary_match.group(1).split(',')]
        
        # Cache it
        self._metadata_cache[file_path] = metadata
        
        return metadata
    
    async def create_link_entry(
        self,
        target_file: str,
        source_file: str,
        entry_number: int,
        context_type: str
    ) -> str:
        """
        Create a link entry for secondary context files.
        
        This allows agents specializing in secondary contexts to find
        relevant evidence without duplicating content.
        
        Args:
            target_file: File to add link to
            source_file: File containing full evidence
            entry_number: Entry number in source file
            context_type: Context type
            
        Returns:
            Link entry markdown
        """
        timestamp = Path(source_file).stat().st_mtime
        
        link_entry = f"""
---

## Evidence Entry (Link): See {Path(source_file).name} #{entry_number}

<!-- type: link -->
<!-- source_file: {source_file} -->
<!-- source_entry: {entry_number} -->
<!-- context: {context_type} -->

### Related Evidence
This entry is primarily documented in **{Path(source_file).name}, Entry #{entry_number}**.

**Context**: {context_type}  
**File**: `{source_file}`  
**Entry**: #{entry_number}

**Why this link exists**: This evidence has both {Path(target_file).stem} and {Path(source_file).stem} context. The full details are in the primary context file to avoid duplication.

---
"""
        return link_entry


# Global retriever instance
_retriever: Optional[ContextRetriever] = None


def get_retriever() -> ContextRetriever:
    """Get or create the global context retriever"""
    global _retriever
    if _retriever is None:
        _retriever = ContextRetriever()
    return _retriever

