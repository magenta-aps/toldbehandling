from typing import Any, Dict, Iterable


def filter_dict_values(data: Dict[Any, Any], values_to_trim: Iterable):
    return dict(filter(lambda pair: pair[1] not in values_to_trim, data.items()))


def filter_dict_none(data: Dict[Any, Any]):
    return filter_dict_values(data, (None,))


# Copied from core python because its containing module `distutils` is deprecated.
def strtobool(val):
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return 1
    elif val in ("n", "no", "f", "false", "off", "0"):
        return 0
    else:
        raise ValueError("invalid truth value %r" % (val,))
