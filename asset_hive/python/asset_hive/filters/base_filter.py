# -*- coding: utf-8 -*-
# Third party
import nukescripts
from Qt import QtCore

# Pipeline
from hive_nuke_utils import node_utils


class HiveFilter(object):
    """
    Base class of hive filter
    """
    # If True, user wants to be notified if a filter match exists
    notify = False
    display_name = "filter"

    def __init__(self):
        """
        Base filter init

        For the filter acceptance test, 'asset' argument type varies
        depending on the controller implementation.

        """
        super(HiveFilter, self).__init__()

    def accepts(self, asset, *args, **kwargs):
        """
        Filter accepts test

        Args:
            asset (misc): Input asset.
        """
        raise NotImplementedError


class PendingVersionUpdate(HiveFilter):
    """
    Show assets that are not at the latest available version
    """
    notify = True
    display_name = "pending updates"

    def accepts(self, asset, *args, **kwargs):
        """
        If asset is not at latest version, return True
        """
        # Current version
        ver_prefix, ver = nukescripts.version.version_get(asset.value(), "v")

        # Latest version
        latest = node_utils.node_ops.get_latest_version(asset)

        # print(asset.node().fullName(), not(int(latest) == int(ver)))
        return not(int(latest) == int(ver))
        # return not asset.is_latest

        # proxy_model = kwargs["proxy_model"]
        # source_row = kwargs["source_row"]
        # source_parent = kwargs["source_parent"]

        # # Compare versions
        # src_model = proxy_model.sourceModel()
        # is_latest = src_model.index(source_row, 1, parent=source_parent).data(QtCore.Qt.DisplayRole) == \
        #     src_model.index(source_row, 2, parent=source_parent).data(QtCore.Qt.DisplayRole)

        # return not is_latest


class UnpublishedAsset(HiveFilter):
    """
    Show assets that are not yet published
    """
    notify = True
    display_name = "not published"

    def accepts(self, asset, *args, **kwargs):
        """
        Check for 'pipeline' dir
        """
        # print("pipeline" in asset.value())
        return "pipeline" not in asset.value()
        # return "pipeline" not in asset.path

        # proxy_model = kwargs["proxy_model"]
        # source_row = kwargs["source_row"]
        # source_parent = kwargs["source_parent"]

        # # Compare versions
        # src_model = proxy_model.sourceModel()
        # return "pipeline" not in src_model.index(
        #     source_row, 4, parent=source_parent).data(QtCore.Qt.DisplayRole)


class TrueFilter(HiveFilter):
    """
    Test True filter
    """
    notify = True
    display_name = "test true"

    def accepts(self, asset, *args, **kwargs):

        return True


class FalseFilter(HiveFilter):
    """
    Test False filter
    """
    notify = True
    display_name = "test false"

    def accepts(self, asset, *args, **kwargs):

        return False
