from magicgui import magic_factory
from napari_plugin_engine import napari_hook_implementation


@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    from .annotate import annotate_module

    opts = dict(auto_call=True)
    return [
        magic_factory(x, **opts) for x in annotate_module("skimage.filters").values()
    ]
