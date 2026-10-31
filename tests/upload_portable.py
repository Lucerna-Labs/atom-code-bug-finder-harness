#!/usr/bin/env python3
"""Upload a project, remove its source, run/export/reimport and reject hostile ZIPs."""
import io
import json
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from secrets import token_hex

ROOT = Path(__file__).resolve().parents[1]


def request(base, path, data=None, headers=None):
    options = {'X-Chaos-Local': '1', 'Origin': base} if data is not None else {}
    options.update(headers or {})
    with urllib.request.urlopen(urllib.request.Request(base+path, data=data, headers=options),timeout=10) as response:
        return response.status,response.read()


def archive(entries):
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as bundle:
        for name,body in entries.items():bundle.writestr(name,body)
    return output.getvalue()


def upload(base,identifier,data):
    return request(base,'/api/projects/import',data,{
        'Content-Type':'application/zip','X-Chaos-Project-Id':identifier,
        'X-Chaos-Project-Name':identifier})


def run(base,config_id):
    status,body=request(base,'/api/runs',json.dumps({'config_id':config_id}).encode(),{'Content-Type':'application/json'})
    assert status==202
    run_id=json.loads(body)['id']
    for _ in range(100):
        state=json.loads(request(base,'/api/runs/'+run_id)[1])['state']
        if state not in ('starting','running'):break
        time.sleep(.05)
    assert state=='succeeded',state
    receipt=json.loads(request(base,'/api/runs/'+run_id+'/receipt')[1])
    assert len(receipt['replays'])==10


def main():
    ids=['portable'+token_hex(4) for _ in range(3)]
    server=subprocess.Popen([sys.executable,str(ROOT/'web_app.py'),'--port','0'],
                            cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        announcement=server.stdout.readline().strip()
        assert announcement.startswith('Chaos Security Benchmark: http://127.0.0.1:'),announcement
        base=announcement.split(': ',1)[1]
        with tempfile.TemporaryDirectory(prefix='app-source-') as tmp:
            source=Path(tmp)/'original';source.mkdir()
            example=ROOT/'examples/ordinary_code'
            for name in ('program.py','target_jsonl.py','checker_jsonl.py'):
                (source/name).write_bytes((example/name).read_bytes())
            config=json.loads((example/'config.json').read_text())
            manifest=json.dumps({'format':'chaos-project-v1','config':config})
            packed=archive({**{p.name:p.read_bytes() for p in source.iterdir()},'chaos-project.json':manifest})
            status,body=upload(base,ids[0],packed)
            assert status==201 and json.loads(body)['config_ids']==[ids[0]]
            shutil.rmtree(source)
            packed=None
            run(base,ids[0])

            second=json.loads(request(base,'/api/configs/'+ids[0])[1])['config']
            second['name']='Second distinct property'
            second_id=ids[0]+'-check2'
            status,_=request(base,'/api/configs',json.dumps({'id':second_id,'config':second}).encode(),
                             {'Content-Type':'application/json'})
            assert status==201
            assert len(json.loads(request(base,'/api/projects/'+ids[0])[1])['config_ids'])==2

            status,bundle=request(base,'/api/projects/'+ids[0]+'/export',headers={'X-Chaos-Local':'1','Origin':base})
            assert status==200
            with zipfile.ZipFile(io.BytesIO(bundle)) as exported:
                assert set(exported.namelist())=={'program.py','target_jsonl.py','checker_jsonl.py','chaos-project.json'}
                portable=json.loads(exported.read('chaos-project.json'))
                assert len(portable['configs'])==2
                assert all(item['cwd']=='.' and item['source_paths']==config['source_paths']
                           for item in portable['configs'])
            status,body=upload(base,ids[1],bundle)
            assert status==201 and json.loads(body)['config_ids']==[ids[1],ids[1]+'-check2']
            run(base,ids[1])

            status,body=upload(base,ids[2],archive({name:(example/name).read_bytes()
                                                   for name in ('program.py','target_jsonl.py','checker_jsonl.py')}))
            assert status==201 and json.loads(body)['config_ids']==[]
            project=json.loads(request(base,'/api/projects/'+ids[2])[1])
            assert len(project['files'])==3
            manual=dict(config)
            manual['cwd']=project['path']
            manual['source_paths']=[project['path']+'/'+name for name in config['source_paths']]
            status,_=request(base,'/api/configs',json.dumps({'id':ids[2],'config':manual}).encode(),
                             {'Content-Type':'application/json'})
            assert status==201
            assert json.loads(request(base,'/api/projects/'+ids[2])[1])['config_ids']==[ids[2]]
            run(base,ids[2])
            status,configured=request(base,'/api/projects/'+ids[2]+'/export',headers={'X-Chaos-Local':'1','Origin':base})
            assert status==200
            with zipfile.ZipFile(io.BytesIO(configured)) as portable_zip:
                assert json.loads(portable_zip.read('chaos-project.json'))['config']['cwd']=='.'

            (ROOT/'projects'/ids[1]/'files'/'program.py').write_text('changed source')
            try:request(base,'/api/projects/'+ids[1]+'/export',headers={'X-Chaos-Local':'1','Origin':base})
            except urllib.error.HTTPError as error:assert error.code==409
            else:raise AssertionError('changed imported source was silently exported')

            hostile=[archive({'../escape.py':'x'}),archive({'/absolute.py':'x'}),
                     archive({'a\\b.py':'x'}),archive({'bomb.txt':'x'*2_000_000})]
            link=zipfile.ZipInfo('link.py');link.create_system=3
            link.external_attr=(stat.S_IFLNK|0o777)<<16
            output=io.BytesIO()
            with zipfile.ZipFile(output,'w') as z:z.writestr(link,'/tmp/target')
            hostile.append(output.getvalue())
            hostile.extend((archive({'chaos-project.json':'[]'}),
                            archive({'chaos-project.json':'x'*65537})))
            for index,data in enumerate(hostile):
                try:upload(base,'bad'+token_hex(4),data)
                except urllib.error.HTTPError as error:assert error.code==400,(index,error.code)
                else:raise AssertionError('unsafe ZIP accepted')
        print('Upload, source removal, run, two-config export/reimport/run, manual setup after manifest-free upload, changed-source refusal, seven unsafe ZIP rejections: passed')
    finally:
        server.terminate();server.wait(timeout=3)
        for identifier in ids:
            (ROOT/'configs'/(identifier+'.json')).unlink(missing_ok=True)
            (ROOT/'configs'/(identifier+'-check2.json')).unlink(missing_ok=True)
            path=ROOT/'projects'/identifier
            if path.exists():shutil.rmtree(path)


if __name__=='__main__':main()
