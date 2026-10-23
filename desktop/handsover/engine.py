# SPDX-License-Identifier: GPL-3.0-only
"""Channel targets are floor(APP-reported limit * result percentage / 100)."""
import asyncio
import copy
import json
import logging
import time
import re
from collections import deque
from dglab_kit_python import DglabSocket
from .config import Settings
from .waveform import frames_for, pairing_url, legacy_packet, target_intensities, channel_limits

LOG = logging.getLogger(__name__)

class Engine:
    def __init__(self, settings: Settings, emit, sdk_factory=DglabSocket):
        self.settings = copy.deepcopy(settings.validate())
        self.emit = emit
        self.factory = sdk_factory
        self.sdk = None
        self.selection = None
        self.devices = {}
        self.enabled = False
        self.game_active = False
        self.lock = asyncio.Lock()
        self.pending = set()
        self.generation = 0
        self.stop_epoch = 0
        self.game_epoch = 0
        self.output_source = None
        self.closing = False
        self.legacy_timers = []
        self.controlled_channels = set()
        self.last_phone_sample = None
        self.auto_enable_pending = True
        self.ready_connection = None
        self.connection_cleanup = None

    def notify(self, text):
        LOG.info(text)
        self.emit('log', text)

    def invalidate_disconnected_feedback(self):
        self.generation += 1
        self.stop_epoch += 1
        self.output_source = None
        for future in self.legacy_timers:
            if not future.done(): future.cancel()
        self.legacy_timers.clear()
        self.controlled_channels.clear()

    async def connect(self):
        await self.disconnect()
        sdk = self.factory(url=self.settings.server, version=self.settings.protocol, connect_timeout=8000, response_timeout=8000)
        self.sdk = sdk
        def state(value, *args):
            if self.sdk is not sdk: return
            status = getattr(value, 'value', value)
            self.emit('phone', str(status))
            if status == 'disconnected':
                self.invalidate_disconnected_feedback()
                self.enabled = False
                self.auto_enable_pending = True
                self.ready_connection = None
                self.devices.clear()
                self.selection = None
                self.emit('enabled', False)
                self.emit('devices', [])
                self.emit('qr', None)
        async def attached(client_id, *args):
            if self.sdk is not sdk: return
            self.notify('手机已接入，正在读取设备。')
            if self.settings.protocol == 'v3':
                legacy_device({}, client_id)
                return
            # The pinned SDK's request_devices applies its response twice, which
            # can overwrite a slots.patch received immediately after the response.
            # send() uses the same official RPC while letting the reader merge once.
            try: await sdk.send(client_id, {'t': 'req', 'm': 'devices.get'})
            except Exception as e: self.emit('error', '读取设备失败：' + str(e))
        async def detached(client_id, *args):
            if self.sdk is not sdk: return
            self.devices.pop(client_id, None)
            if self.selection and self.selection[0] == client_id:
                self.invalidate_disconnected_feedback()
                self.enabled = False
                self.auto_enable_pending = True
                self.ready_connection = None
                self.selection = None
                self.emit('enabled', False)
            self.publish_devices()
        def devices(items, client_id):
            if self.sdk is not sdk: return
            self.devices[client_id] = copy.deepcopy(items)
            self.publish_devices()
        def legacy_device(item, client_id):
            if self.sdk is not sdk or self.settings.protocol != 'v3': return
            if item.get('removed'):
                self.devices.pop(client_id, None)
            else:
                old = self.devices.get(client_id, [{}])[0]
                props = old.get('props', {'connectState': 'waiting', 'intensityA': '—', 'intensityB': '—'})
                self.devices[client_id] = [{'slotId': 'legacy-coyote-3', 'name': '郊狼 3.0 · 兼容连接',
                    'type': 'COYOTE_030', 'props': props, 'slotState': {'hasDevice': True}}]
            self.publish_devices()
        def legacy_data(message, client_id=None):
            if self.sdk is not sdk or self.settings.protocol != 'v3' or not isinstance(message, str): return
            match = re.fullmatch(r'strength-(\d+)[+\-](\d+)[+\-](\d+)[+\-](\d+)', message)
            client_id = sdk.paired_client_id
            if match and client_id:
                legacy_device({}, client_id)
                a, b, limit_a, limit_b = map(int, match.groups())
                self.devices[client_id][0]['props'].update(connectState='connected', intensityA=a, intensityB=b,
                    limitA=limit_a, limitB=limit_b)
                self.publish_devices()
        sdk.on('state', state)
        sdk.on('client-attached', attached)
        sdk.on('client-disconnected', detached)
        sdk.on('devices', devices)
        sdk.on('device', legacy_device)
        sdk.on('data', legacy_data)
        sdk.on('error', lambda *a: self.emit('error', '手机链路错误：' + str(a[0]) if a else '手机链路错误'))
        try:
            result = await sdk.connect()
            if self.sdk is sdk:
                self.emit('qr', pairing_url(self.settings.server, result['targetId'], self.settings.protocol))
                self.notify('二维码已生成。' + ('请使用 DG-LAB 4 APP 扫码。' if self.settings.protocol == 'v4' else '当前为兼容扫码格式，等待手机连接。'))
        except Exception:
            if self.sdk is sdk:
                await self.disconnect()
            raise

    def publish_devices(self):
        items = [(client, d) for client, devices in self.devices.items() for d in devices if d.get('type') == 'COYOTE_030']
        valid = {(client, d['slotId']) for client, d in items}
        if self.selection and self.selection not in valid:
            self.invalidate_disconnected_feedback()
            self.selection = None
            self.enabled = False
            self.auto_enable_pending = True
            self.ready_connection = None
            self.emit('enabled', False)
        if self.selection is None and len(items) == 1:
            self.selection = (items[0][0], items[0][1]['slotId'])
        self.emit('devices', {'items': items, 'selection': self.selection})
        device = self.device()
        if device:
            props = device.get('props', {})
            sample = (props.get('intensityA'), props.get('intensityB'), *channel_limits(device, self.settings.protocol))
            if sample != self.last_phone_sample:
                self.last_phone_sample = sample
                LOG.info('Phone report: actual A=%s B=%s; limits A=%s B=%s; connectState=%r hasDevice=%r',
                    *sample, props.get('connectState'), device.get('slotState', {}).get('hasDevice'))
        connected = self.selection if self.ready() else None
        if self.ready_connection and connected != self.ready_connection:
            self.enabled = False
            self.auto_enable_pending = True
            self.emit('enabled', False)
            if self.connection_cleanup is None:
                async def cleanup():
                    try: await self.stop('设备断开或状态不可用')
                    finally:
                        self.connection_cleanup = None
                        self.publish_devices()
                self.connection_cleanup = asyncio.create_task(cleanup())
        self.ready_connection = connected
        if connected and self.auto_enable_pending and not self.connection_cleanup and not self.closing:
            try: target_intensities(device, self.settings.protocol, 100, self.settings.channels)
            except ValueError: return
            self.auto_enable_pending = False
            self.enabled = True
            self.emit('enabled', True)
            self.notify('设备已连接，上限已读取，已自动开启游戏联动。')

    def device(self):
        if not self.selection: return None
        client, slot = self.selection
        return next((d for d in self.devices.get(client, []) if d.get('slotId') == slot), None)

    def ready(self):
        d = self.device()
        if not self.sdk or not d: return False
        props, slot = d.get('props', {}), d.get('slotState', {})
        return props.get('connectState') == 'connected' and slot.get('hasDevice', True) is not False

    async def select(self, selection):
        await self.stop('切换设备', disable=True)
        self.selection = tuple(selection) if selection else None
        self.ready_connection = None
        self.auto_enable_pending = True
        self.publish_devices()

    async def apply(self, settings):
        settings.validate()
        if settings.port != self.settings.port:
            raise ValueError('本机监听端口在配置文件修改后重启生效；游戏插件的端口也需保持一致。')
        old_server = self.settings.server
        old_protocol = self.settings.protocol
        if old_server != settings.server or old_protocol != settings.protocol:
            await self.disconnect()
        else:
            await self.stop('配置已更新')
        self.settings = copy.deepcopy(settings)
        settings.save()
        self.notify('设置已保存。实际强度按手机各通道上限乘以结果比例计算。')

    async def set_enabled(self, value):
        if value and not self.ready(): raise ValueError('请先扫码并连接郊狼 3.0 设备。')
        if value: target_intensities(self.device(), self.settings.protocol, 100, self.settings.channels)
        self.auto_enable_pending = False
        self.enabled = bool(value)
        if not value: await self.stop('已关闭联动')
        self.emit('enabled', self.enabled)

    def observe(self, future, generation):
        self.pending.add(future)
        def done(f):
            self.pending.discard(f)
            if f.cancelled(): return
            error = f.exception()
            if error and generation == self.generation and not self.closing:
                LOG.warning('Pulse operation failed: %s', error)
                self.emit('error', '波形任务失败：' + str(error))
                asyncio.create_task(self.stop('任务失败', disable=True))
            elif not error and generation == self.generation and self.settings.protocol == 'v4':
                result = f.result()
                LOG.info('APP task acknowledged: reason=%s', result.get('reason') if isinstance(result, dict) else result)
        future.add_done_callback(done)

    async def play(self, kind, manual=False):
        if kind not in ('fake', 'real'): raise ValueError('未知结果。')
        requested_stop, requested_game = self.stop_epoch, self.game_epoch
        async with self.lock:
            if requested_stop != self.stop_epoch or (not manual and requested_game != self.game_epoch): return
            if not manual and (not self.enabled or not self.game_active): return
            if not self.ready():
                if manual: raise ValueError('手机设备尚未连接，无法测试。')
                return
            profile = getattr(self.settings, kind)
            frames = frames_for(profile)
            self.generation += 1
            gen = self.generation
            self.output_source = 'manual' if manual else 'game'
            if not self.settings.channels or profile.percent == 0:
                await asyncio.wait_for(asyncio.shield(self._clear()), timeout=2)
                self.emit('output', '本次比例为 0% 或未选择通道，未输出。')
                return
            client, slot = self.selection
            slots = self.device().get('slotState', {})
            channels = [c for c in self.settings.channels if not slots.get('channelA' if c == 0 else 'channelB', {}).get('isMuted', False)]
            if not channels:
                await asyncio.wait_for(asyncio.shield(self._clear()), timeout=2)
                self.emit('output', '所选通道已在手机静音，未发送波形。')
                return
            try: targets = target_intensities(self.device(), self.settings.protocol, profile.percent, channels)
            except ValueError as e:
                await asyncio.wait_for(asyncio.shield(self._clear()), timeout=2)
                if manual: raise
                self.emit('error', str(e))
                return
            await asyncio.wait_for(asyncio.shield(self._clear()), timeout=2)
            if gen != self.generation: return
            # Reset the base first. A temporary V4 intensity then has a zero
            # baseline and expires back to zero rather than adding to a prior value.
            if self.settings.protocol == 'v4':
                resets = [self.sdk.reset_intensity(client, slot, c, {'immediate': True}) for c in channels]
                await asyncio.wait_for(asyncio.gather(*resets), timeout=2)
                if gen != self.generation: return
                targets = target_intensities(self.device(), self.settings.protocol, profile.percent, channels)
            self.controlled_channels.update(channels)
            if self.settings.protocol == 'v3':
                await asyncio.sleep(.15)
                if gen != self.generation: return
                targets = target_intensities(self.device(), self.settings.protocol, profile.percent, channels)
                for channel, target in targets.items(): self.sdk.set_strength(channel + 1, target)
                self._send_legacy_packet(channels, frames[:10])
                started = asyncio.get_running_loop().time()
                async def remaining():
                    for offset in range(10, len(frames), 10):
                        await asyncio.sleep(max(0, started + offset / 10 - asyncio.get_running_loop().time()))
                        if gen != self.generation: return
                        self._send_legacy_packet(channels, frames[offset:offset+10])
                    await asyncio.sleep(max(0, started + profile.duration_ms / 1000 - asyncio.get_running_loop().time()))
                    if gen == self.generation:
                        for c in channels:
                            self.sdk.set_strength(c + 1, 0)
                            self.sdk.clear_pulse(c + 1)
                        self.controlled_channels.difference_update(channels)
                future = asyncio.create_task(remaining())
                self.legacy_timers.append(future)
                self.observe(future, gen)
            # Both SDK calls enqueue before awaiting completion: A and B run concurrently.
            for channel in channels if self.settings.protocol == 'v4' else []:
                strength = self.sdk.set_temp_intensity(client, slot, channel, targets[channel], profile.duration_ms,
                    {'immediate': True, 'timeout': profile.duration_ms + 3000})
                self.observe(strength, gen)
                future = self.sdk.send_pulse(client, slot, channel, profile.duration_ms, frames,
                    {'immediate': True, 'version': 3, 'timeout': profile.duration_ms + 3000})
                self.observe(future, gen)
            numbers = ' / '.join(f'{"AB"[c]} {v}' for c, v in targets.items())
            text = f"{'假牙' if kind == 'fake' else '真牙'} · 上限的 {profile.percent}% → {numbers} · {profile.duration_ms / 1000:g} 秒"
            self.emit('output', text)
            self.notify(('手动测试：' if manual else '游戏事件：') + text)

    def _send_legacy_packet(self, channels, frames):
        packet = legacy_packet(frames)
        for channel in channels:
            letter = 'A' if channel == 0 else 'B'
            # type=4 is NOT a pulse transport on the live relay: it can be
            # interpreted as setting intensity to zero. Use the official SDK's
            # clientMsg waveform operation, with a single 1-second packet.
            self.sdk.send_pulse({'channel': letter, 'time': 1, 'data': packet})

    async def _clear(self):
        if self.sdk and self.selection:
            client, slot = self.selection
            if self.settings.protocol == 'v3':
                for channel in (1, 2): self.sdk.clear_pulse(channel)
                for channel in self.controlled_channels: self.sdk.set_strength(channel + 1, 0)
                self.controlled_channels.clear()
                for future in self.legacy_timers:
                    if not future.done(): future.cancel()
                self.legacy_timers.clear()
                return
            futures = [self.sdk.clear_operate(client, {'slotId': slot, 'channel': c}) for c in (0, 1)]
            zeros = [self.sdk.reset_intensity(client, slot, c, {'immediate': True}) for c in self.controlled_channels]
            self.controlled_channels.clear()
            for result in await asyncio.gather(*futures, *zeros, return_exceptions=True):
                if isinstance(result, Exception): LOG.warning('Task cleanup: %s', result)

    async def stop(self, reason='停止输出', disable=False):
        self.stop_epoch += 1
        self.generation += 1
        if disable:
            self.enabled = False
            self.auto_enable_pending = False
            self.emit('enabled', False)
        async with self.lock:
            try: await asyncio.wait_for(asyncio.shield(self._clear()), timeout=2)
            except (TimeoutError, ConnectionError): LOG.warning('Cleanup unavailable; finite pulse tasks expire on APP.')
            self.output_source = None
        self.emit('output', reason)

    async def stop_game(self, reason, disable=False):
        """Game lifecycle updates never cancel independent manual tests."""
        self.game_epoch += 1
        if disable:
            self.enabled = False
            self.emit('enabled', False)
        if self.output_source != 'game': return
        self.generation += 1
        async with self.lock:
            # A manual command may have acquired the lock before this cleanup.
            if self.output_source != 'game': return
            try: await asyncio.wait_for(asyncio.shield(self._clear()), timeout=2)
            except (TimeoutError, ConnectionError): LOG.warning('Game cleanup unavailable; finite tasks expire on APP.')
            self.output_source = None
        self.emit('output', reason)

    async def disconnect(self):
        await self.stop('手机未连接', disable=True)
        sdk, self.sdk = self.sdk, None
        self.selection = None
        self.devices.clear()
        self.controlled_channels.clear()
        self.ready_connection = None
        self.auto_enable_pending = True
        self.emit('devices', [])
        self.emit('qr', None)
        self.emit('phone', 'disconnected')
        if sdk:
            try: await sdk.destroy()
            except Exception: LOG.exception('SDK close')

