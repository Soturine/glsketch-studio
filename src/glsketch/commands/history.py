from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Protocol


class Command(Protocol):
    label: str

    def do(self) -> None: ...

    def undo(self) -> None: ...


@dataclass(slots=True)
class History:
    _undo: list[Command]
    _redo: list[Command]

    def __init__(self) -> None:
        self._undo = []
        self._redo = []

    def execute(self, command: Command) -> None:
        command.do()
        self._undo.append(command)
        self._redo.clear()

    def undo(self) -> bool:
        if not self._undo:
            return False
        command = self._undo.pop()
        command.undo()
        self._redo.append(command)
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        command = self._redo.pop()
        command.do()
        self._undo.append(command)
        return True

    @property
    def undo_label(self) -> str | None:
        return self._undo[-1].label if self._undo else None

    @property
    def redo_label(self) -> str | None:
        return self._redo[-1].label if self._redo else None


class SceneHistory:
    """Snapshot history used at the UI transaction boundary."""

    def __init__(self, initial: dict[str, Any]) -> None:
        self._states = [deepcopy(initial)]
        self._index = 0

    def checkpoint(self, state: dict[str, Any]) -> None:
        snapshot = deepcopy(state)
        if snapshot == self._states[self._index]:
            return
        del self._states[self._index + 1 :]
        self._states.append(snapshot)
        self._index += 1

    def undo(self) -> dict[str, Any] | None:
        if self._index == 0:
            return None
        self._index -= 1
        return deepcopy(self._states[self._index])

    def redo(self) -> dict[str, Any] | None:
        if self._index >= len(self._states) - 1:
            return None
        self._index += 1
        return deepcopy(self._states[self._index])
