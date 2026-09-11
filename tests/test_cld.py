import random
import unittest

from statistics.cld import (compact_letter_display, verify_invariants,
                            letter_symbol)
from statistics.types import SignificanceMatrix


def matrix_from_pairs(labels, sig_pairs):
    idx = {l: i for i, l in enumerate(labels)}
    k = len(labels)
    m = [[False] * k for _ in range(k)]
    for a, b in sig_pairs:
        i, j = idx[a], idx[b]
        m[i][j] = m[j][i] = True
    return SignificanceMatrix(list(labels), m, "test")


class TestLetterSymbols(unittest.TestCase):
    def test_bijective_base26(self):
        self.assertEqual(letter_symbol(0), "a")
        self.assertEqual(letter_symbol(25), "z")
        self.assertEqual(letter_symbol(26), "aa")
        self.assertEqual(letter_symbol(27), "ab")
        self.assertEqual(letter_symbol(51), "az")
        self.assertEqual(letter_symbol(52), "ba")
        self.assertEqual(letter_symbol(701), "zz")
        self.assertEqual(letter_symbol(702), "aaa")


class TestCanonicalCase(unittest.TestCase):
    def test_a_ab_b(self):
        # A vs B = NS, B vs C = NS, A vs C = S  =>  A:a, B:ab, C:b
        m = matrix_from_pairs(["A", "B", "C"], [("A", "C")])
        cld = compact_letter_display(m, order=["A", "B", "C"])
        self.assertEqual([], verify_invariants(m, cld))
        # A and C must not share; A-B and B-C must share
        self.assertEqual(set(cld.letters["A"]) & set(cld.letters["C"]), set())
        self.assertTrue(set(cld.letters["A"]) & set(cld.letters["B"]))
        self.assertTrue(set(cld.letters["B"]) & set(cld.letters["C"]))
        self.assertEqual(cld.display["B"], "ab")


class TestBoundaryStructures(unittest.TestCase):
    def test_all_different(self):
        labels = ["A", "B", "C", "D"]
        pairs = [(a, b) for i, a in enumerate(labels) for b in labels[i + 1:]]
        m = matrix_from_pairs(labels, pairs)
        cld = compact_letter_display(m, order=labels)
        self.assertEqual([], verify_invariants(m, cld))
        self.assertEqual(cld.n_letters, 4)

    def test_all_same(self):
        labels = ["A", "B", "C", "D"]
        m = matrix_from_pairs(labels, [])
        cld = compact_letter_display(m, order=labels)
        self.assertEqual([], verify_invariants(m, cld))
        self.assertEqual(cld.n_letters, 1)

    def test_more_than_26_groups(self):
        labels = [f"G{i}" for i in range(30)]
        # make everything significantly different -> 30 letters
        pairs = [(labels[i], labels[j]) for i in range(30) for j in range(i + 1, 30)]
        m = matrix_from_pairs(labels, pairs)
        cld = compact_letter_display(m, order=labels)
        self.assertEqual([], verify_invariants(m, cld))
        self.assertEqual(cld.n_letters, 30)
        # letters must extend past z
        all_syms = set()
        for v in cld.letters.values():
            all_syms.update(v)
        self.assertIn("aa", all_syms)


class TestInvariantsProperty(unittest.TestCase):
    """Property-based: random significance matrices must satisfy the invariants."""

    def test_random_matrices(self):
        rng = random.Random(12345)
        for _ in range(400):
            k = rng.randint(2, 8)
            labels = [chr(ord("A") + i) for i in range(k)]
            idx = {l: i for i, l in enumerate(labels)}
            m = [[False] * k for _ in range(k)]
            for i in range(k):
                for j in range(i + 1, k):
                    if rng.random() < 0.5:
                        m[i][j] = m[j][i] = True
            sm = SignificanceMatrix(labels, m, "random")
            order = labels[:]
            rng.shuffle(order)
            cld = compact_letter_display(sm, order=order)
            problems = verify_invariants(sm, cld)
            self.assertEqual(problems, [], msg=f"matrix={m} problems={problems}")


class TestDecoupledFromTukey(unittest.TestCase):
    def test_accepts_arbitrary_source(self):
        m = matrix_from_pairs(["X", "Y", "Z"], [("X", "Z")])
        m.source = "Games-Howell"
        cld = compact_letter_display(m, order=["X", "Y", "Z"])
        self.assertEqual(cld.source, "Games-Howell")


if __name__ == "__main__":
    unittest.main()
