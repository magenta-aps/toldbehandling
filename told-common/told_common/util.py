from typing import Any, Dict, Iterable


def filter_dict_values(data: Dict[Any, Any], values_to_trim: Iterable):
    return dict(filter(lambda pair: pair[1] not in values_to_trim, data.items()))


def filter_dict_none(data: Dict[Any, Any]):
    return filter_dict_values(data, (None,))
