# SPDX-License-Identifier: GPL-3.0-only
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import urlsplit
import json
import math
import os

DATA_DIR = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'HandsOverDGLab'

@dataclass
class Profile:
    percent: int = 20
    duration_ms: int = 300
    waveform: str = 'BUBBLE'

    def validate(self):
        if type(self.percent) is not int or not 0 <= self.percent <= 100:
            raise ValueError('波形比例必须是 0～100 的整数。')
        if type(self.duration_ms) is not int or not 100 <= self.duration_ms <= 10000 or self.duration_ms % 100:
            raise ValueError('持续时间应为 0.1～10 秒，步长 0.1 秒。')
        from dglab_kit_python import COYOTE_WAVEFORM
        COYOTE_WAVEFORM(self.waveform)
        return self

@dataclass
class Settings:
    version: int = 2
    protocol: str = 'v4'
    server: str = 'wss://trex.dungeon-lab.cn/v4'
    port: int = 17896
    channels: list[int] = field(default_factory=lambda: [0, 1])
    fake: Profile = field(default_factory=Profile)
    real: Profile = field(default_factory=lambda: Profile(100, 1000))

    def validate(self):
        u = urlsplit(self.server)
        if u.scheme not in ('ws', 'wss') or not u.hostname or u.username or u.password or u.fragment:
            raise ValueError('请输入有效的 ws:// 或 wss:// 中继地址，不包含账户信息或片段。')
        if type(self.port) is not int or not 1024 <= self.port <= 65535:
            raise ValueError('本机端口应在 1024～65535 之间。')
        if type(self.version) is not int or self.version != 2:
            raise ValueError('配置版本不受支持。')
        if self.protocol not in ('v3', 'v4'):
            raise ValueError('扫码协议必须为 v3 或 v4。')
        if not isinstance(self.channels, list) or len(set(self.channels)) != len(self.channels) or any(type(c) is not int or c not in (0, 1) for c in self.channels):
            raise ValueError('通道只能选择 A、B 或同时选择两路。')
        self.fake.validate()
        self.real.validate()
        return self

    def save(self, path=None):
        self.validate()
        path = Path(path) if path else DATA_DIR / 'settings.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        tmp.replace(path)

    @classmethod
    def load(cls, path=None):
        path = Path(path) if path else DATA_DIR / 'settings.json'
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        if data.get('version') == 1: data['version'] = 2
        return cls(**{**data, 'fake': Profile(**data['fake']), 'real': Profile(**data['real'])}).validate()
