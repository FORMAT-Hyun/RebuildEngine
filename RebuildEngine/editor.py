#!/usr/bin/env python3
"""Launch Rebuild Engine — Project Manager first, then Editor."""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pygame


def main():
    pygame.init()
    try:
        pygame.font.init()
    except Exception:
        pass
    try:
        pygame.key.start_text_input()
    except Exception:
        pass

    screen = pygame.display.set_mode((1100, 720), pygame.RESIZABLE)
    pygame.display.set_caption("Rebuild Engine — 프로젝트")

    from editor.project_manager import ProjectManager
    from editor.ui import Fonts

    Fonts._cache.clear()
    Fonts._resolved = False

    mgr = ProjectManager(screen)
    project_path = mgr.run()

    if not project_path:
        pygame.quit()
        return

    # Enter editor with selected project
    pygame.display.set_caption("Rebuild Engine IDE")
    Fonts._cache.clear()
    Fonts._resolved = False

    from editor.editor import Editor
    Editor(project_path).run()


if __name__ == "__main__":
    main()
