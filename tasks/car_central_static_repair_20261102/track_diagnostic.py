"""Adjacent-frame correspondence aid for annotation, never object identity truth."""
from review import *
import cv2

data=source()
raw={f:np.asarray(data.image('SAR',f)) for f in range(358,495)}
gray={f:cv2.cvtColor(im,cv2.COLOR_RGB2GRAY) for f,im in raw.items()}
old=json.loads((OLD/'ANNOTATIONS.json').read_text(encoding='utf-8'))['records']
anchors={r['subject_id']:r['sar_box'] for r in old if r['sar_frame']==358}
allout={}
for s,a in anchors.items():
    mask=np.zeros(gray[358].shape,np.uint8)
    corners=native_corners(*(a[k] for k in ['cx','cy','width','height','rotation_deg']))
    cv2.fillConvexPoly(mask,np.round(corners).astype(np.int32),255)
    pts=cv2.goodFeaturesToTrack(gray[358],maxCorners=140,qualityLevel=.01,minDistance=6,mask=mask,blockSize=5)
    p0=pts[:,0].copy();live=np.ones(len(p0),bool);history={358:p0.copy()};diagnostics=[]
    for f in range(359,495):
        ix=np.where(live)[0]
        prev=history[f-1][ix].reshape(-1,1,2).astype(np.float32)
        new,ok,err=cv2.calcOpticalFlowPyrLK(gray[f-1],gray[f],prev,None,winSize=(21,21),maxLevel=3,criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,30,.01))
        back,okb,errb=cv2.calcOpticalFlowPyrLK(gray[f],gray[f-1],new,None,winSize=(21,21),maxLevel=3,criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,30,.01))
        good=ok[:,0].astype(bool)&okb[:,0].astype(bool)&(np.linalg.norm(back[:,0]-prev[:,0],axis=1)<1.5)&(np.linalg.norm(new[:,0]-prev[:,0],axis=1)<10)
        live[ix[~good]]=False
        now=np.full_like(p0,np.nan);now[ix[good]]=new[good,0];history[f]=now
        if np.count_nonzero(live)>=4:
            mat,inliers=cv2.estimateAffinePartial2D(p0[live],now[live],method=cv2.RANSAC,ransacReprojThreshold=3,maxIters=2000,confidence=.99)
            if mat is not None:
                corners_now=np.c_[corners,np.ones(4)]@mat.T
                diagnostics.append({'frame':f,'live':int(live.sum()),'inliers':int(inliers.sum()),'matrix':mat.tolist(),'scale':float(np.hypot(mat[0,0],mat[1,0])),'rotation_change_deg':float(np.degrees(np.arctan2(mat[1,0],mat[0,0]))),'center':(mat@np.r_[a['cx'],a['cy'],1]).tolist(),'corners':corners_now.tolist()})
    allout[s]={'initial_points':p0.tolist(),'frames':{str(f):[[float(x),float(y)] if np.isfinite(x+y) else None for x,y in arr] for f,arr in history.items()},'similarity_diagnostic':diagnostics}
    print(s,'points',len(p0),'final live',live.sum())
    for r in diagnostics:
        if r['frame'] in [380,400,420,440,460,480,494]:print({k:r[k] for k in ['frame','live','inliers','scale','rotation_change_deg','center']})
dump(OUT/'diagnostics'/'adjacent_correspondences.json',{'role':'ANNOTATION_NAVIGATION_ONLY_NOT_IDENTITY_OR_BODY_MEASUREMENT','method':'21px LK, forward-back <1.5px, step<10px; similarity is source-box-conditioned diagnostic only','objects':allout})
# A single object per sheet, retained marker paths plus both old and diagnostic boxes.
for s,obj in allout.items():
    a=anchors[s];p0=np.array(obj['initial_points']);maps={r['frame']:r for r in obj['similarity_diagnostic']}
    frames=[358,400,440,494];w,h=310,300
    sheet=Image.new('RGB',(w*2,(h+46)*2),'#eef2f4');draw=ImageDraw.Draw(sheet)
    for i,f in enumerate(frames):
        r=next(v for v in old if v['subject_id']==s and v['sar_frame']==f);b=r['sar_box'];left=round(b['cx'])-155;top=round(b['cy'])-150
        im=Image.fromarray(raw[f]).crop((left,top,left+w,top+h));d=ImageDraw.Draw(im)
        c=native_corners(*(b[k] for k in ['cx','cy','width','height','rotation_deg']))-np.array([left,top]);d.line([tuple(q) for q in np.vstack([c,c[:1]])],fill='#a0a0a0',width=1)
        if f in maps:
            c=np.array(maps[f]['corners'])-np.array([left,top]);d.line([tuple(q) for q in np.vstack([c,c[:1]])],fill='#ffffff',width=1)
        for k,p in enumerate(obj['frames'][str(f)]):
            if p is None:continue
            x,y=np.array(p)-[left,top]
            d.ellipse((x-2,y-2,x+2,y+2),outline='#fffc68',width=1)
            if k%3==0:d.text((x+2,y-8),str(k),font=font(10),fill='white',stroke_width=1,stroke_fill='#071724')
        x,y=i%2*w,i//2*(h+46);sheet.paste(im,(x,y+46));draw.text((x+8,y+4),f'{s} SAR{f} | 来源框内点的相邻匹配',font=font(14),fill='#152633');draw.text((x+8,y+25),'灰：旧框；白：配准导航，非整车真值',font=font(12),fill='#152633')
    sheet.save(OUT/'reading'/f'diagnostic_{s}.png')
