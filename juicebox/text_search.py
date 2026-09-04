# Problem 3: Text Search
#
# Build a small in-memory text search engine. Documents are added over time;
# a query returns the ids of matching documents, best match first.
#
#   se.add_document(doc_id, text)
#   se.search(query, k=10)   up to k doc ids, most relevant first
#
# Matching:
#   - case-insensitive, whole words only: "cat" must not match "catalog"
#   - every word in the query must appear in the document (AND)
#   - a query with no words, or with a word found in no document -> []
#
# Ranking: documents that feature the query words more heavily rank higher.
# Be ready to justify the scoring you choose.
#
# Example:
#   se = SearchEngine()
#   se.add_document("d1", "Fresh juice daily")
#   se.add_document("d2", "Juice juice juice - the juice catalog")
#   se.add_document("d3", "A catalog of cats")
#   se.search("juice")        -> ["d2", "d1"]
#   se.search("juice fresh")  -> ["d1"]
#   se.search("cat")          -> []     # "catalog"/"cats" are not "cat"
#   se.search("juice", k=1)   -> ["d2"]
from prep_lib import run_test_cases
from collections import Counter
import re
import heapq

class SearchEngine:
    def __init__(self):
        self.index = {}

    def add_document(self, doc_id: str, text: str):
        words = self._tokenize(text)
        w_counts = Counter(words)

        for word in w_counts.keys():
            self.index.setdefault(word, []).append((doc_id, w_counts[word]))

    def search(self, query: str, k: int | None = 10):
        results = {}
        words_set = set()    
        for i, w in enumerate(self._tokenize(query)):
            if w not in self.index: return []
            if w in words_set: continue
            result_set = set()
            for doc_id, count in self.index[w]:
                if i > 0 and doc_id not in results: continue
                if doc_id not in results:
                    results[doc_id] = count
                else:
                    results[doc_id] += count
                result_set.add(doc_id)
            for r_key in list(results.keys()):
                if r_key not in result_set:
                    del results[r_key]
            
            words_set.add(w)

        sorted_results = heapq.nlargest(k, results.items(), key=lambda x: x[1])
        return [doc_id for doc_id, _ in sorted_results]

    def _tokenize(self, text: str):
        return [w.lower() for w in re.findall(r'\w+', text)]


if __name__ == "__main__":
    test_cases = [ 
        [
            ("add_document", ("d1", "Fresh juice daily"), None),
            ("add_document", ("d2", "Juice juice juice - the juice catalog"), None),
            ("add_document", ("d3", "A catalog of cats"), None),
            ("search", ("juice",), ["d2", "d1"]),
            ("search", ("juice fresh",), ["d1"]),
            ("search", ("cat",), []),
            ("search", ("juice", 1), ["d2"]),
        ],
        [
            ("add_document", ("d1", "apple banana cherry"), None),
            ("add_document", ("d2", "apple banana"), None),
            ("add_document", ("d3", "apple cherry"), None),
            ("search", ("apple banana cherry",), ["d1"]),
        ],
    ]

    run_test_cases(test_cases, SearchEngine, None)

