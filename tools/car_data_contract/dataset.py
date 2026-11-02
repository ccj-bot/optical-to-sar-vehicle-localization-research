"""Read normalized evidence with explicit observation, review and A-line roles.

This is an accidental-leakage guard in the public API, not filesystem security.
Raw images are the primary evidence; named extraction/model tables are opt-in.
"""
from pathlib import Path
import json, hashlib
import numpy as np
import pandas as pd
from PIL import Image

OPTICAL_COLUMNS=['frame_uid','run_id','optical_frame_index','optical_timestamp_ms','optical_image_path',
 'nearest_sar_frame_uid','nearest_sar_frame_index','nearest_sar_timestamp_ms','nearest_delta_ms',
 'sync_status','sync_uncertainty_ms','image_available','image_width_px','image_height_px','image_mode',
 'image_sha256','nominal_grid_sar_index','nominal_grid_sar_frame_available','pairing_status']
SAR_COLUMNS=['scene','sar_frame_index','timestamp_ms_nominal','timestamp_source','image_path','image_available',
 'image_width_px','image_height_px','image_mode','image_sha256','coordinate_space_raw']

class CarDataset:
    def __init__(self, root, *, view='observation'):
        if view not in ['observation','review','manual_initialized']:
            raise ValueError('view must be observation, review or manual_initialized')
        self.root=Path(root).resolve();self.view=view
        self._frames={};self._motion=None
    def frames(self,sensor):
        sensor=sensor.upper()
        if sensor not in ['OPTICAL','SAR']:raise ValueError(sensor)
        if sensor not in self._frames:
            cols=OPTICAL_COLUMNS if sensor=='OPTICAL' else SAR_COLUMNS
            self._frames[sensor]=pd.read_parquet(self.root/(sensor+'_FRAMES.parquet'),columns=cols)
        return self._frames[sensor].copy()
    def frame(self,sensor,index):
        sensor=sensor.upper();d=self.frames(sensor);key='optical_frame_index' if sensor=='OPTICAL' else 'sar_frame_index'
        row=d[d[key]==int(index)]
        if len(row)!=1:raise KeyError(f'{sensor} frame {index} unavailable; no endpoint clamping')
        return row.iloc[0].to_dict()
    def image(self,sensor,index,*,verify_hash=True):
        row=self.frame(sensor,index);p=Path(row['optical_image_path'] if sensor.upper()=='OPTICAL' else row['image_path'])
        if verify_hash and hashlib.sha256(p.read_bytes()).hexdigest()!=row['image_sha256']:
            raise ValueError(f'Image hash mismatch: {p}')
        with Image.open(p) as im:return np.array(im.convert('RGB'))
    def optical_proposals(self,frame_index=None):
        filters=None if frame_index is None else [('optical_frame_index','=',int(frame_index))]
        return pd.read_parquet(self.root/'OPTICAL_CANDIDATES.parquet',filters=filters)
    def paired_context(self,optical_frame_index):
        row=self.frame('OPTICAL',optical_frame_index);sar=self.frames('SAR');t=row['optical_timestamp_ms'];u=row['sync_uncertainty_ms']
        nearby=sar[(sar.timestamp_ms_nominal-t).abs()<=u].copy();nearby['delta_from_optical_ms']=nearby.timestamp_ms_nominal-t
        return {'optical':row,'sar_context':nearby,'status':'NOMINAL_CONTEXT_NOT_CONFIRMED_ASSOCIATION'}
    def fragments(self,sar_frame_index,*,representation):
        self.frame('SAR',sar_frame_index)
        if representation!='native_lsd_v2_20261026':raise ValueError('Unknown extraction representation')
        return pd.read_parquet(self.root/'SAR_OBSERVATIONS.parquet',filters=[('sar_frame_index','=',int(sar_frame_index))])
    def background_model(self,sar_frame_index,*,model_id):
        self.frame('SAR',sar_frame_index)
        if model_id!='v2_half_radial_arc_half_uniform':raise ValueError('Unknown background model')
        return pd.read_parquet(self.root/'SAR_BACKGROUND_MODEL.parquet',filters=[('sar_frame_index','=',int(sar_frame_index))])
    def transform(self,sar_frame_index,*,transform_id):
        self.frame('SAR',sar_frame_index)
        if transform_id!='offline_public_translation_v2':raise ValueError('Unknown transform')
        if self._motion is None:self._motion=json.loads((self.root/'provenance/MOTION.json').read_text(encoding='utf-8-sig'))
        c=json.loads((self.root/'COORDINATE_TRANSFORMS.json').read_text(encoding='utf-8'))
        return {'public_delta':self._motion['public_delta'][str(sar_frame_index)],'reference_offset':c['reference_offset_xy'],
                'temporal_input_scope':'FULL_SEQUENCE_OFFLINE','semantics':c['semantics']}
    def reference_mask(self,sar_frame_index,*,mask_id):
        self.frame('SAR',sar_frame_index)
        if mask_id!='lsd_v2_operator_valid_reference':raise ValueError('Unknown mask')
        c=json.loads((self.root/'COORDINATE_TRANSFORMS.json').read_text(encoding='utf-8'))
        packed=np.load(self.root/'provenance/MASKS_PACKED.npy',mmap_mode='r')
        return np.unpackbits(packed[int(sar_frame_index)],axis=1)[:,:c['reference_sar_space']['width_px']].astype(bool)
    def references(self,*,confirmed_only=True):
        if self.view=='observation':raise PermissionError('Manual references require explicit review or manual_initialized view')
        d=pd.read_parquet(self.root/'MANUAL_ANNOTATIONS.parquet')
        return d[d.reference_authority=='USER_CONFIRMED_NATIVE_SAR'].copy() if confirmed_only else d
    def review_timeline(self,subject_id=None):
        if self.view=='observation':raise PermissionError('Review coverage requires explicit review view')
        filters=None if subject_id is None else [('reference_subject_id','=',subject_id)]
        return pd.read_parquet(self.root/'SUBJECT_TIMELINE.parquet',filters=filters)
    def history_index(self):
        if self.view=='observation':raise PermissionError('Historical output requires explicit review view')
        return json.loads((self.root/'HISTORY_INDEX.json').read_text(encoding='utf-8'))
