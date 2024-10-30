"""File processors package.

Provides processors for different file types:
- Assy (Assembly)
- Fabcut
- LP (Lamination)
- SEW-DC (Sew Dress-Cover)
- SEW-FB (Sew Fire-Block)
"""
from src.processors.base import FileProcessor
from src.processors.assy import create_assy_processor
from src.processors.fabcut import create_fabcut_processor
from src.processors.lp import create_lp_processor
from src.processors.sewdc import create_sewdc_processor
from src.processors.sewfb import create_sewfb_processor

__all__ = [
    'FileProcessor',
    'create_assy_processor',
    'create_fabcut_processor',
    'create_lp_processor',
    'create_sewdc_processor',
    'create_sewfb_processor'
]