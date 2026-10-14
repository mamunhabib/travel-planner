"""
Travel Planner - Custom Exception Handler
Captures detailed traceback information (filename, line number, root cause).
"""
import sys
from typing import Optional

class CustomException(Exception):
    """
    Custom exception class that formats error messages with precise file
    and line number details from sys.exc_info() or exception tracebacks.
    """
    def __init__(self, message: str, error_detail: Optional[Exception] = None):
        self.raw_message = str(message)
        self.error_detail = error_detail
        self.file_name = "Unknown File"
        self.line_number = "Unknown Line"
        
        self.error_message = self._generate_detailed_message()
        super().__init__(self.error_message)

    def _generate_detailed_message(self) -> str:
        # Extract traceback from active execution context or original error
        _, _, exc_tb = sys.exc_info()
        
        if exc_tb is None and self.error_detail is not None:
            exc_tb = getattr(self.error_detail, "__traceback__", None)

        if exc_tb is not None:
            # Navigate to the innermost traceback frame where the error actually occurred
            tb = exc_tb
            while tb.tb_next:
                tb = tb.tb_next
            self.file_name = tb.tb_frame.f_code.co_filename
            self.line_number = tb.tb_lineno

        error_desc = f" | Root Error: {self.error_detail}" if self.error_detail else ""
        return (
            f"Error occurred in script [{self.file_name}] "
            f"at line [{self.line_number}]: {self.raw_message}{error_desc}"
        )

    def __str__(self) -> str:
        return self.error_message
