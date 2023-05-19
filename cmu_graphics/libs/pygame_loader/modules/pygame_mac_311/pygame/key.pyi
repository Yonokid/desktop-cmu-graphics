from typing import Tuple

from ._common import RectValue

class ScancodeWrapper(Tuple[bool, ...]): ...

def get_focused() -> bool: ...
def get_pressed() -> ScancodeWrapper: ...
def get_mods() -> int: ...
def set_mods(mods: int) -> None: ...
def set_repeat(delay: int = 0, interval: int = 0) -> None: ...
def get_repeat() -> Tuple[int, int]: ...
def name(key: int, use_compat: bool = True) -> str: ...
def key_code(name: str) -> int: ...
def start_text_input() -> None: ...
def stop_text_input() -> None: ...
def set_text_input_rect(rect: RectValue) -> None: ...
