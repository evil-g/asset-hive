# -*- coding: utf-8 -*-
# Standard
import json
import os
import re


from . import filters

# Globals
CFG = None
DEFAULT_TAB = "Untitled_"


def get_config(reload=False):
    """
    Load config file

    Args:
        reload (bool): If True, reload config file
    """
    global CFG

    if CFG is None or reload:
        cfg_file = os.path.join(os.path.dirname(os.path.dirname(
            os.path.dirname(__file__))), "config", "asset_hive.json")
        with open(cfg_file, "r") as file:
            CFG = json.load(file)

    return CFG or {}


def default_tab():
    """
    Get default tab name

    Returns:
        Default name str
    """
    cfg = get_config()
    return cfg.get("default_tab_name", DEFAULT_TAB)


def is_default_tab(name):
    """
    Return True if input name matches default tab format
    """
    if re.search(default_tab() + "\d*$", name):
        return True

    return False


def is_preset_tab(name):
    """
    Return True if input name matches a preset name
    """
    for preset in get_presets().keys():
        if re.search(preset + "\d*$", name):
            return True

    return False


def is_str_filter(filter):
    """
    Return True if input filter is a str or unicode
    """
    return isinstance(filter, str) or isinstance(filter, unicode)


def get_presets(dirs=None):
    """
    Load presets out of given directory

    Args:
        dirs (list): List of

    """
    presets = {
        "All Assets": [],
        "Color": ["Grade", "OCIO", "LUT", "color"],
        "3D": ["Camera", "ReadGeo"],
        "Deep": ["Deep"],
        # "Pending Version Updates": ["pending_version_update"],
        # "Unpublished": ["unpublished"],
        "Version Updates": [filters.base_filter.PendingVersionUpdate],
        "Not Published": [filters.base_filter.UnpublishedAsset],
        "Test True": [filters.base_filter.TrueFilter],
        "Test False": [filters.base_filter.FalseFilter]
    }

    return presets
