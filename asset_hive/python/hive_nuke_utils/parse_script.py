# Standard
import re


def parse_node_classes(script):
    """
    Get node classes used by a script

    Args:
        script (str): Script path

    Returns:
        List of node Class strs
    """
    classes = []
    with open(script, 'r') as handle:
        for line in handle.readlines():
            match = re.match("(?P<class>^.*)\ \{\\n$", line)
            if match:
                classes.append(match.group("class"))

    return list(set(classes))