class GameServer:
    def __init__(self, engine, port=17896):
        self.engine, self.port = engine, port
        self.server = None
        self.writer = None
        self.seen = set()
        self.order = deque()
        self.last_status = None

    async def start(self):
        self.server = await asyncio.start_server(self.handle, '127.0.0.1', self.port, limit=4096)

    async def handle(self, reader, writer):
        if self.writer:
            writer.close()
            await writer.wait_closed()
            return
        self.writer = writer
        session, sequence = None, -1
        try:
            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=1.8)
                if not line: break
                frame = json.loads(line)
                if frame.get('v') != 1: raise ValueError('游戏插件协议版本不匹配。')
                if type(frame.get('seq')) is not int or type(frame.get('timestamp')) is not int: raise ValueError('无效事件序号或时间。')
                if abs(time.time() * 1000 - frame['timestamp']) > 1500: continue
                if session is None:
                    if frame.get('kind') != 'hello' or not isinstance(frame.get('session'), str): raise ValueError('缺少游戏握手。')
                    session = frame['session']
                if frame.get('session') != session or frame['seq'] <= sequence: continue
                sequence = frame['seq']
                was_active = self.engine.game_active
                self.engine.game_active = frame.get('active') is True and frame.get('paused') is not True and frame.get('hooks') is True
                status = {'connected': True, 'active': self.engine.game_active,
                    'paused': frame.get('paused') is True, 'hooks': frame.get('hooks') is True,
                    'gameplay': frame.get('gameplay', False) is True}
                if status != self.last_status:
                    self.last_status = status
                    self.engine.emit('game', status)
                if frame.get('kind') == 'stop' or not self.engine.game_active:
                    if frame.get('kind') == 'stop' or was_active:
                        await self.engine.stop_game('游戏暂停或不在对局中')
                elif frame.get('kind') == 'result':
                    action = frame.get('action')
                    if not isinstance(action, str) or not action: continue
                    key = (session, action)
                    if key in self.seen: continue
                    self.seen.add(key)
                    self.order.append(key)
                    if len(self.order) > 1024: self.seen.discard(self.order.popleft())
                    await self.engine.play(frame.get('result'))
        except (ConnectionError, TimeoutError): pass
        except Exception as e:
            LOG.warning('Game connection closed: %s', e)
            self.engine.emit('log', '游戏连接异常：' + str(e))
        finally:
            self.engine.game_active = False
            await self.engine.stop_game('游戏连接已断开')
            self.engine.emit('game', {'connected': False, 'active': False, 'hooks': False})
            self.last_status = None
            writer.close()
            try: await writer.wait_closed()
            except Exception: pass
            self.writer = None

    async def close(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        if self.writer: self.writer.close()
