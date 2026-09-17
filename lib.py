# Daniel's personal helpers, shared across every company folder — the
# grown-up sibling of scratch.py. Problem files just write
# `from lib import ...` (uv installs this module into the venv), so helpers
# added below are available to all current and future prep sets.


def run_test_cases(test_cases: list[list], run_specific: int | None = None):
    """My own quick inline checks for a problem file's __main__ block.

    Class scenario: first entry constructs the instance —
    (ClassName, init_args_tuple), or bare ClassName when __init__ takes
    nothing — followed by (method_name, args, expected) steps run
    against that instance.

    Function scenario: no head; every tuple is one call —
    (function, args, expected) — and each may name any function.

    Bare single args don't need a tuple. Either step shape may carry a
    kwargs dict before expected — (method_name, args, kwargs, expected)
    or (function, args, kwargs, expected) — when the call needs keyword
    arguments (e.g. keyword-only params like now=).
    """
    for index, scenario in enumerate(test_cases):
        if run_specific is not None and index != run_specific:
            continue
        head = scenario[0]
        target = head[0] if isinstance(head, tuple) else head
        is_class = isinstance(target, type)
        if is_class:
            init_args = head[1] if isinstance(head, tuple) else ()
            instance = target(*init_args)
            steps = scenario[1:]
            print(f"Test Case {index + 1}: {target.__name__}{init_args}")
        else:
            steps = scenario
            print(f"Test Case {index + 1}")
        for callee, args, *rest in steps:
            if is_class:
                fn, label = getattr(instance, callee), callee
            else:
                fn, label = callee, callee.__name__
            kwargs, expected = rest if len(rest) == 2 else ({}, rest[0])
            if not isinstance(args, tuple):
                args = (args,)
            call = f"{label}{args}" + (f" with {kwargs}" if kwargs else "")
            print(f"{'Method' if is_class else 'Function'}: {label}, "
                  f"args: {args}"
                  + (f", kwargs: {kwargs}" if kwargs else "")
                  + f", expected: {expected}")
            result = fn(*args, **kwargs)
            assert result == expected, (
                f"Failed: {call} returned {result!r}, expected {expected!r}"
            )
        print("All Passed!")
