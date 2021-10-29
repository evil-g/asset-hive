# -*- coding: utf-8 -*-
# Third party
from nukescripts import panels

# Package
import asset_hive


# Dockable panel
panels.registerWidgetAsPanel("asset_hive.ui.AssetHiveWindow",
                             "Asset Hive",
                             "uk.co.thefoundry.AssetHive")
