# SPDX-License-Identifier: GPL-3.0-only
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit, quote
from dglab_kit_python import COYOTE_WAVEFORM, COYOTE_WAVEFORMS
from .config import Profile

def frames_for(profile: Profile) -> list[str]:
    """Repeat/trim original waveform. Percentage controls channel intensity."""
    profile.validate()
    raw = COYOTE_WAVEFORMS[COYOTE_WAVEFORM(profile.waveform)]['raw']
    scaled = []
    for frame in raw:
        data = bytes.fromhex(frame)
        if len(data) != 8 or any(v > 100 for v in data[4:]):
            raise ValueError('官方波形帧格式不符合郊狼 3.0 规范。')
        scaled.append(data.hex().upper())
    if not scaled:
        raise ValueError('波形内容为空。')
    return [scaled[i % len(scaled)] for i in range(profile.duration_ms // 100)]


def channel_limits(device, protocol):
    """Use current APP-reported limits; never guess a missing cap."""
    import math
    values = []
    for channel in ('A', 'B'):
        value = (device or {}).get('props', {}).get('limit' + channel) if protocol == 'v3' else (
            (device or {}).get('slotState', {}).get('channel' + channel, {}).get('intensityMax'))
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 200:
            values.append(None)
        else: values.append(math.floor(value))
    return values


def target_intensities(device, protocol, percent, channels=(0, 1)):
    if type(percent) is not int or not 0 <= percent <= 100: raise ValueError('强度比例应为 0～100%。')
    limits = channel_limits(device, protocol)
    targets = {}
    for channel in channels:
        if limits[channel] is None: raise ValueError(f'手机尚未上报 {"AB"[channel]} 通道上限，请在手机确认通道设置。')
        targets[channel] = limits[channel] * percent // 100
    return targets

def pairing_url(server: str, target_id: str, protocol='v4') -> str:
    parts = urlsplit(server)
    if protocol == 'v3':
        socket_url = urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip('/') + '/' + target_id, parts.query, ''))
        return 'https://www.dungeon-lab.com/app-download.php#DGLAB-SOCKET#' + socket_url
    params = [(k, v) for k, v in parse_qsl(parts.query) if k != 'tid'] + [('tid', target_id)]
    # The live official relay accepts /v4 but returns HTTP 404 for /v4/.
    # Preserve the configured path rather than inventing a trailing slash.
    socket_url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(params), ''))
    return 'https://dungeon-lab.cn/s/?v=1&action=socket&url=' + quote(socket_url, safe='')


def legacy_packet(frames: list[str]) -> list[str]:
    """Public legacy relay expects exactly one second (10 frames) per message.

    It repeats shorter arrays and truncates longer arrays. Pad only with silence
    so a 0.3-second feedback never becomes a 1-second repeating stimulus.
    """
    if not 1 <= len(frames) <= 10: raise ValueError('兼容模式每包应为 1～10 帧。')
    return list(frames) + [frames[-1][:8] + '00000000'] * (10 - len(frames))

def qr_bitmap(url, minimum=260):
    import qrcode
    qr = qrcode.QRCode(box_size=1, border=4, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(url)
    qr.make(fit=True)
    # Integer modules only: never blur a QR by resizing it to an arbitrary size.
    qr.box_size = max(3, minimum // len(qr.get_matrix()))
    return qr.make_image(fill_color='black', back_color='white').convert('RGB')
