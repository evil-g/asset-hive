# Third party
import nuke

# Pipeline
from . import node_ops


def validate_write(node):
    """
    Verify that a Write node is ready to render

    Args:
        node (Nuke.Node): Write node

    Raises: ValueError if node is not correct
    """
    # Must have inputs
    if not node.inputs():
        raise ValueError("{0} has no inputs! Cancelling!"
                         "".format(node.fullName()))
    # Must have filepath set
    if not node.knob("file").value():
        raise ValueError("Please set a file path for {0}!"
                         "".format(node.fullName()))
    # Must have file type set
    if " " == node.knob("file_type").value():
        raise ValueError("Please set a file type for {0}!"
                         "".format(node.fullName()))


def limit_to_range(node_name, start, end):
    """
    Limit a node to a frame range

    Args:
        node_name (str): Name of node to apply limit to
        start (int): Start frame
        end (int): End frame
    """
    node = nuke.toNode(node_name)
    if not node:
        raise ValueError("Node '{0}' does not exist!"
                         "".format(node_name))

    node.knob("use_limit").setValue(True)
    node.knob("first").setValue(start)
    node.knob("last").setValue(end)


def remove_range_limit(node_name):
    """
    Remove frame range limit on Node

    Args:
        node_name (str): Name of node to clear limit from
    """
    node = nuke.toNode(node_name)
    if not node:
        raise ValueError("Node '{0}' does not exist!"
                         "".format(node_name))

    node.knob("use_limit").setValue(False)


def get_range_limit(node_name):
    """
    Get frame range limit for Node

    Args:
        node_name (str): Name of node to get limit for

    Returns:
        (First, Last) tuple
    """
    node = nuke.toNode(node_name)

    if not node.knob("use_limit") or not node.knob("use_limit").value():
        return (None, None)

    return node_ops.get_node_range(node)
