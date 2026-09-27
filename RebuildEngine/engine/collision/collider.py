"""Basic AABB collision."""

from typing import List, Optional, Tuple
from engine.core.object import Instance


def aabb_overlap(a: Instance, b: Instance) -> bool:
    ax1, ay1, ax2, ay2 = a.get_bbox()
    bx1, by1, bx2, by2 = b.get_bbox()
    return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1


def check_collision(inst: Instance, others: List[Instance], object_name: Optional[str] = None) -> Optional[Instance]:
    for other in others:
        if other is inst or not other.active:
            continue
        if object_name and other.object_name != object_name:
            continue
        if aabb_overlap(inst, other):
            return other
    return None


def check_collision_all(inst: Instance, others: List[Instance], object_name: Optional[str] = None) -> List[Instance]:
    result = []
    for other in others:
        if other is inst or not other.active:
            continue
        if object_name and other.object_name != object_name:
            continue
        if aabb_overlap(inst, other):
            result.append(other)
    return result
