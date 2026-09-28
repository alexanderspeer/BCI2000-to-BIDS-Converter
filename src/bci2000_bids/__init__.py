"""Public Python API for converting BCI2000 recordings to BIDS."""

from .convert import ConversionReport, convert
from .bci2000.reader import BCI2000Recording

__all__ = ["BCI2000Recording", "ConversionReport", "convert"]
__version__ = "0.1.0"
