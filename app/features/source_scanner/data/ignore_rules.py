from pathlib import Path

class IgnoreRules:
    """
    Central logic for what files to skip.
    """
    
    # Files/Folders to strictly ignore
    IGNORED_NAMES = {
        ".DS_Store", "Thumbs.db", ".git", ".env", 
        "__pycache__", "venv", "node_modules", ".idea", ".vscode"
    }

    # Extensions we definitely don't want
    IGNORED_EXTENSIONS = {
        ".tmp", ".log", ".bak", ".swp", ".pyc"
    }

    @classmethod
    def should_ignore(cls, path: Path) -> bool:
        """
        Returns True if the file/folder should be skipped.
        """
        # 1. Check strict names
        if path.name in cls.IGNORED_NAMES:
            return True
            
        # 2. Check hidden files (starts with dot)
        # Exception: .gitignore is often useful context for code, 
        # but for now we ignore hidden system files.
        if path.name.startswith(".") and path.name != ".gitignore":
            return True
            
        # 3. Check extensions (only for files)
        if path.is_file() and path.suffix.lower() in cls.IGNORED_EXTENSIONS:
            return True
            
        return False