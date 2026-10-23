# SPDX-License-Identifier: GPL-3.0-only
"""Isolated relay probes. Simulated phone only; never connects real hardware."""
import asyncio
import json
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlsplit

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'desktop'),str(ROOT/'desktop/vendor')]
from dglab_kit_python import DglabSocket
from handsover.waveform import pairing_url
from handsover.config import Settings
from handsover.engine import Engine
from websockets.asyncio.client import connect


async def legacy():
    events=[]
    engine=Engine(Settings(protocol='v3',server='wss://ws.dungeon-lab.cn'),lambda k,v:events.append((k,v)))
    await engine.connect()
    sdk=engine.sdk
    controller=sdk.target_id
    async with connect('wss://ws.dungeon-lab.cn') as phone:
        phone_id=json.loads(await phone.recv())['clientId']
        await phone.send(json.dumps(dict(type='bind',clientId=controller,targetId=phone_id,message='DGLAB')))
        await asyncio.wait_for(phone.recv(),5)
        await phone.send(json.dumps(dict(type='msg',clientId=controller,targetId=phone_id,message='strength-30+50+90+95')))
        for _ in range(50):
            if engine.ready(): break
            await asyncio.sleep(.02)
        await engine.play('fake',manual=True)
        received=[]
        while len([f for f in received if f.startswith('pulse-')])<2:
            received.append(json.loads(await asyncio.wait_for(phone.recv(),3))['message'])
        assert all(m.startswith(('clear-','pulse-','strength-')) for m in received),received
        assert 'strength-1+2+18' in received and 'strength-2+2+19' in received,received
        for message in received:
            if not message.startswith('pulse-'): continue
            packet=json.loads(message.split(':',1)[1])
            assert len(packet)==10 and packet[1]=='2D2D2D2D64646464'
            assert all(f[8:]=='00000000' for f in packet[3:])
        print('V3 live relay: targets A=18 B=19 from limits 90/95 at 20%, original waveform and silent tail delivered',flush=True)
        await engine.disconnect()


async def v4():
    sdk=DglabSocket(url='wss://trex.dungeon-lab.cn/v4',version='v4')
    result=await sdk.connect()
    url=parse_qs(urlsplit(pairing_url('wss://trex.dungeon-lab.cn/v4',result['targetId'])).query)['url'][0]
    attached=[]
    sdk.on('client-attached',lambda *a:attached.append(True))
    try:
        async with connect(url) as phone:
            first=json.loads(await asyncio.wait_for(phone.recv(),5))
            await asyncio.sleep(.25)
            print('V4 QR endpoint first=',first.get('type'),'paired=',bool(attached),flush=True)
    finally: await sdk.destroy()


async def main():
    for fn in (legacy,v4):
        try: await asyncio.wait_for(fn(),25)
        except Exception as e: print(fn.__name__,type(e).__name__,str(e),flush=True)

if __name__=='__main__':asyncio.run(main())
