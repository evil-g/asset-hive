# -*- coding: utf-8 -*-
# Standard
from __future__ import division
from __future__ import print_function
from builtins import range
from past.utils import old_div
from glob import glob
import json
import os
import math

# Third party
import nuke
import nukescripts

# Pipeline
from core_pipeline import logger
from core_pipeline.utils import frame_utils
from core_pipeline.utils import path_utils
from nuke_utils.nodes import timesheet_io
from . import node_ops


# Globals
LOG = logger.get_logger("nuke_utils.nodes.import_nodes")
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
        print("Warning! Missing start or end frame key in shake json. " \
              "Defaulting to Nuke script frame range.")
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


def import_large_transform(paninfo_path, info_path):
    """
    Import transform and shake for a large image

    large_transform, large_shake nodes are created.
    These nodes are supposed to be connected as follows:
    large image -> large_shake -> large_transform -> merge A input

    Args:
        paninfo_path (str): JSON paninfo file path (paninfo_vXXX.json)
        info_path (str): JSON shake info file path
    Returns:
        (nuke.Node, nuke.Node): tuple of shake transform, large transform
    """

    with open(paninfo_path, 'r') as fp:
        pi_dat = json.load(fp)

    with open(info_path, 'r') as fp:
        dat = json.load(fp)

    #print(pi_dat)
    #print(dat)

    x_res = dat['proj_resolution_x']
    y_res = dat['proj_resolution_y']
    x_large_res, y_large_res = pi_dat['large_resolution']

    # Create Transforms
    shake_trans = nuke.createNode("Transform")
    shake_trans.knob('label').setValue('Large Shake')

    trans = nuke.createNode("Transform")
    trans.knob('label').setValue('Large Transform')
    trans.setInput(0, shake_trans)

    #-------------------------------------------
    # Setup large transform
    trans.knob("center").setValue((x_large_res*0.5, y_large_res*0.5))
    trans_x = pi_dat['film_trans_h']
    trans_y = pi_dat['film_trans_v']
    roll = pi_dat['film_roll']
    scale = pi_dat['film_scale']
    large_trans_x = pi_dat['large_film_trans_h']
    large_trans_y = pi_dat['large_film_trans_v']

    large_aperture_h = pi_dat['large_film_aperture_h']
    aperture_h = dat['film_aperture_h']

    attr_list = ['translate', 'rotate', 'scale', 'center']
    for attr in attr_list:
        trans.knob(attr).setAnimated(0)
        trans.knob(attr).setAnimated(1)


    curve_x = trans.knob("translate").animations()[0]
    curve_y = trans.knob("translate").animations()[1]
    curve_cx = trans.knob("center").animations()[0]
    curve_cy = trans.knob("center").animations()[1]
    curve_roll = trans.knob("rotate").animations()[0]

    trans.knob("scale").setSingleValue(True)
    curve_scale = trans.knob("scale").animations()[0]

    start, end = pi_dat['frame_range']


    # film translate: centerを移動する.
    # film roll: 回転量を反転
    # film scale: 逆数に変換.(jsonファイルに出力された値は, filmの矩形に対してのスケール値なので、mayaのpostScale値の逆数)
    #        mayaのpostScaleとnukeのtransformのscaleは画像の拡縮として同一.

    #
    # 分かりにくい注意点としてfilm translate, scaleは下記の補正が必要.

    # 2D Cameraのpixelの密度(ここでは(resolution width) / (aperture width)と定義する)は、大判カメラのpixel密度が異なる
    # (2D Cameraと大判カメラのfocal lengthが一致していることが前提である)
    #
    # そのため2D Cameraで10pixel移動することと大判の画像を10pixel分移動することは意味が異なる。
    # publish時の大判の解像度の最適化処理の結果、2DPanカメラが最もZoomしたとき(flim scaleが最小値)のpixel密度が大判カメラのpixel密度と一致する.
    #
    # 最もzoomしたときのfilm scaleをmin_scaleと定義すると, 下記の式が成り立つ
    # (x_large_res) / (large_aperture_h) == (x_res) / ((min_scale) * (aperture_h))

    # (min_scale) * (aperture_h) * (large_res_x) == (res_x) * (large_aperture_h)
    # (min_scale) := ((res_x) / (large_res_x)) * ((large_aperture_h) / (aperture_h))

    #
    # このmin_scaleの値の逆数をfilm translateに乗算した値で大判画像を移動する
    # 大判画像に適用するscale値にも同様の変換が必要. 最もzoomした時には、大判画像はスケールされない.
    min_scale = (old_div(x_res, x_large_res)) * (old_div(large_aperture_h, aperture_h))

    for frame in range(start, end):
        idx = frame - start

        # scale
        s = old_div(min_scale, scale[idx])

        # translate
        # x = x_large_res*0.5, y = y_large_res*0.5の時大判の中心と2DPan画像の中心が一致
        x = x_large_res*0.5 - x_large_res*0.5*large_trans_x + (trans_x[idx] * x_res * 0.5 * (1.0 / min_scale))
        y = y_large_res*0.5 - x_large_res*0.5*large_trans_y + (trans_y[idx] * x_res * 0.5 * (1.0 / min_scale)) # yのfilm translateはhorizontal apertureで正規化されている

        # centerを移動する点に注意(AEのanchor point)
        # 2DPan画像の中心と大判のcenterが一致している必要がある
        # 2DPanの拡大縮小、回転は2DPan画像の中心. 大判画像の拡大縮小も同一の座標を中心に行う必要がある
        curve_cx.setKey(frame, x)
        curve_cy.setKey(frame, y)

        # Large画像のcenterが2DPan画像の中心となるように補正する
        curve_x.setKey(frame, -x+0.5*x_res)
        curve_y.setKey(frame, -y+0.5*y_res)

        curve_roll.setKey(frame, - roll[idx])
        curve_scale.setKey(frame, s)


    #-------------------------------------------
    # Setup large shake transform
    shake_trans.knob('translate').setAnimated(0)
    shake_trans.knob('translate').setAnimated(1)

    shake_xy = dat['shake_values']

    shake_curve_x = shake_trans.knob("translate").animations()[0]
    shake_curve_y = shake_trans.knob("translate").animations()[1]

    for frame in range(start, end):
        idx = frame - start
        shake_curve_x.setKey(frame, old_div((shake_xy[idx][0]*x_res*0.5), min_scale))
        shake_curve_y.setKey(frame, old_div((shake_xy[idx][1]*x_res*0.5), min_scale))

    # Large Image -> large_shake -> large_transformの順で接続

    return shake_trans, trans


