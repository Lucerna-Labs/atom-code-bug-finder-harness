#!/usr/bin/env python3
"""Exercise actual HTTP GUI and MCP stdio protocol boundaries."""
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from secrets import token_hex

ROOT = Path(__file__).resolve().parents[1]


def web_call(base, path, payload=None, headers=None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(base + path, data=data,
        headers=({'Content-Type':'application/json','X-Chaos-Local':'1','Origin':base} if payload is not None else {}) | (headers or {}))
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.status, response.read()


def mcp_call(process, identifier, method, params):
    process.stdin.write(json.dumps({'jsonrpc':'2.0','id':identifier,'method':method,'params':params})+'\n')
    process.stdin.flush()
    line=process.stdout.readline()
    assert line, 'MCP server closed stdout'
    response=json.loads(line)
    assert response['id']==identifier and 'error' not in response, response
    return response['result']


def main():
    ui = subprocess.Popen([sys.executable,str(ROOT/'web_app.py'),'--port','0'],
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=ROOT)
    config_id='uitest'+token_hex(4)
    try:
        announcement=ui.stdout.readline().strip()
        assert announcement.startswith('Atom Code Bug Finder Harness: http://127.0.0.1:'),announcement
        base=announcement.split(': ',1)[1]
        status,html=web_call(base,'/')
        assert status==200 and b'Choose a configuration' in html
        assert b'Atom Code Bug Finder Harness' in html
        assert b'By Lucerna Labs' in html and b'A Division of Lucerna Media' in html
        health=json.loads(web_call(base,'/api/health')[1])
        assert health['app']=='atom-code-bug-finder-harness'
        assert health['name']=='Atom Code Bug Finder Harness'
        status,js=web_call(base,'/app.js')
        assert status==200 and b'startRun' in js
        try:
            web_call(base,'/api/runs',{'config_id':'example'},{'X-Chaos-Local':'0'})
        except urllib.error.HTTPError as error:
            assert error.code==403
        else:raise AssertionError('POST without local marker accepted')

        example=json.loads(web_call(base,'/api/configs/example')[1])['config']
        project=ROOT/'examples/ordinary_code'
        example['cwd']=str(project)
        example['source_paths']=[str(project/p) for p in example['source_paths']]
        status,created=web_call(base,'/api/configs',{'id':config_id,'config':example})
        assert status==201 and json.loads(created)['id']==config_id
        status,started=web_call(base,'/api/runs',{'config_id':config_id})
        assert status==202
        run_id=json.loads(started)['id']
        for _ in range(100):
            state=json.loads(web_call(base,'/api/runs/'+run_id)[1])['state']
            if state not in ('starting','running'):break
            time.sleep(.05)
        assert state=='succeeded',state
        receipt=json.loads(web_call(base,'/api/runs/'+run_id+'/receipt')[1])
        assert len(receipt['replays'])==10
        assert receipt['gates']['all_witnesses_replay_identically']=='MEASURED'
    finally:
        ui.terminate()
        ui.wait(timeout=3)
        (ROOT/'configs'/(config_id+'.json')).unlink(missing_ok=True)

    modern = subprocess.Popen([sys.executable,str(ROOT/'mcp_server.py')],
                              stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              text=True,cwd=ROOT)
    try:
        meta={'_meta':{'io.modelcontextprotocol/protocolVersion':'2026-07-28',
                       'io.modelcontextprotocol/clientCapabilities':{}}}
        discovered=mcp_call(modern,1,'server/discover',meta)
        assert '2026-07-28' in discovered['supportedVersions']
        assert discovered['_meta']['io.modelcontextprotocol/serverInfo']['name']=='atom-code-bug-finder-harness'
        tools=mcp_call(modern,2,'tools/list',meta)['tools']
        assert {t['name'] for t in tools}>={'list_configs','start_run','read_receipt'}
        configs=mcp_call(modern,3,'tools/call',{**meta,'name':'list_configs','arguments':{}})
        assert configs['structuredContent']['configs'][0]['id']=='example'
        started=mcp_call(modern,4,'tools/call',{**meta,'name':'start_run','arguments':{'config_id':'example'}})
        assert not started['isError']
        run_id=started['structuredContent']['id']
        for number in range(100,200):
            state=mcp_call(modern,number,'tools/call',{**meta,'name':'get_run','arguments':{'run_id':run_id}})['structuredContent']['state']
            if state not in ('starting','running'):break
            time.sleep(.05)
        assert state=='succeeded',state
        receipt=mcp_call(modern,201,'tools/call',{**meta,'name':'read_receipt','arguments':{'run_id':run_id}})
        assert len(receipt['structuredContent']['replays'])==10
    finally:
        modern.stdin.close()
        assert modern.wait(timeout=3)==0,modern.stderr.read()

    legacy = subprocess.Popen([sys.executable,str(ROOT/'mcp_server.py')],
                              stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=ROOT)
    try:
        init=mcp_call(legacy,1,'initialize',{'protocolVersion':'2025-11-25',
            'capabilities':{},'clientInfo':{'name':'test','version':'1'}})
        assert init['protocolVersion']=='2025-11-25'
        assert len(mcp_call(legacy,2,'tools/list',{})['tools'])>=6
    finally:
        legacy.stdin.close()
        assert legacy.wait(timeout=3)==0,legacy.stderr.read()
    print('GUI HTTP and MCP modern/legacy boundaries: config save, runs, receipt, 403 gate, seven tools passed')


if __name__=='__main__':
    main()
