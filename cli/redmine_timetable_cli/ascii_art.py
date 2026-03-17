from __future__ import annotations

import shutil
from pathlib import Path


MEDIUM_BANNER = r"""
  ____  _____ ____  __  __ ___ _   _ _____
 |  _ \| ____|  _ \|  \/  |_ _| \ | | ____|
 | |_) |  _| | | | | |\/| || ||  \| |  _|
 |  _ <| |___| |_| | |  | || || |\  | |___
 |_| \_\_____|____/|_|  |_|___|_| \_|_____|

 _____ ___ __  __ _____ _____  _    ____  _     _____
|_   _|_ _|  \/  | ____|_   _|/ \  | __ )| |   | ____|
  | |  | || |\/| |  _|   | | / _ \ |  _ \| |   |  _|
  | |  | || |  | | |___  | |/ ___ \| |_) | |___| |___
  |_| |___|_|  |_|_____| |_/_/   \_\____/|_____|_____|
""".strip("\n")

COMPACT_BANNER = r"""
 ____  _____ ____  __  __ ___ _   _ _____
|  _ \| ____|  _ \|  \/  |_ _| \ | | ____|
| |_) |  _| | | | | |\/| || ||  \| |  _|
|  _ <| |___| |_| | |  | || || |\  | |___
|_| \_\_____|____/|_|  |_|___|_| \_|_____|
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
