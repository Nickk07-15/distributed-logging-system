class BadZipFileException(Exception):
    """Exception raised for errors in the zip file format."""
    pass

class FilePathDeleteException(Exception):
    """Exception raised for errors while deleting a file."""
    pass