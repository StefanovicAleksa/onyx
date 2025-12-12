from pathlib import Path

class IgnoreRules:
    """
    Central logic for what files the scanner should skip.
    """
    
    # Exact folder/file names to ignore
    IGNORED_NAMES = {
        ".DS_Store", "Thumbs.db", "desktop.ini", 
        ".git", ".env", ".venv", "venv", "node_modules", 
        "__pycache__", ".idea", ".vscode"
    }

    # Extensions that are system/temp files
    IGNORED_EXTENSIONS = {
        ".tmp", ".log", ".bak", ".swp", ".pyc", ".class"
    }

    @classmethod
    def should_ignore(cls, path: Path) -> bool:
        """
        Returns True if the file/folder should be skipped.
        """
        # 1. Check exact name matches
        if path.name in cls.IGNORED_NAMES:
            return True
            
        # 2. Check hidden files (starts with dot)
        # We allow .gitignore but generally ignore dotfiles in data dirs
        if path.name.startswith(".") and path.name != ".gitignore":
            return True
            
        # 3. Check extensions (only for files)
        if path.is_file() and path.suffix.lower() in cls.IGNORED_EXTENSIONS:
            return True
            
        return False