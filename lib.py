# Daniel's personal helpers, shared across every company folder — the
# grown-up sibling of scratch.py. Problem files just write
# `from lib import ...` (uv installs this module into the venv), so helpers
# added below are available to all current and future prep sets.


def run_test_cases(test_cases: list[list], run_specific: int | None = None):
    """My own quick inline checks for a problem file's __main__ block.

    Each scenario is a list whose first entry constructs the instance —
    (ClassName, init_args_tuple), or bare ClassName when __init__ takes
    nothing — followed by (method_name, args, expected) steps run against
    that instance. Bare single args don't need a tuple. A step may also be
    (method_name, args, kwargs, expected) when the method needs keyword
    arguments (e.g. keyword-only params like now=).
    """
    for index, (head, *steps) in enumerate(test_cases):
        if run_specific is not None and index != run_specific:
            continue
        cls, init_args = head if isinstance(head, tuple) else (head, ())
        instance = cls(*init_args)
        print(f"Test Case {index + 1}: {cls.__name__}{init_args}")
        for method, args, *rest in steps:
            kwargs, expected = rest if len(rest) == 2 else ({}, rest[0])
            if not isinstance(args, tuple):
                args = (args,)
            call = f"{method}{args}" + (f" with {kwargs}" if kwargs else "")
            print(f"Method: {method}, args: {args}"
                  + (f", kwargs: {kwargs}" if kwargs else "")
                  + f", expected: {expected}")
            result = getattr(instance, method)(*args, **kwargs)
            assert result == expected, (
                f"Failed: {call} returned {result!r}, expected {expected!r}"
            )
        print("All Passed!")
