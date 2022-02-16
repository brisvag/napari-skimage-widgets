import builtins
import inspect
import re
from ast import literal_eval
from enum import Enum
from functools import wraps
from types import FunctionType

from docstring_parser import parse
from typing_extensions import Annotated


class BoundaryMode(Enum):
    reflect = "reflect"
    constant = "constant"
    nearest = "nearest"
    mirror = "mirror"
    warp = "warp"


HIDDEN = {"skimage.filters._median.median": {"behavior"}}

BIND_DEFAULT = {"output", "out", "cval", "selem"}
NAME_MAP = {
    "data": "napari.types.ImageData",
    "image": "napari.types.ImageData",
    "mask": "napari.types.LabelsData",
}
DOC_TYPE_MAP = {
    "array of bool": "napari.types.ImageData",
    "array": "napari.types.ImageData",
    "ndarray": "napari.types.ImageData",
}

REQUIRED_NO_DEFAULTS = ("image", "kernel", "data")

DEPRECATED = ("multichannel",)  # conflicts with new channel_axis


def gather_functions(module):

    return {
        n: getattr(module, n)
        for n in dir(module)
        if not n.startswith("_")
        if isinstance(getattr(module, n), FunctionType)
    }


def from_builtins(word):
    aliases = {
        "string": "str",
        "boolean": "bool",
        "integer": "int",
        "scalar": "float",
    }
    word = aliases.get(word, word)
    if word in dir(builtins):
        return getattr(builtins, word)


def bound_default(param):
    return Annotated[type(param.default), {"bind": param.default}]


def guess_type(param: inspect.Parameter, doc_type):
    if param.annotation is not param.empty:
        return param.annotation

    if param.name in BIND_DEFAULT:
        return bound_default(param)

    if param.name == "mode":
        return BoundaryMode

    if param.name in NAME_MAP:
        return NAME_MAP[param.name]
    if not doc_type:
        return type(param.default)

    # a couple manual corrections that should be fixed with PRs
    doc_type = doc_type.replace("‘", "")  # filters.median
    doc_type = doc_type.replace("{int, function}", "int or callable")

    _builtin = from_builtins(doc_type.split("or")[0].strip())
    if not _builtin:
        _builtin = from_builtins(doc_type.split(",")[0].strip())
    if _builtin:
        return _builtin

    of_match = re.match(r"(iterable|tuple|sequence|list) of ([^\s]+)", doc_type)
    if of_match:
        import typing

        a, b = of_match.groups()
        container = getattr(typing, a.title())
        type_ = from_builtins(b.rstrip("s"))
        return container[type_]

    if doc_type in DOC_TYPE_MAP:
        return DOC_TYPE_MAP[doc_type]

    if "mask" in param.name:
        return "napari.types.LabelsData"
    if "array of bool" in doc_type:
        return "napari.types.LabelsData"
    if "array" in doc_type:
        return "napari.types.ImageData"

    try:
        val = literal_eval(doc_type)
        if isinstance(val, set):
            return Annotated[str, {"choices": list(val)}]
    except Exception:
        pass

    if param.default is not param.empty:
        return type(param.default)


def guess_return_type(doc):

    if "array of bool" in doc.type_name:
        return "napari.types.LabelsData"
    if doc.type_name in DOC_TYPE_MAP:
        return DOC_TYPE_MAP[doc.type_name]
    if "image" in doc.description:
        return "napari.types.ImageData"
    if "array" in doc.type_name:
        return "napari.types.ImageData"


def annotate_function(function):
    sig = inspect.signature(function)
    doc_params = {p.arg_name: p.type_name for p in parse(function.__doc__).params}
    for k, v in list(doc_params.items()):
        if "," in k:
            for split_key in k.split(","):
                doc_params[split_key.strip()] = v
            del doc_params[k]

    hidden = HIDDEN.get(f"{function.__module__}.{function.__name__}", {})
    params = []
    for p in sig.parameters.values():
        if p.name in DEPRECATED:
            continue
        elif p.name in hidden:
            annotation = bound_default(p)
        else:
            annotation = guess_type(p, doc_params.get(p.name))

        # original functions accept strings, not enums
        if isinstance(annotation, type) and issubclass(annotation, Enum):
            default = annotation(p.default)
        else:
            default = p.default

        if p.name == "channel_axis":
            # TODO: this needs to be nullable for non-channel images!
            pass

        param = inspect.Parameter(
            name=p.name,
            annotation=annotation,
            default=default,
            kind=inspect.Parameter.KEYWORD_ONLY,
        )

        params.append(param)

    doc_returns = parse(function.__doc__).returns
    # Note skimage.filters.inverse has no return doc string
    # Note skimage.filters.threshold should be a different type ....
    if doc_returns is not None:
        return_annotation = guess_return_type(doc_returns)
    else:
        return_annotation = None

    new_sig = sig.replace(parameters=params, return_annotation=return_annotation)

    @wraps(function)
    def wrapper(**kwargs):
        for kw, val in kwargs.items():
            if kw in REQUIRED_NO_DEFAULTS and val is None:
                return
            elif isinstance(val, Enum):
                kwargs[kw] = val.value
        return function(**kwargs)

    wrapper.__signature__ = new_sig

    return wrapper


def annotate_module(module):
    if isinstance(module, str):
        import importlib

        module = importlib.import_module(module)

    functions = gather_functions(module)
    return {fname: annotate_function(func) for fname, func in functions.items()}
