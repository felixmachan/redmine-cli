from __future__ import annotations

import shutil
from pathlib import Path


MEDIUM_BANNER = r"""
 ____  _____ ____  __  __ ___ _   _ _____      ____ _     ___
|  _ \| ____|  _ \|  \/  |_ _| \ | | ____|    / ___| |   |_ _|
| |_) |  _| | | | | |\/| || ||  \| |  _|____| |   | |    | |
|  _ <| |___| |_| | |  | || || |\  | | |____| |___| |___ | |
|_| \_\_____|____/|_|  |_|___|_| \_|_____|    \____|_____|___|
""".strip("\n")

COMPACT_BANNER = r"""
 ____  ____  __  __  ___ _   _ _____      ____ _     ___
|  _ \|  _ \|  \/  ||_ _| \ | | ____|    / ___| |   |_ _|
| |_) | | | | |\/| | | ||  \| |  _|____| |   | |    | |
|  _ <| |_| | |  | | | || |\  | | |____| |___| |___ | |
|_| \_\____/|_|  |_|___|_| \_|_____|    \____|_____|___|
""".strip("\n")


def load_banner() -> str:
    ascii_path = Path(__file__).resolve().parents[1] / "ascii.txt"
    banner = MEDIUM_BANNER
    if ascii_path.exists():
        banner = ascii_path.read_text(encoding="utf-8", errors="replace").strip("\n")

    terminal_width = shutil.get_terminal_size((100, 30)).columns
    available_width = max(terminal_width - 2, 20)

    widest_line = max((len(line) for line in banner.splitlines()), default=0)
    if widest_line <= available_width:
        return banner

    medium_width = max((len(line) for line in MEDIUM_BANNER.splitlines()), default=0)
    if medium_width <= available_width:
        return MEDIUM_BANNER

    return COMPACT_BANNER


BANNER = load_banner()
