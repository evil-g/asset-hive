# Standard
import json
import os
import re
import traceback

# Third party
import nuke
import nukescripts

# Pipeline
from core_pipeline.utils import path_utils


# Globals
DOT_OFFSET = 33

# File knob names for special Node classes
# (Used when file knob isn't named 'file')
NODE_FILE_KNOBS = {
    "Vectorfield": ["vfield_file"]
}

# Default knobs to skip when swapping nodes
SKIP_KNOBS = ["label", "name", "xpos", "ypos", "anima_source_file", "file"]
FRAME_KNOBS = ["first", "last", "origfirst", "origlast"]

# Knob naming
ANIMA_SRC_KNOB = "anima_source_file"
ANIMA_TYPE_KNOB = "anima_type"
DEFAULT_KNOB_STR = "default \((?P<value>.*)\)$"


def element_break_down():
    """
    Shuffle out each channel of input node
    """
    try:
        node = nuke.selectedNode()
    except ValueError:
        nuke.message("No Node selected!")
        return

    # Channels
    channels = [ch.split(".")[0] for ch in node.channels()]

    for name in set(channels):
        shuffle = nuke.nodes.Shuffle(name=name, inputs=[node])
        shuffle.knob("in").setValue(name)
        shuffle.knob("postage_stamp").setValue(1)


def get_node_range(node):
    """
    Get first/last frame for a node

    Args:
        node (nuke.Node): Node to get frame range for

    Returns:
        (First, Last) tuple
    """
    return (int(node.knob("first").value()), int(node.knob("last").value()))


def get_node_files(node, anima_knobs=False):
    """
    Get files referenced by this node

    Args:
        node (Nuke.Node): Node to operate on
        anima_knobs (bool, optional): If True, check for custom anima knobs too

    Returns:
        Dict of knob_name: file path pairs
    """
    if not node:
        return {}

    # File knobs for this node
    # (Default is 'file')
    knob_names = NODE_FILE_KNOBS.get(node.Class()) or ["file"]
    # Add custom anima knobs
    if anima_knobs:
        knob_names.append(ANIMA_SRC_KNOB)

    knob_data = {}
    for knob_name in knob_names:
        # Add node name/file path to dict
        if node.knob(knob_name) and node.knob(knob_name).value():
            # Node has a file entry
            knob_data[knob_name] = node.knob(knob_name).value()

    return knob_data


def map_node_for_os(node=None):
    """
    Update a node for the current os

    Args:
        node (Nuke.Node): Node
    """
    # Default to current node
    if not node:
        node = nuke.thisNode()

    if not node:
        return

    # Update each file knob
    for knob_name, file in get_node_files(node).iteritems():
        # Get mapped file path
        try:
            mapped_file = path_utils.dirmap(file, os_name=os.name)
        except Exception:
            nuke.tprint("Error! Failed to update '{0}'"
                        "".format(node.fullName()))
            traceback.print_exc()
            mapped_file = file

        # TODO 'UnicodeWarning: Unicode equal comparison failed to convert'
        #      'both args to Unicode - interpreting them as being unequal'
        # No update required
        if file == mapped_file:
            continue

        # Update knob
        nuke.tprint("Updating Node '{0}' filepath for {1}"
                    "".format(node.fullName(), os.name))
        update_file(node, knob_name, mapped_file, no_popup=True)


def update_file(node, knob_name, file, no_popup=False):
    """
    Update file path on node while retaining any
    geometry selection if it has a scene_view (Eg: ReadGeo2)

    Args:
        node (Nuke.Node): Node
        knob_name (str): Knob name
        file (str): New file setting
        no_popup (bool, optional): If True, use readKnobs call to skip
                                   knobChanged callback when node is updated.

    Returns:
        True if successful
    """
    # Check knob
    if not node.knob(knob_name):
        nuke.tprint("Error: Failed to update missing knob on {0}!"
                    "".format(node.fullName()))
        return False

    # If geo node, retain geo import
    scene_view = node.knob("scene_view")
    if scene_view:
        orig_sel = scene_view.getSelectedItems()
        orig_import = scene_view.getImportedItems()

    # Update node
    # Note: Use readKnobs to prevent popups. However, this avoids triggering
    # the knobChanged callback, so should be used sparingly (for ex in
    # case of simply remapping the filepath drive for the current OS)
    if no_popup:
        node.readKnobs(knob_name + " " + file)
    else:
        node.knob(knob_name).setValue(file)
    nuke.tprint("Updated node '{0}' file to '{1}'"
                "".format(node.fullName(), file))

    # After file update, set original selection for geo
    if scene_view:
        # Force validate (required due to Nuke bug)
        node.forceValidate()
        # Selected
        scene_view.setSelectedItems(orig_sel)
        nuke.tprint("Updated selected items: {0}".format(orig_sel))
        # Imported
        scene_view.setImportedItems(orig_import)
        nuke.tprint("Updated imported items: {0}".format(orig_import))

    return True


