# -*- coding: utf-8 -*-
# Standard
from glob import glob
import json
import os

# Third party
import nuke
import nukescripts

# Pipeline
from core_pipeline.utils import frame_utils
from core_pipeline.utils import path_utils
from nuke_utils.nodes import timesheet_io
from . import node_ops


# Globals
# Class map for asset type and Nuke Node Class
# that should be used for asset import
IMPORT_CLASS_MAP = {
    "geo": ["Camera2"],
    "shake": ["Transform"]
}

TYPE_KNOB = "type"


def audio_read(path):
    """
    Import audio read

    Args:
        path (str): Audio path

    Returns:
        Nuke Node
    """
    # Load camera shake data
    if not os.path.isfile(path):
        raise ValueError("Audio file '{0}' does not exist!"
                         "".format(path))

    # Create AudioRead
    audio = nuke.createNode("AudioRead")
    audio.knob("file").setValue(path)
    audio.knob("label").setValue(os.path.basename(path))

    return audio


def camera_geo(path, fps=None, read_from_file=False):
    """
    Import a camera

    Args:
        path (str): Camera filepath
        fps (int): Camera frame rate

    Returns:
        Camera node
    """
    # Load camera
    if not os.path.isfile(path):
        raise ValueError("Camera file '{0}' does not exist!"
                         "".format(path))

    camera = nuke.createNode("Camera2", "read_from_file true file {%s}" % path)
    camera.knob("suppress_dialog").setValue(True)

    nuke.tprint("init", camera.knob("haperture").value(),
                camera.knob("vaperture").value())
    # Nuke bug... :/
    # if ".fbx" == os.path.splitext(path)[-1]:
    camera.knob("read_from_file").setValue(True)
    nuke.show(camera)

    # Set to root fps setting as default
    camera.forceValidate()
    if fps is None:
        camera.knob("frame_rate").setValue(nuke.root().fps())
    else:
        camera.knob("frame_rate").setValue(fps)

    # If we imported an FBX, try to set the node name to 'camera'
    # (Do because FBX nodes from MotionBuilder have 'Producer' cameras.
    #  When importing through UI, the default is 'camera', but through a
    #  nuke -t script the first node name is selected, even when forceValidate
    #  is executed. So, we double check it here.)
    if camera.knob("fbx_node_name"):
        camera.knob("fbx_node_name").setValue("camera")

        if "camera" != camera.knob("fbx_node_name").value():
            nuke.tprint("Warning! Failed to set 'camera' fbx node.")

    nuke.tprint("final", camera.knob("haperture").value(),
                camera.knob("vaperture").value())

    return camera


def apply_2dpan(camera, path, settings, fps=None):
    """
    Apply pan data to the given camera node
    """
    # Load camera shake data
    if not os.path.isfile(path):
        raise ValueError("Camera 2dpan file '{0}' does not exist!"
                         "".format(path))

    with open(path, "r") as handle:  # TODO Catch OSError?
        data = json.load(handle)

    # Get animation range for the camera shake
    frange = data.get("frame_range", [])
    try:
        start, end = frange
    except ValueError:
        start = None
        end = None

    # Default to root frame range if start or end key is missing
    if start is None or end is None:
        print "Warning! Missing start or end frame key in shake json. " \
              "Defaulting to Nuke script frame range."
        start = int(nuke.root().knob("first_frame").value())
        end = int(nuke.root().knob("last_frame").value())

    # Get pan keys
    pan_keys = []

    h_pan = data["film_trans_h"]
    v_pan = data["film_trans_v"]
    for idx in range(0, len(h_pan)):
        try:
            pan_keys.append([h_pan[idx], v_pan[idx]])
        except IndexError:
            raise ValueError("Frames missing! Pan horizontal and vertical "
                             "info are out of sync")

    nuke.tprint("pre validate", camera.knob("haperture").value(),
                camera.knob("vaperture").value())
    camera.forceValidate()
    nuke.tprint("post validate", camera.knob("haperture").value(),
                camera.knob("vaperture").value())
    # Turn file read off
    camera.knob("read_from_file").setValue(False)

    # Key for each entry in the pan data
    # H + V pan
    node_ops.key_knob(camera.knob("win_translate"), pan_keys, start, end)
    # Scale
    node_ops.key_knob(camera.knob("win_scale"), data["film_scale"], start, end)
    # Roll
    node_ops.key_knob(camera.knob("winroll"), data["film_roll"], start, end)

    nuke.tprint("post key", camera.knob("haperture").value(),
                camera.knob("vaperture").value())

    return camera


