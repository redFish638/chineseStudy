import os, secrets, shutil, socket, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
root=str(Path(__file__).resolve().parent.parent)
folder=tempfile.mkdtemp(prefix='zhiyu-e2e-')
password=secrets.token_urlsafe(24)
with socket.socket() as listener:
    listener.bind(('127.0.0.1',0))
    port=listener.getsockname()[1]
base_url=f'http://127.0.0.1:{port}'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
env={**os.environ,'DATABASE_URL':'sqlite:///'+folder+'/test.db','ZHIYU_ADMIN_PASSWORD':password,'PUBLIC_ORIGIN':base_url,'COOKIE_SECURE':'false'}
server=subprocess.Popen([sys.executable,'-m','uvicorn','backend.main:app','--host','127.0.0.1','--port',str(port),'--no-access-log'],cwd=root,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
try:
    for i in range(60):
        try:
            opener.open(base_url+'/api/health',timeout=2);break
        except Exception:
            if server.poll() is not None: raise RuntimeError(server.stderr.read().decode())
            time.sleep(.2)
    result=subprocess.run(['node',os.getenv('TEST_BROWSER_SCRIPT', 'tests/browser.cjs')],cwd=root,env={**os.environ,'TEST_ADMIN_PASSWORD':password,'TEST_BASE_URL':base_url,**({'CHROMIUM_EXECUTABLE':os.getenv('CHROMIUM_EXECUTABLE', shutil.which('chromium') or '')} if os.getenv('CHROMIUM_EXECUTABLE') or shutil.which('chromium') else {})})
    raise SystemExit(result.returncode)
finally:
    server.terminate();server.wait(timeout=10)
