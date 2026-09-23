from __future__ import annotations

from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])

from ui.machine.widgets import SectionTabs


def test_section_tabs_set_active_checks_only_that_button():
    tabs = SectionTabs([("a", "A"), ("b", "B"), ("c", "C")])

    tabs.set_active("b")

    assert tabs.button("a").isChecked() is False
    assert tabs.button("b").isChecked() is True
    assert tabs.button("c").isChecked() is False


def test_section_tabs_clicking_emits_key():
    tabs = SectionTabs([("a", "A"), ("b", "B")])
    clicked: list[str] = []
    tabs.tabClicked.connect(clicked.append)

    tabs.button("b").click()

    assert clicked == ["b"]
