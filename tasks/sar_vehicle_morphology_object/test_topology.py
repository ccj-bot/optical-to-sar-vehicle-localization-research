"""Behavioral checks independent of union-find construction."""
import itertools
import json
import unittest
import numpy as np
from scipy import ndimage as ndi
from topology import merge_tree, join, focus_leaves
from common import ROOT


def verify_pairs(z, tree, pixels, pairs):
    for (y1, x1), (y2, x2) in pairs:
        ancestor = join(tree, int(pixels[y1, x1]), int(pixels[y2, x2]))
        level = min(tree['nodes'][ancestor]['level'], z[y1, x1], z[y2, x2])
        for threshold, expected in [(level, True), (np.nextafter(level, np.inf), False)]:
            labels, _ = ndi.label(z >= threshold, structure=np.ones((3, 3)))
            la, lb = labels[y1, x1], labels[y2, x2]
            assert bool(la and la == lb) == expected, (level, threshold, expected)


class TopologyTests(unittest.TestCase):
    def test_flat_plateau_is_single_birth(self):
        tree, _ = merge_tree(np.ones((6, 9)))
        self.assertEqual(len(tree['nodes']), 1)

    def test_atomic_saddle(self):
        z = np.array([[8, 2, 2, 7], [8, 2, 2, 7]], dtype=float)
        tree, pn = merge_tree(z)
        self.assertEqual([n['kind'] for n in tree['nodes']], ['peak', 'peak', 'merge'])
        self.assertEqual(tree['nodes'][-1]['level'], 2)
        verify_pairs(z, tree, pn, [((0, 0), (0, 3))])

    def test_random_equal_levels(self):
        rng = np.random.default_rng(912)
        for _ in range(12):
            z = rng.integers(0, 8, (7, 9)).astype(float)
            tree, pn = merge_tree(z)
            points = [(int(y), int(x)) for y, x in zip(rng.integers(0, 7, 15), rng.integers(0, 9, 15))]
            verify_pairs(z, tree, pn, list(itertools.combinations(points, 2)))

    def test_saved_real_cases(self):
        out = ROOT/'output/sar_vehicle_morphology_object'
        paths = list((out/'objects').glob('*_tree_s*.json'))
        self.assertEqual(len(paths), 14)
        for path in paths:
            tree = json.loads(path.read_text())
            d = np.load(out/'fields'/(path.stem+'.npz')); z = d['field']
            points = [(tree['nodes'][i]['xy'][1], tree['nodes'][i]['xy'][0]) for i in focus_leaves(tree)]
            verify_pairs(z, tree, d['pixel_node'], list(itertools.combinations(points, 2)))


if __name__ == '__main__': unittest.main()
