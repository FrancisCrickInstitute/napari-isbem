try:
    from ._version import version as __version__
except ImportError:
    __version__ = 'unknown'

from ._widgets import iSBEMWidget as iSBEMWidget

__all__ = ['iSBEMWidget']
