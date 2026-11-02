"""Rendered SAR support and missing-aware resampling in display coordinates.

The saturated outer contour locates the rendered fan, not target evidence.
Filling the contour preserves dark interior pixels. Geometry may further
restrict that support, but exterior colors never enter a valid interpolation.
"""
from pathlib import Path
import cv2
import numpy as np

def rendered_fan_support(bgr, saturation_min=50):
    """Filled largest colored outer contour; never classify interior intensities."""
    if not 0 <= saturation_min < 255:
        raise ValueError("saturation_min must lie in [0,255)")
    hsv=cv2.cvtColor(np.asarray(bgr),cv2.COLOR_BGR2HSV)
    colored=(hsv[:,:,1]>saturation_min).astype("uint8")
    contours,_=cv2.findContours(colored,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ValueError("No rendered colored fan contour")
    contour=max(contours,key=cv2.contourArea)
    if cv2.contourArea(contour)<.01*colored.size:
        raise ValueError("Rendered support too small to establish a fan")
    mask=np.zeros(colored.shape,"uint8")
    cv2.drawContours(mask,[contour],-1,1,cv2.FILLED)
    return mask.astype(bool)

def read_rendered_support(video, frames, shape, saturation_min=50):
    """Read actual frame support. Frame IDs and output dimensions are explicit."""
    wanted=set(map(int,frames))
    if not wanted:return {}
    cap=cv2.VideoCapture(str(Path(video)))
    if not cap.isOpened():raise RuntimeError(f"Cannot open source video: {video}")
    result={}
    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES,min(wanted))
        for f in range(min(wanted),max(wanted)+1):
            ok,bgr=cap.read()
            if not ok:raise RuntimeError(f"Missing source support at frame {f}")
            if f not in wanted:continue
            mask=rendered_fan_support(bgr,saturation_min)
            if mask.shape!=tuple(shape):
                mask=cv2.resize(mask.astype("uint8"),(int(shape[1]),int(shape[0])),interpolation=cv2.INTER_NEAREST).astype(bool)
            result[f]=mask
    finally:cap.release()
    return result

def sample_observed(field, support, mx, my):
    """Bilinear value divided by available interpolation weight; zero means missing."""
    support=np.asarray(support,dtype="float32")
    field=np.asarray(field,dtype="float32")
    if field.shape!=support.shape:raise ValueError("Field/support dimensions differ")
    if not np.isfinite(field[support>0]).all():raise ValueError("Nonfinite observed field")
    # np.where avoids an exterior NaN contaminating a nominally zero product.
    measured=np.where(support>0,field,0)*support
    weights=cv2.remap(support,np.float32(mx),np.float32(my),cv2.INTER_LINEAR)
    numerator=cv2.remap(measured,np.float32(mx),np.float32(my),cv2.INTER_LINEAR)
    valid=weights>1e-6
    values=np.divide(numerator,weights,out=np.zeros_like(numerator),where=valid)
    return values,valid,weights