def camera_shake(path, resolution=None, is_offset=False, rolls=None, scales=None, large=False):
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
        print("Warning! Missing start or end frame key in shake json. " \
              "Defaulting to Nuke script frame range.")
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
    if not large:
        trans = create_keyed_transform(
            data["shake_values"], start, end, h_aperture, v_aperture, resolution,
            is_offset=is_offset, scales=scales)
    else:
        # The shake paramter is derived from camera filme translate
        # So, the shake paramter is already normalized by horizontal film aperture.
        # vertical shake is also normalized by horizontal film aperture.
        trans = create_keyed_transform(
            data["shake_values"], start, end, 1.0, 1.0, (0.5*proj_x_res, 0.5*proj_x_res),
            is_offset=is_offset, rolls=rolls, scales=scales)

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
                           rolls=None, scales=None):
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
            input = next(pixel_iter)
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

        if rolls:
            if isinstance(rolls, list):
                roll = - math.radians(rolls[frame - start])
            else:
                roll = - math.radians(rolls)
            x_shake0 = math.cos(roll) * x_shake - math.sin(roll) * y_shake
            y_shake0 = math.sin(roll) * x_shake + math.cos(roll) * y_shake

            x_shake = x_shake0
            y_shake = y_shake0

        if scales:
            if isinstance(scales, list):
                x_shake = scales[frame - start] * x_shake
                y_shake = scales[frame - start] * y_shake
            else:
                x_shake = scales * x_shake
                y_shake = scales * y_shake

        if debug:
            print("Setting key: {0} ({1}, {2})".format(input, x_shake, y_shake))

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
    nuke.nodePaste(path)  # (Resolves expressions with new node names)

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


