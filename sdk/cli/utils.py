"""
ModernTensor CLI — Utils (compatibility shim)
═════════════════════════════════════════════

This module previously created its own ``Console()`` and helper functions.
Everything is now consolidated in ``sdk.cli.ui`` to guarantee a single themed
console.  The public names are re-exported here so that existing imports
(``from sdk.cli.utils import console, print_info, ...``) continue to work.
"""

from sdk.cli.ui import (          # noqa: F401 – intentional re-exports
    console,
    print_error,
    print_info,
    print_success,
    print_warning,
)
