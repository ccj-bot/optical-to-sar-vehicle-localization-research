"""Native image coordinates: x right, y down; positive SVG angle, in degrees."""
import numpy as np

def native_corners(cx, cy, width, height, rotation_deg):
    values=np.asarray([cx,cy,width,height,rotation_deg],float)
    if not np.isfinite(values).all() or width<=0 or height<=0:
        raise ValueError('Box must be finite with positive width and height')
    a=np.deg2rad(rotation_deg);c,s=np.cos(a),np.sin(a)
    local=np.array([[-1,-1],[1,-1],[1,1],[-1,1]])*np.array([width,height])/2
    return local@np.array([[c,s],[-s,c]])+np.array([cx,cy])

def raw_to_reference(points, public_delta, reference_offset):
    return np.asarray(points,float)-np.asarray(public_delta,float)+np.asarray(reference_offset,float)

def reference_to_raw(points, public_delta, reference_offset):
    return np.asarray(points,float)+np.asarray(public_delta,float)-np.asarray(reference_offset,float)
