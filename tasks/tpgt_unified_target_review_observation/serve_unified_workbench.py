from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
import argparse,json,datetime
ROOT=Path('D:/profile/research'); OUT=ROOT/'workspace/output/tpgt/unified_target_review_observation'
class H(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT),**kw)
    def do_POST(self):
        p=urlparse(self.path).path
        if p not in ('/workspace/output/tpgt/unified_target_review_observation/api/reviews','/workspace/output/tpgt/unified_target_review_observation/api/frozen','/workspace/output/tpgt/unified_target_review_observation/api/observations','/workspace/output/tpgt/unified_target_review_observation/api/interpretations'):self.send_error(404);return
        try:
            n=int(self.headers.get('Content-Length','0'));x=json.loads(self.rfile.read(n)); key=str(x.get('review_id') or x.get('freeze_id') or x.get('observation_id') or x.get('interpretation_id')); now=datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f'); kind=p.rsplit('/',1)[-1]; d=OUT/('reviews' if kind=='reviews' else 'frozen_targets' if kind=='frozen' else 'observations' if kind=='observations' else 'interpretations')/key; d.mkdir(parents=True,exist_ok=True); rev=int(x.get('revision',1)); dest=d/f'r{rev:03d}_{now}.json';dest.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8');body=json.dumps({'saved':True,'path':str(dest.relative_to(ROOT))}).encode();self.send_response(201);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        except Exception as e:self.send_error(400,str(e))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=8780);a=ap.parse_args();print(f'http://127.0.0.1:{a.port}/workspace/output/tpgt/unified_target_review_observation/index.html',flush=True);ThreadingHTTPServer(('127.0.0.1',a.port),H).serve_forever()
if __name__=='__main__':main()
