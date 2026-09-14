"""Posthoc named witnesses and a small, static, image-first reading entry."""
import html
import numpy as np
import matplotlib.pyplot as plt
from run_probe import OUT,CODE_ROOT,load,write,picture,overlay

READOUTS = [('A059_original','G4','Main band: three actual fragments'),
            ('A059_original','G73','Weak band: parallel / serial fragments and gaps'),
            ('A059_original','G96','Competing vertical grouping near the same bright core'),
            ('A059_shuffled','G13','Shuffle: two accidental fragments also have a valley')]


def main():
    fig,axes=plt.subplots(len(READOUTS),3,figsize=(14,13),layout='constrained');notes=[]
    for row,(name,gid,description) in enumerate(READOUTS):
        obj=load(OUT/'records'/(name+'.json.gz'));a=np.load(OUT/'records'/(name+'.npz'));z=a['I0']
        g=next(g for g in obj['groups'] if g['id']==gid);fs={f['id']:f for f in obj['fragments']};es={e['id']:e for e in obj['gaps']}
        pts=np.array(g['support_xy']);lo=np.maximum(pts.min(0)-6,0);hi=np.minimum(pts.max(0)+7,[z.shape[1],z.shape[0]])
        for ax in axes[row,:2]:picture(ax,z,name+' / '+gid);ax.set_xlim(lo[0],hi[0]);ax.set_ylim(hi[1],lo[1])
        for j,mid in enumerate(g['members']):
            f=fs[mid];color=plt.get_cmap('tab10')(j%10);overlay(axes[row,1],z.shape,f['support_xy'],color)
            endpoints=np.array(f['endpoints_xy']);axes[row,1].plot(endpoints[:,0],endpoints[:,1],'o',mfc='none',mec='yellow',ms=3)
            axes[row,1].text(*endpoints[0],mid,color='white',fontsize=6)
        for eid in g['gap_witnesses']:
            edge=es[eid];xy=np.array(edge['section_xy']);axes[row,1].plot(xy[:,0],xy[:,1],ls='--',color='cyan',lw=.8)
            axes[row,2].plot(edge['I0_profile'],lw=.8,label=eid)
        axes[row,2].set_title(description,fontsize=9);axes[row,2].set_xlabel('gap sample / actual I0 gray');axes[row,2].legend(fontsize=6)
        notes.append(dict(case=name,group=gid,posthoc_visual_purpose=description,members=g['members'],
            scale_witnesses={mid:{k:dict(passing=sum(v['crest_at_each_pixel']),total=len(v['center'])) for k,v in fs[mid]['scale_audit'].items()} for mid in g['members']}))
    fig.suptitle('Posthoc illustrative hypotheses, NOT selected target objects\nPixels = actual fragments; cyan dashed = gap witness, never filled support',fontsize=13)
    fig.savefig(OUT/'figures/FOCUSED_GROUP_CASES.png',dpi=140);plt.close(fig)
    write(OUT/'MANUAL_READOUTS.json',notes)
    # Show I1/I2/I4 influence along named actual fragments, never overwrite I0.
    obj=load(OUT/'records/A059_original.json.gz');a=np.load(OUT/'records/A059_original.npz');fs={f['id']:f for f in obj['fragments']}
    chosen=['F0_5','F0_103','F0_29'];fig,axes=plt.subplots(3,3,figsize=(13,9),layout='constrained')
    for row,mid in enumerate(chosen):
        f=fs[mid];pts=np.array(f['path_xy']);picture(axes[row,0],a['I0'],mid+' / original path');overlay(axes[row,0],a['I0'].shape,pts,[0,1,1,.8])
        lo=np.maximum(pts.min(0)-7,0);hi=pts.max(0)+8;axes[row,0].set_xlim(lo[0],hi[0]);axes[row,0].set_ylim(hi[1],lo[1])
        for scale,(key,record) in enumerate(f['scale_audit'].items()):
            axes[row,1].plot(record['center'],label=key)
            axes[row,2].plot(np.asarray(record['crest_at_each_pixel'],int)+1.2*scale,label=key)
        axes[row,1].set_title('Same path / displayed field value');axes[row,2].set_title('Each scale retains local crest? (offset rows)')
        axes[row,1].legend(fontsize=7);axes[row,2].legend(fontsize=7)
    fig.suptitle('Fixed original pixel path, multiple same-source scale witnesses',fontsize=13)
    fig.savefig(OUT/'figures/SCALE_WITNESSES.png',dpi=140);plt.close(fig)
    page='<!doctype html><meta charset="utf-8"><title>Local support probe</title><style>body{font:17px system-ui;max-width:1400px;margin:28px auto;line-height:1.6}img{width:100%}li{margin:8px 0}.note{background:#fff0cd;padding:14px}details{margin:18px 0}</style>'
    page+='<h1>实际局部支撑 → fragment → 有限、允许断裂的 group</h1><p class="note">这不是车辆检测。先看原场和真实像素，再看组；同名候选语义不等于正确组织。蓝/青虚线只是间隔剖面，不是亮桥。native 窗口没有改变采样。</p>'
    page+='<p><a href="REPORT.md">研究报告</a> · <a href="VALIDATION.json">技术验证</a> · <a href="APERTURE_COMPARISON.json">逐项 native 对照</a> · <a href="MANUAL_READOUTS.json">示例成员与尺度见证</a></p>'
    for title,image,description in [
        ('1. 同一 native 主侧','NATIVE_MAIN.png','三行分别为 W1/W2/W3；相同原生像素、相同局部支撑，不代表唯一分组或目标归属。'),
        ('2. 同一 native 弱侧','NATIVE_WEAK.png','弱片段与暗断口共同保留；没有为了连通而填入暗间隔。'),
        ('3. 原图组织与偶然分组','FOCUSED_GROUP_CASES.png','G4/G73 为局部片段组合；G96 是同一亮核附近竞争方向解释；shuffled G13 也有间隔和低谷，不可将这些名字当作车辆证据。'),
        ('4. 旧机制为何丢掉主带','BASELINE_LEVELS_AND_REJECTION.png','分位数水平变化与连通支持被吞并、PCA 拒绝是不同步骤；稳定的空输出也不是恢复。'),
        ('5. 多尺度各自承担什么','SCALE_WITNESSES.png','I0 路径保持原样，I1/I2/I4 只记录这些同位置点的响应与局部脊条件变化。')]:
        page+=f'<h2>{title}</h2><p>{description}</p><a href="figures/{image}"><img src="figures/{image}" alt="{title}"></a>'
    page+='<h2>全部夹具 / 窗口</h2>'
    for row in load(OUT/'MANIFEST.json'):
        name=row['name'];page+=f'<details><summary>{html.escape(name)}：原场、像素支撑及组</summary><p><a href="records/{name}.json.gz">完整结构 JSON.gz</a> · <a href="records/{name}.npz">完整二维场 NPZ</a></p><img src="figures/{name}_support.png" alt="{name}"><img src="figures/{name}_groups.png" alt="{name} local witnesses"></details>'
    (OUT/'INDEX.html').write_text(page,encoding='utf8')
    report=CODE_ROOT/'docs/local_support_probe_20260914.md'
    if report.exists():
        (OUT/'REPORT.md').write_text(report.read_text(encoding='utf8').replace(
            '../output/local_support_probe/', '').replace(
            'local_support_probe_assets/', 'figures/'), encoding='utf8')
    print('Image-first review entry and named witness figures complete.')


if __name__=='__main__':main()
