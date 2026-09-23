# Shared test harness. Nothing interview-relevant in here.
#
# NOTE FOR DANIEL: the test files (in each company's tests/ folder) import
# brute-force oracles and enumerate the edge cases. Reading them spoils the
# exercise — just run:
#
#   uv run grade                            # everything
#   uv run grade monaco/p1_rate_limiter.py  # one problem
#   uv run grade monaco                     # one company's set
#
import copy
import importlib
import inspect
import pprint
import signal
import sys
import textwrap
import time
import traceback
from pathlib import Path

# Solution folders are packages (juicebox/, monaco/, ...): only the repo root
# goes on sys.path, and modules load by dotted name ("monaco.p1_rate_limiter").
# Adding a new company folder needs no changes here.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_TTY = sys.stdout.isatty()


def _c(code, s):
    return f"\033[{code}m{s}\033[0m" if _TTY else s


def green(s): return _c("32", s)
def red(s): return _c("31", s)
def yellow(s): return _c("33", s)
def dim(s): return _c("2", s)
def bold(s): return _c("1", s)


class PerfConcern(Exception):
    """Raised inside a case to record a performance/quality warning (⚠),
    as opposed to a failure which records a bug (✗)."""


# ---- LeetCode-style failure output -----------------------------------------
#
# Correctness cases wrap the object under test with `tracing(cls)`, which
# records the constructor call and every method call (with its return value).
# When a case fails, the recorded calls replay as an "Input:" block — the
# constructor first, prior calls with their actual results, and the last call
# (the one whose result was wrong) on its own "→" line — followed by
# "Output:" and "Expected:". Performance cases don't trace and report
# exactly as before.

_UNSET = object()
_LABEL_W = 10          # width of "Expected: ", the widest label
_WRAP_COL = 96         # right margin for wrapped i/o lines
_MAX_CALLS = 80        # longer call logs print head + tail with a gap marker
_VALUE_CAP = 800       # output/expected reprs truncated past this


class desc(str):
    """A human-readable description shown bare on an i/o line (not repr'd)."""


def _fmt_value(v, cap=_VALUE_CAP):
    return str(v) if isinstance(v, desc) else short(v, cap)


def _fmt_call(method, args, kwargs):
    bits = [repr(a) for a in args] + [f"{k}={v!r}" for k, v in kwargs.items()]
    return f"{method}({', '.join(bits)})"


class Failure(AssertionError):
    """A correctness failure carrying its Output / Expected payload.
    The Input line is reconstructed from the case's traced calls."""

    def __init__(self, output=_UNSET, expected=_UNSET, note=None):
        self.output = output
        self.expected = expected
        self.note = note
        bits = []
        if output is not _UNSET:
            bits.append(f"output: {_fmt_value(output, 120)}")
        if expected is not _UNSET:
            bits.append(f"expected: {_fmt_value(expected, 120)}")
        if note:
            bits.append(note)
        super().__init__(" — ".join(bits) or "failed")


_traces = []       # tracing() instances created during the running case
_call_seq = 0      # global counter so the overall-last call gets the "→"
_paused = False    # True inside bench(): timing loops are never replayed


_PENDING = object()    # a traced call's result before/unless it returns


class _Traced:
    """Transparent proxy that records method calls for failure replay."""

    def __init__(self, obj, ctor):
        self._obj = obj
        self._ctor = ctor                  # "ClassName(args...)" repr
        self._log = []                     # [seq, method, args, kwargs, result]
        _traces.append(self)

    def __getattr__(self, name):
        attr = getattr(self._obj, name)
        if not callable(attr):
            return attr

        def call(*args, **kwargs):
            global _call_seq
            if _paused:
                return attr(*args, **kwargs)
            _call_seq += 1
            entry = [_call_seq, name, args, kwargs, _PENDING]
            self._log.append(entry)
            result = attr(*args, **kwargs)
            entry[4] = result
            return result
        return call


