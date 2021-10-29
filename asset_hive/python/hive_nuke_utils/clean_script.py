# -*- coding: utf-8 -*-
# Standard
from __future__ import print_function
import re

# Pipeline
from . import script_utils


def remove_panelDropped(nodes=None, verbose=False):
    """
    Remove extra panelDropped knobs
    (Ex: test_panelDropped_1_1_1, etc)

    Args:
        nodes (list): List of nodes to check for panelDropped knobs
                      Defaults to all Group nodes in the current scene
        verbose (bool): If True, print the number of knobs removed
                        from each node

    Returns: None
    """
    if nodes is None:
        nodes = script_utils.get_all_nodes(classes=["Group"])

    for node in nodes:
        removed = 0
        for knob_name, knob in node.knobs().items():
            # Knob has extra panelDropped
            match = re.search("panelDropped(_\d+)+$", knob_name)
            if match:
                node.removeKnob(knob)
                removed += 1

        if verbose and removed:
            print("{0}: removed {1} panelDropped knobs".format(
                node.fullName(), removed))
