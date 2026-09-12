from pathlib import Path
import csv,json
W=Path('D:/profile/research/workspace')
rows=list(csv.DictReader((W/'output/tpgt/phase_0b/EVENT_SOURCE_CANDIDATES.csv').open(encoding='utf-8-sig')))
ids=['C_IDS','C_LOCAL','C_FRAMES','C_RAW','P_TRACKS','P_FRAMES','P_DET','GM_REG','GM_STATES','GM_P1D','P_PILOT','P_BOXES','P_FRAME_REG','P_TIMING']
for sid in ids:
    r=next((r for r in rows if r['source_id']==sid),None)
    if not r: continue
    p=Path(r['source_path']); print('\nSOURCE',sid,str(p))
    if p.suffix=='.csv':
        with p.open(encoding='utf-8-sig') as f:
            reader=csv.DictReader(f); print('FIELDS',reader.fieldnames); print('FIRST',next(reader,None))
    elif p.suffix=='.json': print(p.read_text(encoding='utf-8-sig')[:6000])
