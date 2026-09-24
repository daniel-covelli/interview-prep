from collections import OrderedDict

od = OrderedDict([("a", None), ("b", None)])

od["c"] = None

od["a"] = None
print(list(od))