def swap_node(node_a, node_b, cleanup=True, skip_knobs=SKIP_KNOBS,
              skip_frames=False):
    """
    Swap node a for node b, then delete node a

    Args:
        node_a (Nuke.Node): Node to transfer values from
        node_b (Nuke.Node): Node to transfer values to
        cleanup (bool, optional): Delete Node A after the transfer
        skip_knobs (list): List of knob names to skip when swapping
        skip_frames (bool): If True, do not transfer the old frame
                            range to the new node.
                            Defaults to False.

    Returns:
        Nuke.Node
    """
    if isinstance(node_a, str):
        node_a = nuke.toNode(node_a)

    if isinstance(node_b, str):
        node_b = nuke.toNode(node_b)

    # Node is missing
    if not node_a or not node_b:
        raise RuntimeError("Failed to swap nodes!")

    # Transfer dependents
    # All nodes depending on Node A through expressions or inputs
    # (Downstream connections)
    dependents = node_a.dependent(
        nuke.EXPRESSIONS | nuke.INPUTS | nuke.HIDDEN_INPUTS,
        forceEvaluate=False)
    for dependent in dependents:
        # Find Node A in the dependent list and
        # replace it with Node B
        for idx in range(dependent.inputs()):
            if dependent.input(idx) == node_a:
                dependent.setInput(idx, node_b)
                break

    # Transfer dependencies of Node A
    # (Upstream connections)
    dependencies = node_a.dependencies(
        nuke.EXPRESSIONS | nuke.INPUTS | nuke.HIDDEN_INPUTS)
    for dependency in dependencies:
        # Find the dependency node in Node A's input list
        # Connect Node B to the dependency node
        for idx in range(node_a.inputs()):
            # Remove Node A input
            node_a.setInput(idx, None)
            # Connect
            node_b.setInput(idx, dependency)

    # TODO Transfer expressions? Test

    # Ignore frame knobs when necessary
    if skip_frames:
        skip_knobs.extend(FRAME_KNOBS)

    # Transfer knob values
    for knob_name, knob in node_a.knobs().iteritems():
        # Missing knob
        if knob_name in skip_knobs or not node_b.knob(knob_name):
            continue

        # Clean knob value
        # Eg: If value if a default style string (Eg: 'default (linear)'),
        #     strip out everything except what's inside the parentheses
        value = knob.value()
        if isinstance(value, str):
            match = re.match(DEFAULT_KNOB_STR, value)
            if match:
                value = match.group("value")

        # Set value on Node B
        try:
            node_b.knob(knob_name).setValue(value)
        except Exception:
            print "Failed to transfer knob value '{0}' from {1} to {2}" \
                "".format(knob_name, node_a.fullName(), node_b.fullName())

    # Get Node A position
    a_xpos = node_a.xpos()
    a_ypos = node_a.ypos()

    # Delete Node A
    if cleanup:
        nuke.delete(node_a)

    # Set Node B to Node A's position
    node_b.setXYpos(a_xpos, a_ypos)

    return node_b


def _setup_knob(knob, value, flags=None):
    """
    Set up knob

    Args:
        knob (nuke.Knob): Input knob
        value (str, etc): Knob value
        flags (list): List of nuke knob flags
                      Eg: [nuke.READ_ONLY, nuke.INVISIBLE]

    Returns: None
    """
    knob.setValue(value)

    if flags:
        # List of flags
        if isinstance(flags, list):
            for flag in flags:
                knob.setFlag(flag)
        # Single flag
        elif isinstance(flags, int):
            knob.setFlag(flags)
        else:
            try:
                knob.setFlag(flags)
            except Exception:  # Invalid
                raise ValueError("Invalid flag type '{0}': {1}"
                                 "".format(type(flags), flags))


def add_text_knob(node, name, value, flags=None):
    """
    Add text knob to the given node

    Args:
        node (nuke.Node): Node to add to
        name (str): Knob name
        value (str): Knob value
        flags (list): Nuke knob flags

    Returns:
        Nuke.Knob
    """
    # Create knob
    knob = nuke.Text_Knob(name)

    # Use json dump for dict
    if isinstance(value, dict):
        value = json.dumps(value)

    # Knob settings
    _setup_knob(knob, value, flags)

    # Add to node
    node.addKnob(knob)

    return knob


def add_str_knob(node, name, value, flags=None):
    """
    Add string knob to the given node

    Args:
        node (nuke.Node): Node to add to
        name (str): Knob name
        value (str): Knob value
        flags (list): Nuke knob flags

    Returns:
        Nuke.Knob
    """
    # Create knob
    knob = nuke.String_Knob(name)

    # Use json dump for dict
    if isinstance(value, dict):
        value = json.dumps(value)

    # Knob settings
    _setup_knob(knob, value, flags)

    # Add to node
    node.addKnob(knob)

    return knob