def camera_shake(path, resolution=None, is_offset=False, scales=None):
    """
    Apply camera shake data to a Transform Node

    Args:
        path (str): JSON file path containing camera shake data
        resolution (tuple): Resolution tuple (width, height)
        is_offset (bool): If True, treat transforms as actual pixel offset
                          (don't calculate with using camera attrs)

    Returns:
        Transform Node
    """
    # Load camera shake data
    if not os.path.isfile(path):
        raise ValueError("Camera shake file '{0}' does not exist!"
                         "".format(path))

    with open(path, "r") as handle:  # TODO Catch OSError?
        data = json.load(handle)

    # Get animation range for the camera shake
    start = data.get("start_frame")
    end = data.get("end_frame")

    # Default to root frame range if start or end key is missing
    if start is None or end is None:
        print "Warning! Missing start or end frame key in shake json. " \
              "Defaulting to Nuke script frame range."
        start = int(nuke.root().knob("first_frame").value())
        end = int(nuke.root().knob("last_frame").value())

    # Get aperture
    h_aperture = data.get("film_aperture_h")
    v_aperture = data.get("film_aperture_v")

    if not h_aperture or not v_aperture:
        raise ValueError("Shake JSON is missing h + v aperture values.")

    # Try to use res values from shake json
    proj_x_res = data.get("proj_resolution_x")
    proj_y_res = data.get("proj_resolution_y")
    if proj_x_res and proj_y_res:
        resolution = (proj_x_res, proj_y_res)

    # Create transform
    trans = create_keyed_transform(
        data["shake_values"], start, end, h_aperture, v_aperture, resolution,
        is_offset=is_offset, scales=scales)
    # Show JSON basename on label
    trans.knob("label").setValue("Shake\n" + os.path.basename(path))

    # Add knob with source file path
    node_ops.add_anima_file_knob(trans, path)
    node_ops.add_text_knob(trans, TYPE_KNOB, "camera shake")

    # Focus first tab
    trans.knob("translate").setFlag(0)

    # Turn off black outside
    trans.knob("black_outside").setValue(False)

    return trans


def create_keyed_transform(transforms, start, end, h_aperture, v_aperture,
                           resolution=None, debug=False, is_offset=False,
                           scales=None):
    """
    Create a Transform Node and apply the provided camera shake values

    Args:
        transforms (list): List of [x, y] transform values
        start (int): Start frame
        end (int): End frame
        h_aperture (float): Camera horizontal aperture
        v_aperture (float): Camera vertical aperture
        resolution (tuple): Resolution tuple (width, height)
        debug (bool): Print each keyframe that is set
        is_offset (bool): If True, treat transforms as actual pixel offset
                          (don't calculate with using camera attrs)

    Returns:
        Transform Node
    """
    # Get resolutions
    try:
        x_res, y_res = resolution
    # Default to root resolution
    except TypeError:
        fmt = nuke.root().format()
        x_res = fmt.width()
        y_res = fmt.height()

    # Transform
    trans = nuke.createNode("Transform")

    # Set as animated
    trans.knob("translate").setAnimated(0)
    trans.knob("translate").setAnimated(1)
    # Get anim curves
    animations = trans.knob("translate").animations()
    anim_x_curve = animations[0]
    anim_y_curve = animations[1]

    # Apply shake data for each camera
    pixel_iter = iter(transforms)
    for frame in range(start, end):
        # Get next shake list
        try:
            input = pixel_iter.next()
        except StopIteration:
            raise ValueError("Shake data is missing entries for frames in"
                             "{0}-{1}".format(start, end))

        # Get keyframe setting
        # Offset pixels are given
        if is_offset:
            x_shake = float(input[0])
            y_shake = float(input[1])
        # Calculate offset pixels
        else:
            x_shake = (float(input[0]) / h_aperture) * x_res
            y_shake = (float(input[1]) / v_aperture) * y_res

        if scales:
            if isinstance(scales, list):
                x_shake = scales[frame - start] * x_shake
                y_shake = scales[frame - start] * y_shake
            else:
                x_shake = scales * x_shake
                y_shake = scales * y_shake

        if debug:
            print "Setting key: {0} ({1}, {2})".format(input, x_shake, y_shake)

        # Set keys
        anim_x_curve.setKey(frame, x_shake)
        anim_y_curve.setKey(frame, y_shake)

    return trans