def tracing(cls):
    """Factory for cls whose instances record their calls for Input replay."""
    return lambda *a, **kw: _Traced(cls(*a, **kw), _fmt_call(cls.__name__, a, kw))


_SNAPSHOT_ITEMS = 2000   # args with more nested items than this are logged by reference


def _small(obj, budget=_SNAPSHOT_ITEMS):
    """True if obj holds at most `budget` nested items (bails out early)."""
    stack, seen = [obj], 0
    while stack:
        cur = stack.pop()
        seen += 1
        if seen > budget:
            return False
        if isinstance(cur, dict):
            stack.extend(cur.keys()); stack.extend(cur.values())
        elif isinstance(cur, (list, tuple, set, frozenset)):
            stack.extend(cur)
    return True


def _snapshot(value):
    """Deep-copy small arguments so a solution that mutates its inputs
    (sorts a list in place, say) still replays with what it was GIVEN."""
    if not _small(value):
        return value
    try:
        return copy.deepcopy(value)
    except Exception:
        return value


class _TracedFn:
    """Call-recording wrapper for a module-level solution function. Records
    each call (args snapshotted, see _snapshot) so a failure prints the
    exact call that produced the wrong output."""

    def __init__(self, fn, name):
        self._fn = fn
        self._name = name
        self._log = []
        self._ctor = None
        try:
            self._sig = inspect.signature(fn)
        except (TypeError, ValueError):
            self._sig = None
        self.__wrapped__ = fn
        self.__name__ = name
        self.__doc__ = getattr(fn, "__doc__", None)

    def __call__(self, *args, **kwargs):
        global _call_seq
        if _paused:
            return self._fn(*args, **kwargs)
        if self not in _traces:            # first call of this case
            self._log = []
            _traces.append(self)
        _call_seq += 1
        entry = [_call_seq, self._name, tuple(_snapshot(a) for a in args),
                 {k: _snapshot(v) for k, v in kwargs.items()}, _PENDING]
        self._log.append(entry)
        result = self._fn(*args, **kwargs)
        entry[4] = result
        return result

    def __repr__(self):
        return f"<traced {self._name}>"

    def format_call(self, args, kwargs):
        """`name(param=value, ...)` — one line if it fits, else one
        parameter per line, values pretty-printed."""
        params = None
        if self._sig is not None:
            try:
                bound = self._sig.bind(*args, **kwargs)
                params = list(bound.arguments.items())
            except TypeError:
                params = None
        if params is None:
            params = [(None, a) for a in args] + list(kwargs.items())

        def one(k, v):
            return f"{k}={short(v, _VALUE_CAP)}" if k else short(v, _VALUE_CAP)
        avail = _WRAP_COL - 6 - _LABEL_W
        flat = f"{self._name}({', '.join(one(k, v) for k, v in params)})"
        if len(flat) <= avail:
            return [flat]
        lines = [f"{self._name}("]
        for n, (k, v) in enumerate(params):
            prefix = f"{k}=" if k else ""
            width = avail - 4 - len(prefix)
            if len(repr(v)) > _VALUE_CAP:
                text = short(v, _VALUE_CAP)      # too big to pretty-print; cap it
            else:
                text = pprint.pformat(v, width=width, compact=True)
            first, *rest = text.splitlines()
            lines.append(f"    {prefix}{first}")
            lines.extend("    " + " " * len(prefix) + ln for ln in rest)
            lines[-1] += ")" if n == len(params) - 1 else ","
        return lines


def expect(output, expected, note=None):
    """Exact-equality check, reported LeetCode-style on mismatch."""
    if output != expected:
        raise Failure(output=output, expected=expected, note=note)


def expect_set(output, expected_ids, note=None):
    """A list with exactly expected_ids as members, in any order."""
    ok = (isinstance(output, list) and len(output) == len(set(output))
          and set(output) == set(expected_ids))
    if not ok:
        raise Failure(output=output,
                      expected=desc(f"{sorted(expected_ids)!r} in any order"),
                      note=note)


