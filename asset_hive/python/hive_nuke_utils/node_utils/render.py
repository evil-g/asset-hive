# -*- coding: utf-8 -*-
# Third party
import nuke
import nukescripts

# Pipeline
from . import import_nodes


def setup_scene_render(scene_inputs, camera_path, bg=None, fps=None):
    """
    Set up a Scanline Render or Ray Render for the scene

    Args:
        scene_inputs (list): List of Nuke.Node objs to be scene inputs
        camera_path (str): Path to camera file
        bg (str): Path to background image
        fps (int): Camera fps

    Returns:
        Final Nuke.Node in tree
    """
    scene = nuke.createNode("Scene")

    # Connect obj inputs
    for idx in range(0, len(scene_inputs)):
        scene.setInput(idx, scene_inputs[idx])

    # Set up camera
    camera = import_nodes.camera_geo(camera_path, fps=fps)

    # Render scene
    scene_render_node = nuke.createNode("RayRender")
    scene_render_node.setInput(1, scene)
    scene_render_node.setInput(1, camera)

    return scene_render_node


def set_up_projection(parent, camera, crop=False, fps=None, insert_dot=False):
    """
    Set up Project3D projection

    Args:
        parent (Nuke.Node): Node for Project3D input
        camera (str or nuke.Node): Projection camera path or
                                   projection camera node (or dot)
        crop (bool): Setting for Project3D crop knob
        fps (int): Camera fps
        insert_dot (bool): If True, insert dot between pcam and
                           Project3D camera input

    Returns:
        Nuke.Node
    """
    proj = nuke.createNode("Project3D")
    proj.setInput(0, parent)

    # Create camera node if necessary
    if isinstance(camera, str):
        camera = import_nodes.camera_geo(camera, fps=fps)

    # Insert dots between camera + projection node
    if insert_dot:
        nukescripts.clear_selection_recursive()
        dot = nuke.createNode("Dot", "name pcam hide_input True")
        dot.setInput(0, camera)
        proj.setInput(1, dot)
    else:
        proj.setInput(1, camera)

    # Set crop
    proj.knob("crop").setValue(crop)

    return proj
