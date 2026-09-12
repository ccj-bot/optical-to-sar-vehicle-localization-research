from pathlib import Path
import sys,socket,subprocess,json,time,urllib.request
W=Path('D:/profile/research/workspace');O=W/'output/tpgt/phase_1a';A=O/'audit'
with socket.socket() as sock:
    sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
log=(A/'local_viewer_server.log').open('a',encoding='utf-8')
p=subprocess.Popen([sys.executable,'-m','http.server',str(port),'--bind','127.0.0.1','--directory',str(O)],cwd=O,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
url=f'http://127.0.0.1:{port}/index.html'
for _ in range(30):
    try:
        with urllib.request.urlopen(url,timeout=2) as r:assert 'TPGT Phase 1A' in r.read().decode('utf-8')
        break
    except OSError:time.sleep(.2)
else:raise RuntimeError('Viewer server failed')
record={'url':url,'pid':p.pid,'root':str(O),'bind':'127.0.0.1','purpose':'Local evidence review; files also open standalone without server'}
(A/'local_viewer_server.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record))
