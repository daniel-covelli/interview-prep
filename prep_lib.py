# Daniel's personal helpers, shared across every company folder — the
# grown-up sibling of scratch.py. Problem files reach this via
# `from lib import ...` (each company folder's lib.py pointer resolves here),
# so helpers added below are available to all current and future prep sets.


def run_test_cases(test_cases: list[tuple], class_to_make, run_specific: int | None = None):
    """My own quick inline checks for a problem file's __main__ block.

    test_cases: list of scenarios; each scenario is a list of
    (method_name, args_tuple, expected) steps run against one fresh instance.
    """
    for index, test_case in enumerate(test_cases):
        if run_specific is not None and index != run_specific: continue
        c = class_to_make()
        print(f"Test Case: {index + 1}")
        for method, args, expected in test_case:
            print(f"Method: {method}, args: {args}, expected: {expected}")
            method_to_call = getattr(c, method)

            result = method_to_call(*args)

            assert result == expected, f"Failed: {method}({args}) returned {result}, expected {expected}"
        print(f"All Passed!")
