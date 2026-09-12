"""Localhost-only Phase 1A workbench server with append-only JSON persistence."""
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
import argparse,json,datetime

O=Path('D:/profile/research/workspace/output/tpgt/phase_1a'); WB=O/'observation_workbench'
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw): super().__init__(*a,directory=str(O),**kw)
    def do_POST(self):
        path=urlparse(self.path).path
        if path not in ('/api/records','/api/interpretations'): self.send_error(404);return
        try:
            n=int(self.headers.get('Content-Length','0')); obj=json.loads(self.rfile.read(n)); eid=str(obj['event_hypothesis_id']); stamp=datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f')
            if path.endswith('records'):
                phase=obj.get('observation_phase','UNKNOWN'); rev=int(obj.get('revision',0)); dest=WB/'records'/eid/f'r{rev:03d}_{phase}_{stamp}.json'
            else: dest=WB/'interpretations'/eid/f'interpretation_{stamp}.json'
            dest.parent.mkdir(parents=True,exist_ok=True); dest.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
            body=json.dumps({'saved':True,'path':str(dest.relative_to(O))}).encode(); self.send_response(201);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        except Exception as e:self.send_error(400,str(e))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=8765);a=ap.parse_args();server=ThreadingHTTPServer(('127.0.0.1',a.port),Handler);print(f'http://127.0.0.1:{a.port}/index.html',flush=True);server.serve_forever()
if __name__=='__main__':main()