def nukescript(path, backdrop=False):
    """
    Import a Nuke script and place it on a backdrop

    Args:
        path (str): Path to nukescript
        backdrop (bool): Apply backdrop
                         Defaults to False

    Returns:
        Backdrop node for imported nukescript or list of nodes
    """
    if not os.path.isfile(path):
        raise RuntimeError("Cannot import nukescript. File is missing:"
                           "{0}".format(path))

    # Clear selection
    nukescripts.clear_selection_recursive()
    # Existing nodes
    pre_nodes = nuke.allNodes(recurseGroups=True)

    # Import
    nuke.scriptReadFile(path)

    # Newly imported nodes
    post_nodes = nuke.allNodes(recurseGroups=True)
    new_nodes = set(post_nodes) - set(pre_nodes)

    # Add backdrop
    if backdrop:
        return [node_ops.add_backdrop(new_nodes)]

    # Otherwise, return nodes
    return new_nodes


def published_nk(path, backdrop=True):
    """
    Import a published Nuke script


    Args:
        path (str): Path to published .nk file
        backdrop (bool): Whether to add a backdrop
                         Defaults to True
    """
    nodes = nukescript(path, backdrop=backdrop)

    # Set title and label
    if nodes and backdrop:
        nodes[0].knob("label").setValue("Published Nuke Script:\n{0}"
                                        "".format(os.path.basename(path)))

        # Add anima file knob
        node_ops.add_anima_file_knob(nodes[0], path)

    return nodes


def read(path, start=None, end=None, format=None):
    """
    Create a Read node for the given path

    Args:
        path (str): Filepath or directory path
        start (int, optional): Start frame
        end (int, optional): End frame
        format (nuke.Format, optional): Format to set for Read
                                        Defaults to nuke.Root.format

    Returns:
        Read Node
    """
    # Is a file is provided, just import it
    if not os.path.isfile(path):
        # If we get a directory, glob all files in it and use
        if os.path.isdir(path):
            parent_dir = path
            files = os.listdir(path)
        # Otherwise, assume path is a padded style filepath
        # Eg: 'test.####.exr', 'test.%04d.exr'
        else:
            parent_dir = os.path.dirname(path)
            target_ext = os.path.splitext(path)[-1]

            # Try glob
            try:
                files = glob(frame_utils.get_sequence_path(path))
            # Try listdir
            except Exception:
                # Note: Can't always glob bc basename may not be the same
                #       For now, filter out any bad exts, etc
                files = [f for f in os.listdir(parent_dir)]

            # Filter out bad ext
            files = [f for f in files if f.endswith(target_ext)]

            # No files, or ext is different :/
            # Fall back on entire directory
            if not files:
                files = os.listdir(parent_dir)

        # Remove hidden files
        files = filter(lambda f: not f.startswith("."), files)
        files.sort()

        # No files found
        if not files:
            raise RuntimeError("Failed to import read - no files found:\n{0}"
                               "".format(path))

        # For .mov files, skipping padding
        if 1 == len(files) and files[0].endswith(".mov"):
            path = os.path.join(parent_dir, files[0])
        # Get padded filepath
        else:
            # Frame range
            if not start and start != 0:
                start = frame_utils.frame_from_file(files[0])
            if not end and end != 0:
                end = frame_utils.frame_from_file(files[-1])

            # Get full filename path
            try:
                path = frame_utils.padded_filepath(os.path.join(
                    parent_dir, files[0]))
            except TypeError:
                raise RuntimeError("Failed to import read - there are "
                                   "multiple image sequences in '{0}'"
                                   "".format(path))

    # Create node
    read = nuke.createNode("Read", "file {%s}" % path)

    # Set frame range
    if start or start == 0:
        read.knob("first").setValue(int(start))
        read.knob("origfirst").setValue(int(start))
    if end or end == 0:
        read.knob("last").setValue(int(end))
        read.knob("origlast").setValue(int(end))

    # Set format
    if format:
        read.knob("format").setValue(format)

    return read


