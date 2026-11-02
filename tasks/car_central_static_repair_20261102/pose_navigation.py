"""Local image-motion navigation for manual annotation. Not identity validation."""
from review import *
import cv2

data=source();raw={f:data.image('SAR',f) for f in range(358,495)}
gray={f:cv2.cvtColor(im,cv2.COLOR_RGB2GRAY) for f,im in raw.items()}
old=json.loads((OLD/'ANNOTATIONS.json').read_text(encoding='utf-8'))['records']
anchors={r['subject_id']:r['sar_box'] for r in old if r['sar_frame']==358}
models={}
for radius in [100,160]:
    variant={}
    for s,a in anchors.items():
        center=np.array([a['cx'],a['cy']],float);pose=np.eye(3);rows=[]
        for f in range(358,495):
            if f>358:
                mask=np.zeros_like(gray[f]);cv2.circle(mask,tuple(np.round(center).astype(int)),radius,255,-1)
                pts=cv2.goodFeaturesToTrack(gray[f-1],maxCorners=220,qualityLevel=.03,minDistance=7,mask=mask,blockSize=5)
                new,ok,_=cv2.calcOpticalFlowPyrLK(gray[f-1],gray[f],pts,None,winSize=(21,21),maxLevel=2)
                back,okb,_=cv2.calcOpticalFlowPyrLK(gray[f],gray[f-1],new,None,winSize=(21,21),maxLevel=2)
                good=ok[:,0].astype(bool)&okb[:,0].astype(bool)&(np.linalg.norm(back[:,0]-pts[:,0],axis=1)<.8)&(np.linalg.norm(new[:,0]-pts[:,0],axis=1)<8)
                p,q=pts[good,0],new[good,0]
                # Similarity supplies yaw only. Preserve original footprint dimensions.
                m,ins=cv2.estimateAffinePartial2D(p,q,method=cv2.RANSAC,ransacReprojThreshold=1.5,maxIters=2000,confidence=.99)
                if m is None:raise RuntimeError((s,f,'insufficient correspondence'))
                scale=np.hypot(m[0,0],m[1,0]);rot=m[:,:2]/scale
                inlier=ins[:,0].astype(bool);translation=np.median(q[inlier]-p[inlier]@rot.T,axis=0)
                step=np.eye(3);step[:2,:2]=rot;step[:2,2]=translation;pose=step@pose;center=(pose@np.r_[a['cx'],a['cy'],1])[:2]
                residual=np.linalg.norm(q[inlier]-(p[inlier]@rot.T+translation),axis=1)
            box=dict(a);box.update(cx=float(center[0]),cy=float(center[1]),rotation_deg=float(a['rotation_deg']+np.degrees(np.arctan2(pose[1,0],pose[0,0]))))
            rows.append({'frame':f,'box':box,'correspondences':int(inlier.sum()) if f>358 else None,'median_residual':float(np.median(residual)) if f>358 else None})
        variant[s]=rows
        print(radius,s,[(r['frame'],[round(r['box'][k],1) for k in ['cx','cy','rotation_deg']]) for r in rows if r['frame'] in [400,420,440,460,480,494]])
    models[str(radius)]=variant
dump(OUT/'diagnostics'/'local_rigid_navigation.json',{'role':'LOCAL_COMMON_IMAGE_MOTION_NAVIGATION_NOT_INDEPENDENT_BODY_MEASUREMENT','preserved':'source widths and heights; no scale fitting used for body','variants':models})
for f in [400,420,440,460,480,494]:
    im=Image.fromarray(raw[f]);d=ImageDraw.Draw(im)
    for rad,col in [('100','#ffffff'),('160','#ffbf69')]:
        for s,rows in models[rad].items():
            b=next(r['box'] for r in rows if r['frame']==f);c=native_corners(*(b[k] for k in ['cx','cy','width','height','rotation_deg']));d.line([tuple(p) for p in np.vstack([c,c[:1]])],fill=col,width=1)
            if rad=='100':d.text((b['cx']-15,b['cy']),s,font=font(16),fill='white',stroke_width=1,stroke_fill='black')
    im.save(OUT/'reading'/f'rigid_navigation_{f}.png')
