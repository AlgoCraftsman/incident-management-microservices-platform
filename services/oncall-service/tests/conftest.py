from __future__ import annotations

import sys
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
COMMON_ROOT = Path(__file__).resolve().parents[3] / "libs" / "platform_common"
sys.path.insert(0, str(COMMON_ROOT))
sys.path.insert(0, str(SERVICE_ROOT))

for module_name in list(sys.modules):
    if module_name == "app" or module_name.startswith("app.") or module_name.startswith("platform_common"):
        del sys.modules[module_name]
