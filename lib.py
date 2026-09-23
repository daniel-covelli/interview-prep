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

    Drop a bare `show` (from lib) anywhere in the steps to print the
    instance's internal state at that point — `(show, "label")` titles
    the snapshot, and `(show, obj)` prints some other object instead
    (the only form that works in a function scenario).
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
        for step in steps:
            if step is show or (isinstance(step, tuple) and step[:1] == (show,)):
                extra = step[1] if isinstance(step, tuple) and len(step) > 1 else None
                if extra is None or isinstance(extra, str):
                    show(instance, label=extra, indent=4)
                else:
                    show(extra, indent=4)
                continue
            callee, args, *rest = step
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


# ---------------------------------------------------------------------
# State printer
# ---------------------------------------------------------------------

_MAX_CHAIN = 40      # nodes to follow along a .next chain before "..."
_MAX_DEPTH = 3       # nesting depth before values collapse to "..."
_WIDTH = 78          # fold long dicts/lists onto one entry per line


def show(obj, label: str | None = None, indent: int = 0) -> None:
    """Print an object's attributes in an easy-to-grok layout.

    Each attribute of `obj` goes on its own line. Containers render as
    Python literals (deque/OrderedDict/etc. keep their type name so you
    can tell them apart from plain lists/dicts), sets are sorted, and
    long mappings/sequences fold to one entry per line.

    Linked nodes: an object with a forward link (`next`, `right`, `nxt`)
    is walked as a chain from that attribute, each node printed as
    key:value (or its class name). Hops render as
        `<->`  back-link (`prev`/`left`) points back correctly
        `-->`  node HAS a back-link attribute but it doesn't point back
        `->`   singly linked (no back-link attribute)
    A revisited node stops the walk with `↻ back to <label>`, so a
    cycle is visible instead of looping forever.
    """
    pad = " " * indent
    print(f"{pad}{label or type(obj).__name__} state:")
    attrs = vars(obj) if hasattr(obj, "__dict__") else {}
    if not attrs and hasattr(obj, "__slots__"):
        attrs = {n: getattr(obj, n) for n in obj.__slots__ if hasattr(obj, n)}
    if not attrs:
        print(f"{pad}  {_fmt(obj, 0, set())}")
        return
    for name, value in attrs.items():
        text = _fmt(value, 0, set())
        if len(text) > _WIDTH and _entries(value) is not None:
            print(f"{pad}  {name} = {_open(value)}")
            for entry in _entries(value):
                print(f"{pad}      {entry}")
            print(f"{pad}  {_close(value)}")
        else:
            print(f"{pad}  {name} = {text}")


_FORWARD = ("next", "right", "nxt", "succ")
_BACKWARD = ("prev", "left", "pred")


def _link_attrs(value) -> tuple[str | None, str | None]:
    if isinstance(value, type) or callable(value):
        return None, None
    fwd = next((a for a in _FORWARD if hasattr(value, a)), None)
    back = next((a for a in _BACKWARD if hasattr(value, a)), None)
    return fwd, back


def _is_node(value) -> bool:
    return _link_attrs(value)[0] is not None


def _node_label(node) -> str:
    for k, v in (("key", "value"), ("key", "val"), ("k", "v")):
        if hasattr(node, k) and hasattr(node, v):
            return f"{getattr(node, k)!r}:{getattr(node, v)!r}"
    for name in ("key", "val", "value", "data", "item"):
        if hasattr(node, name):
            return repr(getattr(node, name))
    return type(node).__name__


def _chain(node, seen: set) -> str:
    fwd, back = _link_attrs(node)
    out, count = "", 0
    while node is not None and _is_node(node):
        if id(node) in seen:
            return out.rstrip() + f" ↻ back to {_node_label(node)}"
        seen.add(id(node))
        out += _node_label(node)
        count += 1
        if count >= _MAX_CHAIN:
            return out + " ..."
        nxt = getattr(node, fwd)
        if nxt is None:
            return out
        if back is None:
            out += " -> "
        elif getattr(nxt, back, None) is node:
            out += " <-> "
        else:
            out += " --> "
        node = nxt
    if node is not None:
        out += _fmt(node, _MAX_DEPTH, seen)
    return out


def _fmt(value, depth: int, seen: set) -> str:
    from collections import OrderedDict, deque
    from collections.abc import Mapping

    if value is None or isinstance(value, (bool, int, float, str, bytes)):
        return repr(value)
    if isinstance(value, type):
        return value.__name__
    if callable(value) and not hasattr(value, "__dict__"):
        return getattr(value, "__name__", repr(value))
    if depth >= _MAX_DEPTH:
        return "..."
    if id(value) in seen:
        return f"<{type(value).__name__}>"

    if isinstance(value, Mapping):
        seen = seen | {id(value)}
        body = ", ".join(f"{_fmt(k, depth + 1, seen)}: {_fmt(v, depth + 1, seen)}"
                         for k, v in value.items())
        if isinstance(value, OrderedDict):
            return f"OrderedDict[{body}]"
        if type(value) is dict:
            return "{" + body + "}"
        return f"{type(value).__name__}{{{body}}}"
    if isinstance(value, (set, frozenset)):
        seen = seen | {id(value)}
        items = sorted((_fmt(v, depth + 1, seen) for v in value), key=str)
        return "{" + ", ".join(items) + "}"
    if isinstance(value, (list, tuple, deque)):
        seen = seen | {id(value)}
        body = ", ".join(_fmt(v, depth + 1, seen) for v in value)
        if isinstance(value, deque):
            return f"deque[{body}]"
        if isinstance(value, tuple):
            return "(" + body + ")"
        if type(value) is list:
            return "[" + body + "]"
        return f"{type(value).__name__}[{body}]"
    if _is_node(value):
        # Walk the chain only for a top-level attribute; inside a
        # container (e.g. a key -> node map) just label the node.
        return _chain(value, set(seen)) if depth == 0 else _node_label(value)
    if hasattr(value, "__dict__") or hasattr(value, "__slots__"):
        seen = seen | {id(value)}
        names = (vars(value).keys() if hasattr(value, "__dict__")
                 else [n for n in value.__slots__ if hasattr(value, n)])
        body = ", ".join(f"{n}={_fmt(getattr(value, n), depth + 1, seen)}"
                         for n in names)
        return f"{type(value).__name__}({body})"
    return repr(value)


def _entries(value) -> list[str] | None:
    """One formatted line per entry, for folding long containers."""
    from collections.abc import Mapping
    if isinstance(value, Mapping):
        return [f"{_fmt(k, 1, set())}: {_fmt(v, 1, set())}," for k, v in value.items()]
    if isinstance(value, (list, tuple, set, frozenset)) or type(value).__name__ == "deque":
        items = value
        if isinstance(value, (set, frozenset)):
            items = sorted(value, key=repr)
        return [f"{_fmt(v, 1, set())}," for v in items]
    return None


def _open(value) -> str:
    from collections import OrderedDict, deque
    from collections.abc import Mapping
    if isinstance(value, OrderedDict):
        return "OrderedDict["
    if isinstance(value, deque):
        return "deque["
    if isinstance(value, Mapping):
        return "{"
    if isinstance(value, (set, frozenset)):
        return "{"
    if isinstance(value, tuple):
        return "("
    return "["


def _close(value) -> str:
    return {"{": "}", "(": ")"}.get(_open(value), "]")
