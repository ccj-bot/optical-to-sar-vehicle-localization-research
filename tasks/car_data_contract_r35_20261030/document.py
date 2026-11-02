"""Human-readable schema, source overview and handoff for the normalized data."""
from pathlib import Path
import json,sys,shutil,importlib.metadata
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from PIL import Image,ImageDraw,ImageFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from normalize import ROOT,OUT,sha,read_json,dump_json

def main(out=OUT):
    out=Path(out);contract=read_json(out/'DATA_CONTRACT.json');verify=read_json(out/'VERIFICATION.json')
    assert verify['status']=='PASS_DATA_INTEGRITY_AND_SEMANTIC_GUARDS'
    dump_json(out/'ENVIRONMENT.json',{'python':sys.version,'executable':sys.executable,
      'packages':{n:importlib.metadata.version(n) for n in ['numpy','pandas','pyarrow','Pillow','opencv-python','matplotlib']}})
    op=pd.read_parquet(out/'OPTICAL_FRAMES.parquet');sar=pd.read_parquet(out/'SAR_FRAMES.parquet');manual=pd.read_parquet(out/'MANUAL_ANNOTATIONS.parquet');counts=pd.read_csv(out/'SAR_OBSERVATION_FRAME_COUNTS.csv')
    rules={
      'obs_id':'Unique extracted-line record within the frozen source cache; not a physical scatterer or car ID.',
      'source_array_row':'Exact row in the source OBS.npz whose sha256 is bound in DERIVED_OPERATOR.json.',
      'source_candidate_id':'Workbench candidate used when the user created this frame pair; not a guaranteed cross-time identity.',
      'object_hypothesis_id':'Source-scoped optical tracking hypothesis. Never automatically joined to a manual entity.',
      'reference_subject_id':'User workbench ID namespace, valid at recorded reference frames; no unobserved track is implied.',
      'sar_raw_rotation_deg':'Degrees rotating the width axis in x-right/y-down coordinates; positive SVG rotation.',
      'sar_axis_deg_undirected':'Long box axis modulo180 degrees; front/rear heading remains unknown.',
      'raw_a_x':'Native SAR display x coordinate of extracted segment endpoint a; pixels.',
      'raw_a_y':'Native SAR display y coordinate of extracted segment endpoint a; pixels.',
      'a_x':'Same endpoint in explicitly transported reference grid; pixels.',
      'a_y':'Same endpoint in explicitly transported reference grid; pixels.',
      'angle_rad':'Axial segment tangent, radians, modulo pi; not body axis.',
      'angle_deg':'Axial segment tangent in degrees; not body axis.',
      'length_px':'Extracted segment length in native display pixels; not physical vehicle length.',
      'clipped':'Extractor clipped a segment at operator-valid context; does not mean whole vehicle is truncated.',
      'boundary_contact':'Source optical rectangle contacts image boundary; physical truncation is a separate unknown.',
      'background_density':'Value of the inherited assumed background model, separated from observed segment coordinates.',
      'arc_ratio':'Inherited background model mixture ratio; not measured arc ownership or real background probability.',
      'annotation_state':'Review coverage only. UNANNOTATED never means absent, negative, or invisible.',
      'visibility_judgment':'Explicit annotation if available; NOT_RECORDED does not mean invisible.',
      'presence_judgment':'Known only at recorded user-confirmed pairs; otherwise UNKNOWN.',
      'nominal_grid_sar_frame_available':'Whether the nominal index target actually exists; false for optical297 -> SAR495.',
      'nearest_sar_frame_index':'Nearest available timestamp context; does not silently replace a missing grid target.',
      'image_sha256':'Exact current JPEG source bytes; decoding is validated, original sensor IQ is unavailable here.',
      'source_json_pointer':'JSON Pointer into the immutable annotation snapshot.',
      'physical_identity_status':'Independent physical identity state; upstream tracking labels are retained in source_* fields.',
      'vehicle_ownership':'Physical attribution of a line; UNRESOLVED for all extracted segments.',
    }
    dictionary={'schema_kind':'TYPED_TABLE_DATA_DICTIONARY','dataset':'CAR_R35_DATA_CONTRACT_V1','tables':{}}
    roles={
      'OPTICAL_FRAMES':'source frame inventory; observation view', 'SAR_FRAMES':'source frame inventory; observation view',
      'OPTICAL_CANDIDATES':'source detector/track proposals; opt-in optical prior',
      'SAR_OBSERVATIONS':'optional named line extractor output; original images remain primary',
      'SAR_BACKGROUND_MODEL':'optional inherited model assumptions; not measurement',
      'MANUAL_ANNOTATIONS':'explicit review or manual-initialized input only',
      'SUBJECT_TIMELINE':'coverage ledger, including unannotated states; contains no fabricated geometry',
      'LEGACY_AGENT_DRAFTS':'historical agent readings/interpolation/body constructions; not accepted references',
      'RECENT_CONDITIONED_PROPOSALS':'historical A-line diagnostics and transports; not new labels',
      'KNOWN_DATA_EXPOSURE':'known development exposure; does not certify unlisted uses absent',
      'REFERENCE_ASSOCIATIONS':'frame-local user pair and source hint; not cross-time ID reconciliation',
      'FRAME_TRANSFORMS':'offline full-sequence estimated translation; not physical motion',
      'OPERATOR_MASK_COVERAGE':'derived operator-valid area; not full displayed support',
    }
    for p in sorted(out.glob('*.parquet')):
        schema=pq.read_schema(p);md=pq.read_metadata(p)
        dictionary['tables'][p.stem]={'file':p.name,'rows':md.num_rows,'role':roles.get(p.stem,'source-scoped supporting metadata'),
          'fields':[{'name':f.name,'arrow_type':str(f.type),'nullable':f.nullable,'meaning':rules.get(f.name,'Source or normalized field; scope follows table role and DATA_CONTRACT.json.')} for f in schema]}
    dump_json(out/'TABLE_SCHEMA.json',dictionary)
    unknowns={
      'user_confirmed_sar_reference_frames':[358],
      'confirmed_user_subjects':manual.loc[manual.reference_authority=='USER_CONFIRMED_NATIVE_SAR','manual_target_id'].tolist(),
      'unestablished':[
        {'field':'cross_time_manual_identity','state':'UNRESOLVED','needed':'direct same-object source review across actual optical/SAR phases'},
        {'field':'sar_part_semantics','state':'NOT_ANNOTATED','needed':'mark observed support and competing ownership without deriving it from a whole box'},
        {'field':'sar_body_observed_vs_completed_edges','state':'NOT_ANNOTATED','needed':'record visible support versus approximate unseen-body completion'},
        {'field':'occlusion_and_truncation_per_frame','state':'NOT_ANNOTATED_CURRENT_REFERENCE','needed':'separate optical occlusion, image truncation and SAR observability'},
        {'field':'hardware_sync_offset_and_drift','state':'UNVERIFIED','needed':'separate nominal time contexts from validated synchronization'},
        {'field':'independent_confirmation_dataset','state':'NOT_DEFINED','needed':'new source/entity groups outside development exposure'},
      ],'annotation_source_rules':['direct native-image reading','interpolation with source anchors','transport with named transform','model candidate','unknown'],
      'current_full_sequence_registration_is_not_full_sequence_annotation':True}
    dump_json(out/'DATA_GAPS.json',unknowns)
    # Useful actual-image overview without choosing views by response score.
    font=lambda n:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',n)
    im=Image.new('RGB',(2048,680),'#13202b');d=ImageDraw.Draw(im)
    for i,f in enumerate([0,164,329,494]):
        sr=sar.loc[sar.sar_frame_index==f].iloc[0];oi=(op.optical_timestamp_ms-sr.timestamp_ms_nominal).abs().idxmin();rr=op.loc[oi]
        x=i*512;d.text((x+12,9),f"光学{int(rr.optical_frame_index)} / SAR{f}",font=font(22),fill='white')
        d.text((x+12,38),f"名义时间差 {int(sr.timestamp_ms_nominal-rr.optical_timestamp_ms):+d} ms",font=font(17),fill='#c9d7e2')
        for path,y,size in [(rr.optical_image_path,72,(512,288)),(sr.image_path,370,(512,296))]:
            with Image.open(path) as source:im.paste(source.convert('RGB').resize(size,Image.Resampling.LANCZOS),(x,y))
    im.save(out/'RAW_SEQUENCE_OVERVIEW.png')
    plt.rcParams['font.family']='Microsoft YaHei'
    fig,axes=plt.subplots(3,1,figsize=(12,6),constrained_layout=True)
    axes[0].plot(op.optical_frame_index,op.candidate_count,color='#3267aa',lw=1.1);axes[0].set(title='完整光学序列：每帧候选条数（不是车辆真值数量）',ylabel='候选条数',xlabel='光学帧')
    axes[1].plot(counts.sar_frame_index,counts.fragment_count,color='#58906f',lw=1.1);axes[1].set(title='完整 SAR 序列：旧提取器产生的线段数量',ylabel='派生线段',xlabel='SAR 帧')
    axes[2].hlines(0,0,494,color='#acb4bd',lw=12);axes[2].scatter([358],[0],color='#d44b40',s=100,zorder=3);axes[2].annotate('仅 SAR358 有6个当前用户确认框',(358,0),xytext=(180,.55),arrowprops={'arrowstyle':'->'});axes[2].set(xlim=(-5,499),ylim=(-.7,1),yticks=[],xlabel='SAR 帧',title='当前参考覆盖：其余帧保持未标注状态')
    fig.savefig(out/'DATA_COVERAGE.png',dpi=160);plt.close(fig)
    # Copy the reader used to validate this release so later development cannot
    # change package behavior silently.
    dest=out/'runtime/car_data_contract';dest.mkdir(parents=True,exist_ok=True)
    for p in (ROOT/'tools/car_data_contract').glob('*.py'):shutil.copyfile(p,dest/p.name)
    contract['status']='NORMALIZED_AND_TECHNICALLY_VERIFIED';contract['validation']='VERIFICATION.json';contract['schema_dictionary']='TABLE_SCHEMA.json';contract['data_gaps']='DATA_GAPS.json'
    contract['layer_rules']['raw_frames']='native decoded JPEG image evidence, not original radar IQ/RCS'
    contract['coordinate_rules']=read_json(out/'COORDINATE_TRANSFORMS.json')
    dump_json(out/'DATA_CONTRACT.json',contract)
    counts0=contract['counts'];report=f'''# CAR 数据规范 v1：R35 完整序列

已形成可读取的数据包，作用是固定数据来源、坐标、时间和观测含义。当前范围为 R35ZF，标准化数据不等于新增了可靠标注或定位能力。

**入口：[数据覆盖图](DATA_COVERAGE.png) · [完整序列原图抽览](RAW_SEQUENCE_OVERVIEW.png) · [字段字典](TABLE_SCHEMA.json) · [核验回执](VERIFICATION.json)。**

## 已规范的数据

|数据|实际数量|使用含义|
|---|---:|---|
|光学原生帧|298，帧0–297|原图路径、字节哈希、尺寸、名义时间|
|SAR原生帧|495，帧0–494|原图；保留全部时相和全图背景、邻车|
|光学候选|4212条|检测/跟踪提案，原始ID带来源范围|
|SAR派生线段|672155条|旧算子提取结果；原生与运输坐标、裁切、来源行可追溯|
|用户配对记录|9条|6个确认SAR框、3个无SAR框的DRAFT|
|当前用户SAR参考覆盖|1帧：358|其它帧未标注；未据此判目标消失|
|逐对象逐帧登记|7137条|9个参考ID×793源图；是登记表，不是新增标注|
|旧代理草稿登记|1884条|含直接粗读、插值和未标注；保留为历史草稿|

数据来自2026-10-27保存的用户标注快照，本轮没有刷新浏览器。人工框原始坐标逐值保留；正角度遵循原生x向右、y向下的SVG旋转定义。完整框允许超出可观测扇面，不靠截断坐标修饰结果。

## 这次落实的规范

**图像与假设。** 原图是主要证据。线段表只包含明确命名的旧提取器结果；提取器采用JET近似反色表、DoG、MAD、正值截取、0.995分位缩放、LSD和6像素长度条件。这些仍是方法选择，完整来源写在[算子说明](DERIVED_OPERATOR.json)。背景密度/弧形比例移到单独模型表，默认图像接口不自动带入这些假设。

**对象与时间。** 光学候选ID、用户配对ID、旧50候选ID分别保留来源范围。上游“FORMAL”等状态写入source字段，不升级为物理身份。9个用户ID只在有记录的帧具有相应证据；未用相同ID或相近坐标自动补出整段同车关系。

**时间配对。** 继承名义同步和250ms不确定性，额外提供不确定区间内的全部SAR上下文。光学297预计对应SAR495，而源视频只有0–494；预计帧缺失与最近可用494同时记录。公共平移使用全序列离线数据，注明不是物理运动，也不能用于宣称在线无未来信息。

**缺测和标注。** 原图可用、没有候选、没有人工记录、DRAFT、未记录可见性、UNKNOWN身份是不同字段。672155个线段的物理归属均保持UNRESOLVED。原框代表近似整体范围，未给出的部件、真实车头方向、轮廓精度和像素归属保持空值。

**使用接口。** 默认observation视图提供原图与帧信息；候选、线段、背景模型和公共变换必须显式调用。人工参考、标注覆盖与历史结果只在review或manual_initialized视图可读。这是代码接口防误用，文件仍可供研究者直接检查。

## 读取方式

默认解释器为 `python -X utf8 -B`。包内带固定的读取器副本，原图和原视频仍位于源路径，迁移电脑时需一并迁移依赖。

```python
import sys
from pathlib import Path
package = Path('output/car_data_contract_r35_20261030')
sys.path.insert(0, str(package / 'runtime'))
from car_data_contract import CarDataset

data = CarDataset(package)  # observation视图
sar = data.image('SAR', 358)
optical_candidates = data.optical_proposals(215)
time_context = data.paired_context(215)
# 以下是明确选择一个历史派生表示，并非默认原图信息
segments = data.fragments(358, representation='native_lsd_v2_20261026')

review = CarDataset(package, view='review')
confirmed = review.references()  # 只读6个确认框
timeline = review.review_timeline()
```

## 真实验收与剩余缺口

已通过{verify['passed_count']}项数据/语义检查：793张图逐张解码；与原缓存核对495张SAR和500项来源；全部672155个片段坐标往返；候选原值、用户框原值；错误旋转符号反例；缺失SAR495拒绝读取；默认接口阻止人工参考泄漏。上游数据和旧封存保持。

**完整时序标准标注还没有完成。** 当前只有358的6个人工参考；跨帧同车关系、端部/侧边语义、遮挡状态、观测边与补全边仍需按原图逐项记录。具体缺项见[DATA_GAPS](DATA_GAPS.json)。旧草稿、插值和上一轮拟合没有填进这些空项。该包使用的是已暴露开发场景，不是独立测试集。

后续先沿这份统一帧表和对象登记表补直接观察记录，再比较不同结构提取与解释。这样能区分真实时序变化、标注不足和某个提取器的选择效应。
'''
    (out/'START_HERE.md').write_text(report,encoding='utf-8');(out/'REPORT.md').write_text(report,encoding='utf-8')
    print(json.dumps({'stage':'documented','tables':len(dictionary['tables']),'entry':str(out/'START_HERE.md')},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