def expect_len(output, n, note=None):
    """A list with exactly n entries (membership checked by the caller)."""
    if not isinstance(output, list) or len(output) != n:
        raise Failure(output=output,
                      expected=desc(f"a list of exactly {n} result(s)"),
                      note=note)


def expect_raises(exc_type, fn, note=None):
    """fn() must raise exc_type; returning normally is the failure."""
    try:
        output = fn()
    except exc_type:
        return
    raise Failure(output=output,
                  expected=desc(f"{exc_type.__name__} to be raised"),
                  note=note)


def _crash_site(exc):
    """Best-effort '<file>:<line> in <fn>' pointing at the solution frame."""
    try:
        for fr in reversed(traceback.extract_tb(exc.__traceback__)):
            p = Path(fr.filename).resolve()
            rel = p.relative_to(ROOT) if ROOT in p.parents else None
            # a solution frame lives under ROOT but not in grader/ or a tests/
            if rel and "tests" not in rel.parts and rel.parts[0] != "grader":
                return f"{p.name}:{fr.lineno} in {fr.name}"
    except Exception:
        pass
    return None


class Suite:
    def __init__(self, title):
        self.title = title
        self.passed = 0
        self.failed = 0
        self.warned = 0
        self.skipped = 0
        self._section = ""
        print(f"\n{bold('== ' + title + ' ' + '=' * max(1, 66 - len(title)))}")

    def section(self, name):
        self._section = name
        print(f"\n {bold(name)}")

    def case(self, label, fn):
        global _call_seq
        _traces.clear()
        _call_seq = 0
        try:
            fn()
        except PerfConcern as e:
            self.warned += 1
            print(f"  {yellow('⚠')} {label}")
            self._detail(str(e))
        except NotImplementedError:
            # Monaco-style scaffolds stub methods with NotImplementedError:
            # that's "not written yet", not a bug.
            self.skipped += 1
            print(f"  {dim('- ' + label + ' (skipped: not implemented yet)')}")
        except AssertionError as e:
            self.failed += 1
            print(f"  {red('✗')} {label}")
            if isinstance(e, Failure):
                self._print_input()
                if e.output is not _UNSET:
                    self._io("Output:", _fmt_value(e.output), color=red)
                if e.expected is not _UNSET:
                    self._io("Expected:", _fmt_value(e.expected), color=green)
                if e.note:
                    self._io("", e.note, color=dim)
            else:
                self._detail(str(e) or "assertion failed (no message)")
                self._print_input()
        except Exception as e:
            self.failed += 1
            print(f"  {red('✗')} {label}")
            self._print_input()
            self._io("Raised:", f"{type(e).__name__}: {e}", color=red)
            site = _crash_site(e)
            if site:
                self._io("", f"at {site}", color=dim)
        else:
            self.passed += 1
            print(f"  {green('✓')} {label}")

    def skip(self, label, reason):
        self.skipped += 1
        print(f"  {dim('- ' + label + ' (skipped: ' + reason + ')')}")

    def skip_all(self, reason):
        self.skipped += 1
        print(f"  {dim('- skipped: ' + reason)}")

    def info(self, msg):
        print(f"    {dim(msg)}")

    def _detail(self, msg):
        for line in msg.splitlines():
            print(f"      {line}")

    def _io(self, label, text, color=None):
        """One wrapped 'Label:  value' block at the failure-detail indent."""
        pad = label.ljust(_LABEL_W) if label else " " * _LABEL_W
        width = max(30, _WRAP_COL - 6 - _LABEL_W)
        lines = textwrap.wrap(str(text), width=width, break_long_words=True,
                              break_on_hyphens=False,
                              drop_whitespace=False) or [""]
        lines = [ln if i == 0 else ln.lstrip() or ln for i, ln in enumerate(lines)]
        head = "      " + (bold(pad) if label else pad)
        cont = "      " + " " * _LABEL_W
        print(head + (color(lines[0]) if color else lines[0]))
        for ln in lines[1:]:
            print(cont + (color(ln) if color else ln))

    def _print_input(self):
        """Replay the traced calls of the current case as the Input block.
        Skipped in PERFORMANCE sections: the input there is a synthetic
        workload of thousands of records, and the assert message already
        names the scaling that went wrong."""
        if "PERF" in self._section.upper():
            return
        traces = [t for t in _traces if t._log]
        if not traces:
            return
        last_seq = max(t._log[-1][0] for t in traces)
        # only the instance that made the failing (last) call is replayed:
        # instances never share state, so other objects' histories are noise
        traces = [t for t in traces if t._log[-1][0] == last_seq]
        many = len(traces) > 1
        label = "Input:"

        def fmt_entry(m, a, kw, res):
            call = _fmt_call(m, a, kw)
            # show each prior call's actual return so state history is visible
            # (None results are elided; they're almost always mutators)
            if res is _PENDING or res is None:
                return call
            return f"{call} -> {short(res, 48)}"

        for i, t in enumerate(traces):
            if isinstance(t, _TracedFn):
                # pure function: only the failing (last) call matters
                _, _m, a, kw, _res = t._log[-1]
                earlier = len(t._log) - 1
                for j, line in enumerate(t.format_call(a, kw)):
                    self._io(label if j == 0 else "", line)
                    label = ""
                if earlier:
                    self._io("", f"(the case's {earlier} earlier call"
                                 f"{'s' if earlier > 1 else ''} not shown)", color=dim)
                continue
            entries = list(t._log)
            arrow = None
            if entries[-1][0] == last_seq:
                _, m, a, kw, _res = entries.pop()
                arrow = _fmt_call(m, a, kw)
            calls = [fmt_entry(m, a, kw, res) for _, m, a, kw, res in entries]
            if len(calls) > _MAX_CALLS:
                omitted = len(calls) - 60
                calls = calls[:25] + [f"[… {omitted} calls omitted …]"] + calls[-35:]
            name = f"{t._ctor} #{i + 1}" if many else t._ctor
            body = "; ".join(calls) if calls else "(fresh instance)"
            self._io(label, f"{name}: {body}")
            if arrow is not None:
                self._io("", f"→ {arrow}")
            label = ""

    def summary(self):
        parts = [green(f"{self.passed} passed")]
        if self.failed:
            parts.append(red(f"{self.failed} FAILED"))
        if self.warned:
            parts.append(yellow(f"{self.warned} concern(s)"))
        if self.skipped:
            parts.append(dim(f"{self.skipped} skipped"))
        print(f"\n {bold(self.title + ':')} {', '.join(parts)}")
        return self


