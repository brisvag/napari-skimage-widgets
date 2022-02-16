import pytest
from magicgui import magicgui
from skimage import filters

from napari_skimage_widgets.annotate import annotate_module


@pytest.mark.parametrize("function", list(annotate_module(filters).values()))
def test_widgets(function):
    magicgui(function)
