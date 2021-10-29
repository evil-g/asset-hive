# -*- coding: utf-8 -*-
# Standard
import os
import subprocess

from core_pipeline.utils import path_utils


def open_file_browser(path):
    """
    Open directory path in file browser

    Args:
        path (str): Filepath str

    Returns: None
    """
    # Map path for current OS
    path = os.path.normpath(path_utils.clean_path(path))

    # Verify path exists
    if not path or not os.path.exists(path):
        raise OSError("Path '{0}' does not exist!".format(path))

    # Windows Explorer
    if "nt" == os.name:
        cmd = "explorer /open,{0}".format(path)
    # Linux Dolphin
    else:
        cmd = "dolphin {0}".format(path)

    # TODO Replace with log
    print("Opening:", cmd)
    subprocess.Popen(cmd, shell=True)
