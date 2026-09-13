"""First exploratory stage: seven raw/scale-2 exact merge trees and overlays."""
import numpy as np
import matplotlib.pyplot as plt
from scipy import ndimage as ndi
from common import arguments, load_cases, writejson, digest, git_snapshot, smooth, show, savefig
from topology import merge_tree, focus_leaves, draw_tree


def main():
    args = arguments(); cases = load_cases(args)
    if not (args.out/'PREEXISTING_GIT.json').exists():
        writejson(args.out/'PREEXISTING_GIT.json', git_snapshot())
    lineage = []; summary = []
    for r, z, raw, note, anchor in cases:
        sid = r['sample_id']; alias = r['atlas_id']; stats = {}
        lineage.append({'sample_id': sid, 'atlas_id': alias, 'field': r['field'],
                        'sha256': digest(args.source/r['field']), 'gt_geometry': r['gt_geometry'],
                        'gt_quality': r['gt_quality'], 'identity': r['canonical_vehicle'],
                        'selection': note, 'dark_reading_anchor_uv': anchor})
        fig, axes = plt.subplots(2, 3, figsize=(15, 9), layout='constrained')
        for row, sigma in enumerate([0, 2]):
            f = smooth(z, sigma); tree, pn = merge_tree(f)
            selected = focus_leaves(tree)
            labels = draw_tree(axes[row, 1], tree, selected)
            axes[row, 1].set_title(f'sigma={sigma}: induced tree / selected leaves only')
            show(axes[row, 0], z, f'Original field + sigma {sigma} peak locations')
            for node, label in labels.items():
                x, y = tree['nodes'][node]['xy']; color = plt.get_cmap('tab10')((label-1)%10)
                axes[row, 0].scatter(x, y, s=32, facecolors='none', edgecolors=[color])
                axes[row, 0].text(x+1, y-1, str(label), color=color, fontsize=9)
            show(axes[row, 2], z, f'sigma {sigma} superlevel contours: q90/75/55')
            for q, color in [(90, '#ffd176'), (75, '#e76561'), (55, '#55cbd3')]:
                level = float(np.percentile(f, q))
                axes[row, 2].contour(f, levels=[level], colors=[color], linewidths=.65)
            tree['display_leaf_ids'] = selected
            tree['display_labels'] = labels
            writejson(args.out/'objects'/f'{sid}_tree_s{sigma}.json', tree)
            np.savez_compressed(args.out/'fields'/f'{sid}_tree_s{sigma}.npz', field=f, pixel_node=pn)
            stats[f's{sigma}_peaks'] = sum(n['kind']=='peak' for n in tree['nodes'])
            stats[f's{sigma}_merges'] = sum(n['kind']=='merge' for n in tree['nodes'])
        fig.suptitle(f'{alias} {sid} | {note}\nGT aperture is not response mask; raw and smoothed fields are same-source views', fontsize=13)
        savefig(fig, args.out/'figures'/f'{sid}_merge.png')
        summary.append({'sample_id': sid, **stats})
        print(alias, stats, flush=True)
    writejson(args.out/'CASE_LINEAGE.json', lineage)
    writejson(args.out/'MERGE_SUMMARY.json', summary)


if __name__ == '__main__': main()
