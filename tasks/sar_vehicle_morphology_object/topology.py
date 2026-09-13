"""Exact discrete 8-neighbor superlevel merge tree, with atomic equal levels.

This compact tree keeps births and merges, not all component-growth pixels.
It is descriptive topology of the supplied field; no physical parts or masks.
"""
import numpy as np


def neighbors(i, h, w):
    y, x = divmod(int(i), w)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if (dx or dy) and 0 <= y+dy < h and 0 <= x+dx < w:
                yield (y+dy)*w+x+dx


def merge_tree(field):
    z = np.asarray(field, dtype=float); h, w = z.shape; a = z.ravel()
    assert np.isfinite(z).all()
    parent = np.full(a.size, -1, dtype=int); size = np.ones(a.size, dtype=int)
    top = {}; nodes = []; pixel_node = np.full(a.size, -1, dtype=int)

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = int(parent[i])
        return int(i)

    def union(i, j):
        ri, rj = root(i), root(j)
        if ri != rj:
            if size[ri] < size[rj]: ri, rj = rj, ri
            parent[rj] = ri; size[ri] += size[rj]

    order = np.argsort(-a, kind='stable')
    breaks = np.r_[0, np.flatnonzero(np.diff(a[order]) != 0)+1, len(order)]
    for begin, end in zip(breaks[:-1], breaks[1:]):
        batch = order[begin:end]; level = float(a[batch[0]])
        old_links = []
        for i in batch:
            for j in neighbors(i, h, w):
                if parent[j] >= 0:
                    old_links.append((int(i), top[root(j)]))
        parent[batch] = batch
        for i in batch:
            for j in neighbors(i, h, w):
                if parent[j] >= 0: union(int(i), j)
        groups = {}
        for i in batch:
            groups.setdefault(root(int(i)), {'pixels': [], 'children': set()})['pixels'].append(int(i))
        for i, child in old_links: groups[root(i)]['children'].add(child)
        for rt, group in groups.items():
            children = sorted(group['children'])
            if len(children) == 1:
                node = children[0]
            else:
                node = len(nodes); p = min(group['pixels']); y, x = divmod(p, w)
                record = {'id': node, 'kind': 'peak' if not children else 'merge',
                          'level': level, 'xy': [x, y], 'children': children,
                          'parent': None, 'boundary': x in (0, w-1) or y in (0, h-1)}
                record['winner'] = node if not children else max(
                    (nodes[c]['winner'] for c in children), key=lambda c: (nodes[c]['level'], -c))
                nodes.append(record)
                for child in children: nodes[child]['parent'] = node
                for child in children:
                    losing = nodes[child]['winner']
                    if losing != record['winner']:
                        nodes[losing]['death'] = level
                        nodes[losing]['persistence'] = nodes[losing]['level']-level
            top[rt] = node; pixel_node[group['pixels']] = node
    roots = sorted({top[root(i)] for i in range(a.size)})
    for rt in roots:
        peak = nodes[rt]['winner']; nodes[peak]['death'] = None
        nodes[peak]['persistence'] = nodes[peak]['level']-float(a.min())
        nodes[peak]['essential'] = True
    return {'shape': [h, w], 'minimum': float(a.min()), 'maximum': float(a.max()),
            'connectivity': 8, 'equal_levels': 'atomic', 'nodes': nodes, 'roots': roots}, pixel_node.reshape(z.shape)


def ancestors(tree, node):
    result = []
    while node is not None:
        result.append(node); node = tree['nodes'][node]['parent']
    return result


def join(tree, a, b):
    pool = set(ancestors(tree, a))
    return next(n for n in ancestors(tree, b) if n in pool)


def focus_leaves(tree, n=10):
    # View cap only; all peaks, including boundary peaks and texture, are saved.
    peaks = [q for q in tree['nodes'] if q['kind'] == 'peak']
    selected = sorted(peaks, key=lambda q: (-q['persistence'], -q['level'], q['id']))[:n]
    return [q['id'] for q in sorted(selected, key=lambda q: (q['xy'][1], q['xy'][0]))]


def draw_tree(ax, tree, selected):
    selected = set(selected); nodes = tree['nodes']; counter = [0]; positions = {}
    colors = __import__('matplotlib').colormaps['tab10']
    labels = {}

    def visit(n):
        node = nodes[n]
        if node['kind'] == 'peak':
            if n not in selected: return None
            x = counter[0]; counter[0] += 1; positions[n] = x
            labels[n] = x+1
            ax.scatter([x], [node['level']], color=colors(x % 10), s=22)
            return x, node['level']
        branches = [v for c in node['children'] if (v := visit(c)) is not None]
        if not branches: return None
        if len(branches) == 1: return branches[0]
        xs = [v[0] for v in branches]
        for x, height in branches: ax.plot([x, x], [height, node['level']], color='#526572', lw=1)
        ax.plot([min(xs), max(xs)], [node['level']]*2, color='#526572', lw=1)
        return float(np.mean(xs)), node['level']

    for rt in tree['roots']: visit(rt)
    ax.set_xticks(range(counter[0]), range(1, counter[0]+1)); ax.set_xlabel('selected peak (not x position)')
    ax.set_ylabel('same-field display gray'); ax.grid(alpha=.18)
    return labels