def load_class(module_name, class_name):
    """Import a solution module by dotted name ("monaco.p1_rate_limiter")
    and pull a class out of it.

    Returns (cls, None) on success, (None, reason) on failure. Catches
    BaseException because the solution files may run inline asserts or call
    sys.exit at import time.
    """
    fname = module_name.rsplit(".", 1)[-1] + ".py"
    try:
        module = importlib.import_module(module_name)
    except BaseException as e:
        return None, (f"importing {fname} failed with "
                      f"{type(e).__name__}: {e} (inline test code at module "
                      f"level runs on import — did its own asserts fail?)")
    cls = getattr(module, class_name, None)
    if cls is None:
        return None, f"{fname} has no class {class_name} — not implemented yet"
    return cls, None


def load_fn(module_name, fn_name):
    """load_class for module-level functions (p3/p4 are function-shaped).
    The function comes back call-traced (like tracing() for classes) so a
    failure prints the exact call that produced the wrong output. The
    raw function is available as `.__wrapped__` for perf timing loops."""
    fn, err = load_class(module_name, fn_name)
    if fn is None:
        err = err.replace("has no class", "has no function")
        return fn, err
    return _TracedFn(fn, fn_name), None


_BUDGET_S = 10.0     # a single timed fn() call longer than this is a TLE


