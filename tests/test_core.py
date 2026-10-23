# SPDX-License-Identifier: GPL-3.0-only
from pathlib import Path
import asyncio
import copy
import json
import sys
import tempfile
import time
import unittest
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'desktop'), str(ROOT / 'desktop/vendor')]
from handsover.config import Settings, Profile
from handsover.waveform import frames_for, pairing_url, qr_bitmap, legacy_packet, target_intensities
from handsover.engine import Engine, GameServer
from dglab_kit_python import COYOTE_WAVEFORM, COYOTE_WAVEFORMS
from websockets.asyncio.server import serve

DEVICE = {'slotId': 'test-coyote', 'name': 'Test Coyote', 'type': 'COYOTE_030',
    'props': {'connectState': 'connected', 'intensityA': 30, 'intensityB': 50},
    'slotState': {'hasDevice': True, 'channelA': {'intensityMax':100}, 'channelB': {'intensityMax':80}}}

class WaveformTests(unittest.TestCase):
    def test_both_qr_formats_decode_exactly_without_resampling(self):
        import zxingcpp
        for protocol, server in [('v4','wss://trex.dungeon-lab.cn/v4'),('v3','wss://ws.dungeon-lab.cn')]:
            url=pairing_url(server,'1059065f-4d45-48df-a636-14d26e366301',protocol)
            for size in (220,420):
                bitmap=qr_bitmap(url,size)
                result=zxingcpp.read_barcode(bitmap)
                self.assertIsNotNone(result)
                self.assertEqual(result.text,url)
            if protocol=='v3': self.assertEqual(url.count('#'),2)
    def test_all_presets_preserve_frequency_and_source(self):
        original = copy.deepcopy(COYOTE_WAVEFORMS)
        for waveform in COYOTE_WAVEFORM:
            for percent in (0, 20, 100):
                actual = frames_for(Profile(percent, 10000, waveform.value))
                self.assertEqual(len(actual), 100)
                source = COYOTE_WAVEFORMS[waveform]['raw']
                for i, f in enumerate(actual):
                    a, b = bytes.fromhex(f), bytes.fromhex(source[i % len(source)])
                    self.assertEqual(a[:4], b[:4])
                    self.assertEqual(a, b)
        self.assertEqual(original, COYOTE_WAVEFORMS)

    def test_invalid_profiles_are_rejected(self):
        for p in [Profile(-1), Profile(101), Profile(True), Profile(20, 50), Profile(20, 101), Profile(20, 10100), Profile(20, 300, 'missing')]:
            with self.assertRaises((ValueError, TypeError)): frames_for(p)

    def test_default_frames_and_v4_pairing(self):
        self.assertEqual(frames_for(Profile()), ['2D2D2D2D00000000', '2D2D2D2D64646464', '2D2D2D2D00000000'])
        url = pairing_url('wss://example.test/v4?region=cn', 'new-session')
        inner = parse_qs(urlsplit(url).query)['url'][0]
        self.assertEqual(parse_qs(urlsplit(inner).query), {'region': ['cn'], 'tid': ['new-session']})
        self.assertEqual(urlsplit(inner).path, '/v4')

    def test_legacy_short_feedback_is_padded_with_silence_without_repeating(self):
        source=frames_for(Profile())
        packet=legacy_packet(source)
        self.assertEqual(packet[:3],source)
        self.assertEqual(len(packet),10)
        self.assertTrue(all(f[8:]=='00000000' for f in packet[3:]))
        self.assertEqual(legacy_packet(packet),packet)

    def test_config_roundtrip_and_invalid_limits(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'settings.json'
            cfg = Settings(channels=[1], fake=Profile(7, 900))
            cfg.save(p)
            self.assertEqual(Settings.load(p), cfg)
            for obj in [Settings(channels=[True]), Settings(port=0), Settings(server='https://example.test'), Settings(channels=[0, 0])]:
                with self.assertRaises(ValueError): obj.validate()

    def test_numeric_targets_use_each_mobile_limit_not_current_strength(self):
        device=copy.deepcopy(DEVICE)
        self.assertEqual(target_intensities(device,'v4',20),{0:20,1:16})
        self.assertEqual(target_intensities(device,'v4',100),{0:100,1:80})
        self.assertEqual(target_intensities(device,'v4',0),{0:0,1:0})
        device['props'].update(intensityA=199,intensityB=0)
        device['slotState']['channelB']['intensityMax']=33
        self.assertEqual(target_intensities(device,'v4',20),{0:20,1:6})
        self.assertEqual(target_intensities({'props':{'limitA':100,'limitB':80}},'v3',20),{0:20,1:16})
        for invalid in [None,-1,201,True,float('nan')]:
            device['slotState']['channelA']['intensityMax']=invalid
            with self.assertRaises(ValueError): target_intensities(device,'v4',20)

class SpySDK:
    def __init__(self): self.calls, self.pending = [], []
    def send_pulse(self, client, slot, channel, duration, frames, options):
        self.calls.append(('pulse', client, slot, channel, duration, copy.deepcopy(frames), options))
        f = asyncio.get_running_loop().create_future()
        self.pending.append(f)
        return f
    def clear_operate(self, client, options):
        self.calls.append(('clear', client, options))
        for f in self.pending:
            if not f.done(): f.set_result({'reason': 'cleared'})
        f = asyncio.get_running_loop().create_future()
        f.set_result({})
        return f
    def reset_intensity(self, client, slot, channel, options):
        self.calls.append(('zero',client,slot,channel,options))
        f=asyncio.get_running_loop().create_future(); f.set_result({})
        return f
    def set_temp_intensity(self, client, slot, channel, target, duration, options):
        self.calls.append(('intensity',client,slot,channel,target,duration,options))
        f=asyncio.get_running_loop().create_future(); f.set_result({'reason':'completed'})
        return f
    async def destroy(self): pass

class EngineTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.events = []
        self.engine = Engine(Settings(), lambda k, v: self.events.append((k, v)))
        self.spy = SpySDK()
        self.engine.sdk = self.spy
        self.engine.selection = ('test-app', DEVICE['slotId'])
        self.engine.devices = {'test-app': [copy.deepcopy(DEVICE)]}
        self.engine.enabled = self.engine.game_active = True
    async def asyncTearDown(self): await self.engine.disconnect()

    async def test_two_channels_enqueue_without_waiting_for_completion(self):
        await asyncio.wait_for(self.engine.play('fake'), .2)
        pulse = [c for c in self.spy.calls if c[0] == 'pulse']
        self.assertEqual([c[3] for c in pulse], [0, 1])
        self.assertTrue(all(not f.done() for f in self.spy.pending))
        self.assertTrue(all(c[6]['immediate'] for c in pulse))
        self.assertEqual([(c[3],c[4],c[5]) for c in self.spy.calls if c[0]=='intensity'],[(0,20,300),(1,16,300)])
        await self.engine.play('real')
        self.assertEqual(len(self.spy.pending), 4)
        self.assertEqual(self.engine.devices['test-app'][0]['props']['intensityA'], 30)
        self.assertEqual(self.engine.devices['test-app'][0]['props']['intensityB'], 50)

    async def test_disabled_inactive_and_zero_never_play(self):
        self.engine.enabled = False
        await self.engine.play('real')
        self.engine.enabled = True
        self.engine.game_active = False
        await self.engine.play('real')
        self.engine.game_active = True
        self.engine.settings.real.percent = 0
        await self.engine.play('real')
        self.assertFalse(any(c[0] == 'pulse' for c in self.spy.calls))

    async def test_channel_selection_and_stop_clear_both(self):
        self.engine.settings.channels = [1]
        await self.engine.play('fake')
        self.assertEqual([c[3] for c in self.spy.calls if c[0] == 'pulse'], [1])
        await self.engine.stop('test', disable=True)
        self.assertFalse(self.engine.enabled)
        self.assertEqual([c[2]['channel'] for c in self.spy.calls if c[0] == 'clear'][-2:], [0, 1])
        self.assertEqual([c[3] for c in self.spy.calls if c[0]=='zero'],[1,1])

    async def test_disconnected_device_refuses_manual_output(self):
        self.engine.devices['test-app'][0]['props']['connectState'] = 'disconnected'
        with self.assertRaises(ValueError): await self.engine.play('fake', manual=True)
        self.assertFalse(self.spy.calls)

    async def test_connection_auto_enables_only_after_limits_arrive_and_sends_nothing(self):
        self.engine.enabled = False
        device=self.engine.devices['test-app'][0]
        del device['slotState']['channelA']['intensityMax']
        self.engine.publish_devices()
        self.assertFalse(self.engine.enabled)
        device['slotState']['channelA']['intensityMax']=100
        self.engine.publish_devices()
        self.assertTrue(self.engine.enabled)
        self.assertEqual([e for e in self.events if e==('enabled',True)],[('enabled',True)])
        self.assertFalse(self.spy.calls)
        self.engine.publish_devices()
        self.assertEqual(len([e for e in self.events if e==('enabled',True)]),1)

    async def test_manual_stop_stays_off_until_device_reconnects(self):
        self.engine.publish_devices()
        await self.engine.stop('stop button',disable=True)
        self.engine.publish_devices()
        self.assertFalse(self.engine.enabled)
        device=self.engine.devices['test-app'][0]
        device['props']['connectState']='disconnected'
        self.engine.publish_devices()
        await asyncio.sleep(.02)
        device['props']['connectState']='connected'
        self.engine.publish_devices()
        self.assertTrue(self.engine.enabled)
        await self.engine.set_enabled(False)
        self.engine.publish_devices()
        self.assertFalse(self.engine.enabled)

    async def test_manual_disable_while_waiting_is_respected_when_limits_arrive(self):
        self.engine.enabled=False
        device=self.engine.devices['test-app'][0]
        del device['slotState']['channelA']['intensityMax']
        self.engine.publish_devices()
        await self.engine.set_enabled(False)
        device['slotState']['channelA']['intensityMax']=100
        self.engine.publish_devices()
        self.assertFalse(self.engine.enabled)

    async def test_stop_invalidates_a_waiting_manual_command(self):
        await self.engine.lock.acquire()
        p = asyncio.create_task(self.engine.play('real', manual=True))
        await asyncio.sleep(0)
        s = asyncio.create_task(self.engine.stop(disable=True))
        await asyncio.sleep(0)
        self.engine.lock.release()
        await asyncio.gather(p, s)
        self.assertFalse(any(c[0] == 'pulse' for c in self.spy.calls))

    async def test_manual_works_without_game_or_enabled_link_and_survives_game_stop(self):
        self.engine.enabled = self.engine.game_active = False
        await self.engine.play('fake', manual=True)
        before=len(self.spy.calls)
        await self.engine.stop_game('pause')
        await self.engine.stop_game('game disconnected', disable=True)
        self.assertEqual(len(self.spy.calls), before)
        self.assertTrue(all(not f.done() for f in self.spy.pending))
        await self.engine.play('real', manual=True)
        self.assertEqual(len(self.spy.pending), 4)
        await self.engine.stop('stop button')
        self.assertTrue(all(f.done() for f in self.spy.pending))

    async def test_game_stop_cancels_game_feedback_but_not_queued_manual_test(self):
        await self.engine.play('real')
        await self.engine.lock.acquire()
        manual = asyncio.create_task(self.engine.play('fake', manual=True))
        await asyncio.sleep(0)
        stopped = asyncio.create_task(self.engine.stop_game('pause'))
        await asyncio.sleep(0)
        self.engine.lock.release()
        await asyncio.gather(manual, stopped)
        self.assertEqual(self.engine.output_source, 'manual')
        self.assertTrue(all(not f.done() for f in self.spy.pending[-2:]))

    async def test_phone_muted_channel_is_respected(self):
        self.engine.devices['test-app'][0]['slotState']['channelA'] = {'isMuted':True}
        await self.engine.play('fake',manual=True)
        self.assertEqual([c[3] for c in self.spy.calls if c[0]=='pulse'],[1])

    async def test_game_protocol_dedup_stale_and_pause(self):
        bridge = GameServer(self.engine, 0)
        await bridge.start()
        port = bridge.server.sockets[0].getsockname()[1]
        reader, writer = await asyncio.open_connection('127.0.0.1', port)
        async def send(kind, seq, action='', age=0, **kw):
            frame = dict(v=1, session='session', seq=seq, timestamp=int(time.time()*1000)-age,
                kind=kind, active=True, hooks=True, result='fake', action=action)
            frame.update(kw)
            writer.write((json.dumps(frame)+'\n').encode())
            await writer.drain()
            await asyncio.sleep(.025)
        try:
            await send('hello', 1)
            await send('result', 2, 'one')
            await send('result', 3, 'one')
            await send('result', 4, 'stale', age=5000)
            await send('result', 2, 'out-of-order')
            self.assertEqual(len([c for c in self.spy.calls if c[0] == 'pulse']), 2)
            await send('stop', 5, active=False, paused=True)
            self.assertFalse(self.engine.game_active)
            self.assertTrue(any(c[0] == 'clear' for c in self.spy.calls))
        finally:
            writer.close()
            await writer.wait_closed()
            await asyncio.sleep(.04)
            await bridge.close()

    async def test_frozen_heartbeat_disconnects_game(self):
        bridge = GameServer(self.engine, 0)
        await bridge.start()
        _, writer = await asyncio.open_connection('127.0.0.1', bridge.server.sockets[0].getsockname()[1])
        frame = dict(v=1, kind='hello', session='session', seq=1, timestamp=int(time.time()*1000), active=True, hooks=True)
        writer.write((json.dumps(frame)+'\n').encode())
        await writer.drain()
        await asyncio.sleep(1.95)
        self.assertTrue(self.engine.enabled)
        self.assertFalse(self.engine.game_active)
        writer.close()
        await writer.wait_closed()
        await bridge.close()

    async def test_repeated_paused_game_messages_do_not_cancel_manual_or_repaint_status(self):
        self.engine.enabled = self.engine.game_active = False
        bridge = GameServer(self.engine, 0)
        await bridge.start()
        _, writer = await asyncio.open_connection('127.0.0.1', bridge.server.sockets[0].getsockname()[1])
        async def send(kind, seq):
            frame = dict(v=1,kind=kind,session='paused-session',seq=seq,timestamp=int(time.time()*1000),
                active=False,paused=True,gameplay=True,hooks=True)
            writer.write((json.dumps(frame)+'\n').encode())
            await writer.drain()
            await asyncio.sleep(.025)
        try:
            await send('hello',1)
            await self.engine.play('real',manual=True)
            before=len(self.spy.calls)
            for seq in range(2,7): await send('stop' if seq%2 else 'heartbeat',seq)
            self.assertEqual(len(self.spy.calls),before)
            self.assertEqual(len([e for e in self.events if e[0]=='game']),1)
            writer.close()
            await writer.wait_closed()
            await asyncio.sleep(.04)
            self.assertEqual(len(self.spy.calls),before)
        finally:
            writer.close()
            await bridge.close()

class OfficialSDKIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_legacy_numeric_intensity_pulse_and_automatic_zero(self):
        captured=[]
        async def relay(ws):
            for f in [
                {'type':'bind','clientId':'controller','targetId':'','message':'targetId'},
                {'type':'bind','clientId':'controller','targetId':'phone','message':'200'},
                {'type':'msg','clientId':'controller','targetId':'phone','message':'strength-30+50+90+95'}]:
                await ws.send(json.dumps(f))
            async for raw in ws: captured.append(json.loads(raw))
        async with serve(relay,'127.0.0.1',0) as server:
            cfg=Settings(protocol='v3',server=f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}')
            e=Engine(cfg,lambda *a:None)
            await e.connect()
            for _ in range(100):
                if e.ready(): break
                await asyncio.sleep(.01)
            self.assertTrue(e.ready())
            self.assertEqual(e.device()['props']['intensityA'],30)
            self.assertEqual(e.device()['props']['intensityB'],50)
            await e.play('fake',manual=True)
            await asyncio.sleep(.35)
            await e.stop(disable=True)
            await e.disconnect()
        self.assertTrue(captured)
        self.assertTrue(all(f['type'] in ('clientMsg',3) or (f['type']==4 and f['message']=='clear' and f['channel'] in (1,2)) for f in captured))
        self.assertEqual([(f['channel'],f['strength']) for f in captured if f['type']==3],[(1,18),(2,19),(1,0),(2,0)])
        pulses=[f['message'] for f in captured if f['type']=='clientMsg']
        self.assertEqual(len(pulses),2)
        self.assertIn('2D2D2D2D64646464',pulses[0])
        packet=json.loads(pulses[0].split(':',1)[1])
        self.assertEqual(len(packet),10)
        self.assertTrue(all(f[8:]=='00000000' for f in packet[3:]))

    async def test_v4_wire_protocol_and_phone_updates(self):
        captured = []
        device = copy.deepcopy(DEVICE)
        async def relay(ws):
            await ws.send(json.dumps({'type':'hello', 'clientId':'controller-session'}))
            await ws.send(json.dumps({'type':'client_attached', 'clientId':'phone-app'}))
            async for raw in ws:
                f = json.loads(raw)
                if f.get('type') == 'ping':
                    await ws.send(json.dumps({'type':'pong'}))
                    continue
                if f.get('type') != 'message': continue
                data = f['data']
                captured.append(data)
                if data['m'] == 'devices.get':
                    result = {'devices':[device]}
                else: result = {'reason':'completed'}
                await ws.send(json.dumps({'type':'message', 'clientId':'phone-app',
                    'data':{'t':'resp','reqId':data['reqId'],'result':result}}))
                if data['m'] == 'devices.get':
                    await ws.send(json.dumps({'type':'message','clientId':'phone-app', 'data':{
                        't':'ev','ev':'slots.patch','slots':[{'slotId':device['slotId'], 'props':{'intensityA':44,'intensityB':61}}]}}))
        async with serve(relay, '127.0.0.1', 0) as server:
            cfg = Settings(server=f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/v4')
            e = Engine(cfg, lambda *a: None)
            await e.connect()
            for _ in range(100):
                if e.ready() and e.device()['props']['intensityA'] == 44: break
                await asyncio.sleep(.01)
            self.assertTrue(e.ready())
            self.assertEqual(e.device()['props']['intensityB'], 61)
            await e.play('fake', manual=True)
            await e.play('real', manual=True)
            await e.stop(disable=True)
            await e.disconnect()
        ops=[c['data'] for c in captured if c['m']=='device.op']
        pulses = [c for c in ops if c['t']==0]
        self.assertEqual([c['c'] for c in pulses], [0,1,0,1])
        self.assertEqual([c['d'] for c in pulses], [300,300,1000,1000])
        self.assertTrue(all(c['t'] == 0 and c['im'] and c['ver'] == 3 for c in pulses))
        self.assertTrue(all(c['m'] in ('devices.get','device.op','device.op.clear') for c in captured))
        targets=[c for c in ops if c['t']==4]
        self.assertEqual([(c['c'],c['v'],c['d']) for c in targets],[(0,20,300),(1,16,300),(0,100,1000),(1,80,1000)])
        self.assertTrue(all(c['v']==0 for c in ops if c['t']==7))
        self.assertFalse(any(c['t']==3 for c in ops))
        self.assertEqual(pulses[0]['v'][1], '2D2D2D2D64646464')
        self.assertEqual(pulses[2]['v'][1], '2D2D2D2D64646464')

if __name__ == '__main__': unittest.main(verbosity=2)
