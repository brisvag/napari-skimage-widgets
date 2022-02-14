from magicgui import magic_factory

from .annotate import annotate_module


def _generate_widgets():
    opts = dict(auto_call=True)
    return {
        name: magic_factory(func, **opts)
        for name, func in annotate_module("skimage.filters").items()
    }


_widgets = _generate_widgets()

__all__ = list(_widgets)


def __getattr__(name):
    if name in __all__:
        return _widgets[name]
    raise AttributeError(name)
