#!/usr/bin/env python3

import skimage.filters

from napari_skimage_widgets.annotate import gather_functions

TEMPLATE = """name: napari-skimage-widgets
display_name: skimage widgets
contributions:
  commands:{commands}
  widgets:{widgets}"""

COMMAND = """
    - id: napari-skimage-widgets.{name}
      python_name: napari_skimage_widgets.plugin:{name}
      title: Create skimage.{name} widget"""

WIDGET = """
    - command: napari-skimage-widgets.{name}
      display_name: {name} filter"""


names = gather_functions(skimage.filters).keys()

commands = []
widgets = []
for name in names:
    commands.append(COMMAND.format(name=name))
    widgets.append(WIDGET.format(name=name))

print(TEMPLATE.format(commands="".join(commands), widgets="".join(widgets)))