def add_anima_file_knob(node, path):
    """
    Add a knob called 'anima_source_file' to the provided node.
    Used to track source files for nodes that don't have
    a file knob (keyed Transform nodes, BackdropNodes, etc).

    Args:
        node (Nuke.Node): Source node
        path (str): Filepath

    Returns:
        Nuke.Knob
    """
    return add_text_knob(node, ANIMA_SRC_KNOB, path)


def get_anima_file_knob(node):
    """
    Get anima file knob on the given node
    """
    return node.knob(ANIMA_SRC_KNOB)


def add_anima_type_knob(node, value):
    """
    Generic anima type knob to tag nodes with relevant info

    Args:
        node (nuke.Node): Input node
        value (str): Knob value

    Returns:
        nuke.Knob
    """
    return add_text_knob(node, ANIMA_TYPE_KNOB, value)


def get_anima_type_knob(node):
    """
    Get anima file knob on the given node
    """
    return node.knob(ANIMA_TYPE_KNOB)


def add_backdrop(nodes):
    """
    Add a backdrop to the list of nodes

    Args:
        nodes (list): List of Nuke nodes

    Returns:
        Backdrop node
    """
    nukescripts.clear_selection_recursive()

    # Select nodes
    for node in nodes:
        node.knob("selected").setValue(True)
        node.setXYpos(node.xpos() + 1000, node.ypos() + 1000)
        # node.autoplace()

    # Autoplace backdrop
    backdrop = nukescripts.autobackdrop.autoBackdrop()
    # nukescripts.clear_selection_recursive()
    # backdrop.autoplace()

    return backdrop


def key_knob(knob, keys, start, end, debug=False):
    """
    Key a node knob

    Args:
        knob (nuke.Knob): Knob to key
        keys (list): List of values for keys
        start (int): Start frame
        end (int): End frame
        debug (bool): If True, print keys
    """
    knob.setAnimated(0)
    knob.setAnimated(1)

    # Get anim curves
    animations = knob.animations()

    # Apply shake data for each camera
    pixel_iter = iter(keys)
    for frame in range(start, end):
        # Get next shake list
        try:
            input = pixel_iter.next()
        except StopIteration:
            raise ValueError("Shake data is missing entries for frames in"
                             "{0}-{1}".format(start, end))

        if debug:
            print "Setting key: {0} ({1}, {2})".format(input)

        # Multiple keys
        if isinstance(input, list):
            for idx in range(0, len(input)):
                try:
                    animations[idx].setKey(frame, input[idx])
                except IndexError:
                    raise IndexError(
                        "Animation curve + input key len mismatch! "
                        "Curves: {0} | Keys: {1}".format(animations, input))
        # Single key
        else:
            # Set on all available curves
            for curve in animations:
                curve.setKey(frame, input)

    return knob


def move_dependencies(input_node, skip_hidden=True):
    """
    Move dependencies of the input node vertically

    TODO: This could be improved a bit, and assumes node positions start
          from the node graph's (0, 0) point

    Args:
        input_node (nuke.Node): Starting node
        skip_hidden (bool): If True, skip moving any inputs that are hidden

    Returns: None
    """
    v_offsets = {
        "Constant": 100,
        "Read": 100
    }

    xpos = input_node.xpos()
    ypos = input_node.ypos()

    x_offset = 0
    for dep in input_node.dependencies():
        # Determine new position
        xpos += x_offset
        dep.setXYpos(xpos, ypos - v_offsets.get(dep.Class(), 50))
        # Increase x offset
        x_offset -= 100

        # Skip hidden
        if skip_hidden and dep.knob("hide_input") and \
                dep.knob("hide_input").value():
            continue

        # Recurse
        move_dependencies(dep)


def copy_node(node):
    """
    Copy input node

    Args:
        node (nuke.Node or str): Input node

    Returns:
        Copied node
    """
    nukescripts.clear_selection_recursive()

    # Get node from name str
    if isinstance(node, str):
        to_copy = nuke.toNode(node)
    else:
        to_copy = node

    if not to_copy:
        raise ValueError("No node named '{0}'".format(node))

    # Select source
    to_copy.knob("selected").setValue(True)

    # Copy
    nuke.nodeCopy(to_copy.fullName())
    nukescripts.clear_selection_recursive()

    # Paste
    copied_node = nuke.nodePaste(to_copy.fullName())
    nukescripts.clear_selection_recursive()

    return copied_node


def get_latest_version(knob, prefix="v"):
    """
    Get highest available version for node

    Args:
        knob (nuke.Knob): File knob
        prefix (str): Version prefix
                      Defaults to 'v'
    """
    start = knob.value()
    ver_prefix, ver = nukescripts.version_get(start, prefix)
    while True:
        try:
            curr = knob.value()
            ver_prefix, ver = nukescripts.version_get(curr, prefix)
            # Next version
            next_ver = nukescripts.version_set(
                curr, prefix, int(ver), int(ver) + 1)
            knob.setValue(next_ver)
            # Revert
            if not os.path.exists(knob.evaluate()):
                knob.setValue(curr)
                break

            nuke.root().setModified(True)
        except ValueError:
            break

    knob.setValue(start)
    return int(ver)