def read_geo(path, shapes=None, animated=False):
    """
    Create and return a ReadGeo node

    Args:
        path (str): Path to geo
        shapes (list): List of shape names to import and select on node

    Returns:
        Nuke.Node
    """
    # Create node without scene selection dialog
    read_geo = nuke.createNode("ReadGeo2", "file {%s}" % path)
    # Foundry Nuke Bug 308781
    # When a ReadGeo node is created pythonically, abc items are not
    # automatically loaded and getAllItems returns ['------- '] :/
    # This bug is still present as of Nuke 11.1v1
    # Current workaround is to force validate the node here.
    read_geo.forceValidate()

    scene_view = read_geo.knob("scene_view")
    # Not an abc
    if not scene_view:
        return read_geo

    # Get all items in .abc
    all_items = scene_view.getAllItems()

    # Only import provided
    if shapes:
        matches = []
        for shape in shapes:
            for item in all_items:
                print item, shape
                if item not in matches:
                    if item.endswith(shape):
                        matches.append(item)
                    # Check shapes provided in Maya-style
                    # Ex: (|book01|book0Shape1)
                    else:
                        split_shape = filter(None, shape.split("|"))[-1]
                        print split_shape
                        if item.endswith(split_shape):
                            matches.append(item)
        # print "*********************"
        # print "Shapes", shapes
        # print "Matches", matches
        # print "*********************"
        scene_view.setImportedItems(matches)
        scene_view.setSelectedItems(matches)
    # Import and select all
    # (There is a Nuke bug with this so we have to do it manually)
    else:
        scene_view.setImportedItems(all_items)
        scene_view.setSelectedItems(all_items)

    # TODO Move this above so it applies to fbx
    # If geo is not animated, don't read every frame
    read_geo.knob("read_on_each_frame").setValue(animated)
    # TODO Specify lock frame here?

    # Always turn off subframe
    read_geo.knob("sub_frame").setValue(False)

    return read_geo


def timesheet(path):
    """Create TimeWarp for TimeSheet
    Args:
        path(string): file path
    """
    node = timesheet_io.import_timesheet_text(path, allow_duplicates=True)

    return node


def read_flicker_removal(path):
    """ Read a given fbx file for eliminating the flicker effect generated by the step animation.
    """
    path = path_utils.normalize(path)
    # name = "RmFlickerAxis_" + namespace

    # axis_node = nuke.toNode(name)
    # if axis_node is None:
    #     axis_node = nuke.createNode("Axis2", "read_from_file true file {}".format(path))
    #     axis_node.setName(name)

    axis_node = nuke.createNode("Axis2", "read_from_file true file {}".format(path))
    # axis_node["file"].setValue(path)

    return axis_node


def flicker_removal(path, width, height):
    """Create Axis and Transform for flicker removal
    Args:
        path(string): fbx path (flicker removal)
        width(int): image width
        height(int): image height
    """
    # axis_node = read_flicker_removal(path, namespace)
    path = path_utils.normalize(path)
    axis_node = nuke.createNode("Axis2", "read_from_file true file {}".format(path))

    # trs_name = "RmFlickerOffset_" + namespace
    # trs_node = nuke.toNode(trs_name)
    #
    # if not trs_node:
    #     trs_node = nuke.createNode("Transform")
    #     trs_node.setName(trs_name)

    half_w = width * 0.5
    half_h = height * 0.5

    trs_node = nuke.createNode("Transform")
    trs_node.knob("center").setValue([half_w, half_h])
    trs_node.knob("translate").setExpression(
        "-{}.translate.x * {}".format(axis_node.name(), half_w), 0)
    trs_node.knob("translate").setExpression(
        "-{}.translate.y * {}".format(axis_node.name(), half_w), 1) # note: do not multiply the aspect ratio
    trs_node.knob("rotate").setExpression(
        "{}.rotate.z".format(axis_node.name()))
    trs_node.knob("scale").setExpression(
        "{}.scaling.x".format(axis_node.name()))

    return trs_node


def light_anchor(path):
    """Create Axis and Transform for LightAnchor
    Args:
        path(string): fbx path (flicker removal)
    """
    path = path_utils.normalize(path)
    axis_node = nuke.createNode("Axis2", "read_from_file true file {}".format(path))

    return axis_node


def read_from_write(write):
    """
    Create a read for a Write node's path

    Args:
        write (nuke.Node): Nuke node

    Returns:
        List of created nodes
    """
    x = write.xpos()
    y = write.ypos() + 100
    created = []

    # Read each file path
    for knob, path in node_ops.get_node_files(write).iteritems():
        read_node = read(path)

        # Set position
        read_node.setXYpos(x, y)

        # Next x pos
        x += 100

        created.append(read_node)

    return created


def reads_from_writes(writes=None):
    """
    Read from write for each node

    Args:
        writes (list): List of Write nodes to created Read for

    Raises:
        RuntimeError if no Write

    Returns: None
    """
    if writes is None:
        writes = nuke.selectedNodes()

    if writes is None:
        raise RuntimeError("選択されていないWriteノード！ (Select Write nodes)")

    for write in writes:
        read_from_write(write)
