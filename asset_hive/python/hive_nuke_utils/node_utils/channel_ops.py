# Third party
import nuke

# Pipeline
from . import node_ops


def add_alpha(diffuse, alpha=True, dot=False):
    """
    Create a node tree to add an all white or all black
    alpha channel to a diffuse map

    Args:
        diffuse (str): Path to diffuse map
        alpha (bool): Whether alpha should be white or black
        dot (bool): If True, put a dot under the Read

    Returns:
        Final Nuke node in tree (Shuffle)
    """
    # Load diffuse map
    diff_read = nuke.createNode("Read", "file {%s}" % diffuse)

    # Add dot
    last = None
    if dot:
        last = nuke.createNode("Dot")
        last.setXpos(last.xpos() + node_ops.DOT_OFFSET)
        last.setInput(0, diff_read)

    # If diffuse already has an alpha, use it
    if "rgba.alpha" in diff_read.channels():
        return last or diff_read

    shuffle_alpha = nuke.createNode("Shuffle")

    for knob in ["red", "green", "blue"]:
        shuffle_alpha.knob(knob).setValue(knob)

    if alpha:
        shuffle_alpha.knob("alpha").setValue("white")
    else:
        shuffle_alpha.knob("alpha").setValue("black")

    return shuffle_alpha


def merge_diff_alpha(diffuse, alpha, dot=False):
    """
    Create a node tree to output a diffuse/alpha map
    pair as a single set of channels

    Args:
        diffuse (str): Path to diffuse map
        alpha (str): Path to alpha map
        dot (bool): If True, put a dot under the Reads

    Returns:
        Final Nuke node in tree (ShuffleCopy)
    """
    # Load diffuse map
    diff_read = nuke.createNode("Read", "file {%s}" % diffuse)
    # Add dot
    diff_dot = None
    if dot:
        diff_dot = nuke.createNode("Dot")
        diff_dot.setXpos(diff_dot.xpos() + node_ops.DOT_OFFSET)
        diff_dot.setInput(0, diff_read)

    # TODO Diffuse already has an alpha! (Abandon?)
    if "rgba.alpha" in diff_read.channels():
        pass

    # Load alpha map
    alpha_read = nuke.createNode("Read", "file {%s}" % alpha)
    # Add dot
    alpha_dot = None
    if dot:
        alpha_dot = nuke.createNode("Dot")
        alpha_dot.setXpos(alpha_dot.xpos() + node_ops.DOT_OFFSET)
        alpha_dot.setInput(0, alpha_read)

    # Set up tree to merge alpha and diffuse maps
    shuffle_alpha = nuke.createNode("Shuffle")

    # Shuffle Red to alpha, with RGB at black
    for knob in ["red", "green", "blue"]:
        shuffle_alpha.knob(knob).setValue("black")
    shuffle_alpha.knob("alpha").setValue("red")

    # Connect to alpha read
    shuffle_alpha.setInput(0, alpha_dot or alpha_read)

    # ShuffleCopy to get all 4 channels
    shuffle_copy = nuke.createNode("ShuffleCopy")

    # Keep diffuse map RGB
    shuffle_copy.knob("in2").setValue("alpha")
    for knob in ["red", "green", "blue"]:
        shuffle_copy.knob(knob).setValue(knob)
    shuffle_copy.knob("alpha").setValue("alpha2")

    shuffle_copy.setInput(1, diff_dot or diff_read)
    shuffle_copy.setInput(0, shuffle_alpha)

    return shuffle_copy


def create_merge():
    """
    Create default merge node
    """
    merge = nuke.createNode("Merge2")
    merge.knob("operation").setValue("over")

    return merge