class _TimeUp(BaseException):
    """Raised inside fn() by the alarm; BaseException so a solution's
    `except Exception` can't swallow it."""


def bench(fn, repeat=3, budget=_BUDGET_S):
    """Best-of-N wall time for fn(). Best (not mean) suppresses OS noise.
    Call tracing is paused while fn runs: timing loops are never replayed,
    and the recorder must not add cost to what's being measured.

    A single fn() call that runs past `budget` seconds is abandoned and
    the case fails as a TLE: a correct-complexity solution finishes every
    perf workload in well under a second, so waiting minutes for a
    quadratic one to complete only delays the same verdict."""
    global _paused
    best = float("inf")
    was = _paused
    _paused = True

    def alarm(signum, frame):
        raise _TimeUp()
    old = signal.signal(signal.SIGALRM, alarm)
    try:
        for _ in range(repeat):
            signal.setitimer(signal.ITIMER_REAL, budget)
            t0 = time.perf_counter()
            try:
                fn()
            except _TimeUp:
                raise AssertionError(
                    f"TLE: one timed run exceeded the {budget:.0f}s budget and was "
                    f"abandoned. Workloads this size finish in well under a second at "
                    f"the target complexity — the solution is doing super-linear work "
                    f"(see this case's name for what is being scaled).") from None
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
            best = min(best, time.perf_counter() - t0)
    finally:
        signal.signal(signal.SIGALRM, old)
        _paused = was
    return best


def fmt_s(seconds):
    if seconds < 1e-3:
        return f"{seconds * 1e6:.0f}µs"
    if seconds < 1.0:
        return f"{seconds * 1e3:.1f}ms"
    return f"{seconds:.2f}s"


def short(obj, limit=90):
    r = repr(obj)
    return r if len(r) <= limit else r[:limit] + "…"


def check_topk(result, true_counts, k, ctx=None):
    """Validate a top-k result list of (item, count) against a dict of true
    counts, without assuming any particular tie order. On failure, one valid
    answer is shown as Expected.

    A result is valid iff: right length, tuples, no duplicate items, every
    returned count is that item's true count, sorted descending, and the
    count sequence equals the true top-k count sequence (so no higher-count
    item was skipped).
    """
    n = len(true_counts)
    want_len = min(k, n)
    want = sorted(true_counts.items(), key=lambda kv: (-kv[1], str(kv[0])))[:want_len]
    tied = len(set(true_counts.values())) < n
    expected = desc(short(want, _VALUE_CAP)
                    + (" (items with equal counts are interchangeable)" if tied else ""))

    def fail(note):
        raise Failure(output=result, expected=expected,
                      note=note + (f"  [{ctx}]" if ctx else ""))

    if not isinstance(result, list):
        fail(f"expected a list, got {type(result).__name__}")
    if len(result) != want_len:
        fail(f"expected {want_len} results (k={k}, {n} distinct items), got {len(result)}")
    for pair in result:
        if not (isinstance(pair, tuple) and len(pair) == 2):
            fail(f"expected (item, count) tuples, got element {short(pair)}")
    items = [i for i, _ in result]
    if len(set(items)) != len(items):
        fail("result contains duplicate items")
    for item, cnt in result:
        actual = true_counts.get(item)
        if actual is None:
            fail(f"{item!r} was returned but isn't in the true result set for this query")
        if actual != cnt:
            fail(f"wrong count for {item!r}: returned {cnt}, true count is {actual}")
    counts = [c for _, c in result]
    if counts != sorted(counts, reverse=True):
        fail("results not sorted by count descending")
    if counts != [c for _, c in want]:
        fail("count sequence doesn't match the true top-k counts — "
             "a higher-count item was omitted")
