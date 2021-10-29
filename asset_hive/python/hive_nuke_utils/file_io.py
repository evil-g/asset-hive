# -*- coding: utf-8 -*-
# Standard
from builtins import bytes, range, str
import re

# Third party
import nuke
import nukescripts

# Pipeline
from core_pipeline.utils import file_io


def nodeCopy_with_root(filepath, nodes=None):
    """
    Export selected nodes with root node as well
    nuke.nodeCopy does not natively export the Root node

    Args:
        filepath (str): File path
        nodes (list): List of nodes to export
                      If None, export all nodes
    """
    # Select input nodes
    if nodes:
        nukescripts.clear_selection_recursive()
        for node in nodes:
            node.knob("selected").setValue(True)
    # Select all
    else:
        nuke.selectAll()

    # Export
    nuke.nodeCopy(filepath)

    # Add root node
    # Root .nk text
    root_str = nuke.root().writeKnobs(nuke.TO_SCRIPT | nuke.WRITE_ALL)
    root_tmp = "Root {\n"
    for line in root_str.split("\n"):
        if line:
            root_tmp += " {0}\n".format(line)
    root_tmp += "}"

    # Python3 - Decode bytes str if necessary
    result = file_io.load(filepath)
    if isinstance(result, bytes):
        result = result.decode("utf8")
    # Insert Root as first node
    data = re.sub(r"\r", "", result)
    pre_lines = data.split("\n")
    for idx in range(0, len(pre_lines)):
        if pre_lines[idx].endswith("{"):
            break
    pre_lines.insert(idx if idx > 0 else 0, root_tmp)

    # Encode for output
    try:
        output = "\n".join(pre_lines).encode("utf8")
    except Exception:
        output = "\n".join(pre_lines)

    # Reexport with root
    file_io.save(output, filepath, overwrite=True)
