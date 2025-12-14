import time
from enum import Enum
from typing import Dict, List

from core.tts import TTS_CLASS_MAP


class ObjectState(Enum):
    SAFE = 0
    NEARBY = 1
    APPROACHING = 2


APPROACH_CONFIRM_TIME = 0.8
LEAVE_CONFIRM_TIME = 1.2
EXPIRE_TIME = 2.0

WARN_COOLDOWN = 5.0
GLOBAL_WARN_COOLDOWN = 4.0

ENV_WARN_COOLDOWN = 10.0


class TrackedObject:
    def __init__(self, obj_id, cls_name):
        self.id = obj_id
        self.cls = cls_name

        self.state = ObjectState.NEARBY

        self.first_seen = time.time()
        self.last_seen = time.time()

        self.approach_since = None
        self.leave_since = None

        self.last_warned = None


class WarningManager:
    def __init__(self):
        self.objects: Dict[int, TrackedObject] = {}

        self.env_last_warned: Dict[str, float] = {}
        self.env_muted = set()
        self.last_env: Dict = {}

        self.env_alert_enabled: bool = True
        self.global_last_warned: float | None = None


    def update_object(self, obj_id, cls_name, is_approaching):
        now = time.time()

        if obj_id not in self.objects:
            self.objects[obj_id] = TrackedObject(obj_id, cls_name)

        obj = self.objects[obj_id]
        obj.last_seen = now

        if obj.state == ObjectState.NEARBY:
            if is_approaching:
                if obj.approach_since is None:
                    obj.approach_since = now
                elif now - obj.approach_since >= APPROACH_CONFIRM_TIME:
                    obj.state = ObjectState.APPROACHING
                    obj.approach_since = None
                    obj.leave_since = None
                    return obj
            else:
                obj.approach_since = None

        elif obj.state == ObjectState.APPROACHING:
            if not is_approaching:
                if obj.leave_since is None:
                    obj.leave_since = now
                elif now - obj.leave_since >= LEAVE_CONFIRM_TIME:
                    obj.state = ObjectState.NEARBY
                    obj.leave_since = None
            else:
                obj.leave_since = None

        return None


    def should_warn(self, obj: TrackedObject) -> bool:
        if obj.state != ObjectState.APPROACHING:
            return False

        now = time.time()

        if obj.last_warned is None:
            obj.last_warned = now
            return True

        if now - obj.last_warned >= WARN_COOLDOWN:
            obj.last_warned = now
            return True

        return False


    def can_global_warn(self) -> bool:
        now = time.time()

        if self.global_last_warned is None:
            self.global_last_warned = now
            return True

        if now - self.global_last_warned >= GLOBAL_WARN_COOLDOWN:
            self.global_last_warned = now
            return True

        return False


    def cleanup(self):
        now = time.time()
        expired = [
            k for k, v in self.objects.items()
            if now - v.last_seen >= EXPIRE_TIME
        ]
        for k in expired:
            del self.objects[k]


    def get_all_objects(self) -> List[TrackedObject]:
        return list(self.objects.values())


    def get_active_warnings(self) -> List[str]:
        result = []
        for obj in self.objects.values():
            if obj.state == ObjectState.APPROACHING:
                label = TTS_CLASS_MAP.get(obj.cls, obj.cls)
                result.append(label)
        return result


    def should_env_warn(self, zone_name: str) -> bool:
        if not self.env_alert_enabled:
            return False

        if zone_name in self.env_muted:
            return False

        now = time.time()
        last = self.env_last_warned.get(zone_name)

        if last is None or (now - last) >= ENV_WARN_COOLDOWN:
            self.env_last_warned[zone_name] = now
            return True

        return False


    def mute_env_zone(self, zone_name: str):
        self.env_muted.add(zone_name)


    def unmute_env_zone(self, zone_name: str):
        self.env_muted.discard(zone_name)


    def disable_env_alerts(self):
        self.env_alert_enabled = False


    def enable_env_alerts(self):
        self.env_alert_enabled = True


    def reset_all(self):
        self.objects.clear()
        self.env_last_warned.clear()
        self.env_muted.clear()
        self.last_env.clear()
        self.env_alert_enabled = True
        self.global_last_warned = None


warning_manager = WarningManager()
