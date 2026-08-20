from dataclasses import dataclass

from glsketch.commands import History, SceneHistory


@dataclass
class AppendCommand:
    target: list[int]
    value: int
    label: str = "append"

    def do(self) -> None:
        self.target.append(self.value)

    def undo(self) -> None:
        self.target.pop()


def test_history_undo_redo() -> None:
    values: list[int] = []
    history = History()
    history.execute(AppendCommand(values, 3))
    assert values == [3]
    assert history.undo()
    assert values == []
    assert history.redo()
    assert values == [3]


def test_scene_history_discards_redo_branch() -> None:
    history = SceneHistory({"value": 1})
    history.checkpoint({"value": 2})
    assert history.undo() == {"value": 1}
    history.checkpoint({"value": 3})
    assert history.redo() is None
    assert history.undo() == {"value": 1}