def read(path, start=None, end=None, format=None, node_class=None):
    """
    Create a Read node for the given path

    Args:
        path (str): Filepath or directory path
        start (int, optional): Start frame
        end (int, optional): End frame
        format (nuke.Format, optional): Format to set for Read
                                        Defaults to nuke.Root.format
        node_class (str): Node class. Defaults to 'Read'

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
        files = [f for f in files if not f.startswith(".") and os.path.isfile(
            os.path.join(parent_dir, f))]
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
    # Force class
    if node_class:
        LOG.debug("Using input node_class: {0}".format(node_class))
        try:
            read = nuke.createNode(node_class, "file {%s}" % path)
        # Invalid input type
        except TypeError:
            raise TypeError("Invalid node_class arg type: {0}, type '{1}'"
                            "".format(node_class, type(node_class)))
        # Invalid node class
        except RuntimeError:
            raise RuntimeError("Invalid node class: {0}".format(node_class))
    # Default - start with Read
    else:
        read = nuke.createNode("Read", "file {%s}" % path)
        # Check exr type
        # TODO Add OpenExr support
        try:
            if ".exr" == os.path.splitext(path)[-1]:
                # Note:
                #   1. If you read a deepscanline into a Read node,
                #      the exr metadata will not accessible immediately.
                #      So, in the abscence of metadata, we will switch
                #      to a DeepRead node.
                #   2. `nuke.toNode(read.fullName())` must be used here
                #       to access the metadata. If `read.metadata()` is used,
                #       it returns `[]` even if there is metadata present.
                exr_type = nuke.toNode(read.fullName()).metadata().get(
                    "exr/type", "")
                LOG.debug(
                    "Checking exr scanline type... '{0}'".format(exr_type))
                if not exr_type or "deepscanline" == exr_type:
                    deep = nuke.createNode("DeepRead", "file {%s}" % path)
                    deep_type = nuke.toNode(
                        deep.fullName()).metadata().get("exr/type")
                    LOG.debug("Checking deep scanline type... '{0}'".format(
                        deep_type))
                    if not deep_type or "deepscanline" == deep_type:
                        nuke.delete(read)
                        read = nuke.toNode(deep.fullName())
                    else:
                        nuke.delete(deep)
        except IndexError:
            LOG.warning("Failed to splitext on input image", exc_info=True)
            LOG.warning("Skipping DeepRead check...")

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
                print(item, shape)
                if item not in matches:
                    if item.endswith(shape):
                        matches.append(item)
                    # Check shapes provided in Maya-style
                    # Ex: (|book01|book0Shape1)
                    else:
                        split_shape = [_f for _f in shape.split("|") if _f][-1]
                        print(split_shape)
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

    if not os.path.isfile(path):
        raise ValueError("Flicker removal file '{0}' does not exist!"
                         "".format(path))

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
    if not os.path.isfile(path):
        raise ValueError("Lightanchor file '{0}' does not exist!"
                         "".format(path))

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
    for knob, path in node_ops.get_node_files(write).items():
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


def create_postage_stamp(node=None):
    """
    Create postage stamp from input node

    Args:
        node (nuke.Node): Input node

    Returns:
        New stamp node
    """
    node = node or nuke.selectedNode()
    if not node:
        raise ValueError("No input node or selected node found!")

    nukescripts.clear_selection_recursive()

    # Create and connect postage stamp
    stamp = nuke.createNode("PostageStamp")
    stamp.setInput(0, node)
    stamp.setXYpos(node.xpos() + 50, node.ypos() + 50)

    return stamp


def create_topnode_postage_stamp(node=None):
    """
    Create postage stamp to topnode

    Args:
        node (nuke.Node): Input node

    Returns:
        New stamp node
    """
    stamp = create_postage_stamp(node)
    stamp.knob("label").setValue("[value [topnode].name]")
    return stamp


def create_input_postage_stamp(node=None):
    """
    Create postage stamp to input0

    Args:
        node (nuke.Node): Input node

    Returns:
        New stamp node
    """
    stamp = create_postage_stamp(node)
    stamp.knob("label").setValue("[value this.input0.label]")
    return stamp
