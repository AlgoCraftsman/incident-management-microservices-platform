from __future__ import annotations

import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

for module_name in list(sys.modules):
    if module_name == "platform_common" or module_name.startswith("platform_common."):
        del sys.modules[module_name]
