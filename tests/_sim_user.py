from __future__ import annotations

import sys
import os

# TO RUN REQUIRES THE habitat-sim CONDA ENVIRONMENT ACTIVATED

os.environ["PKG_PROXY_API"]="package_proxy._local.api.LocalApi"
os.environ["PKG_PROXY_TARGET"]="habitat_sim"
os.environ["PKG_PROXY_API_LOGLEVEL"]="DEBUG"

import package_proxy

import attr
import habitat_sim.utils as hab_utils
import magnum as mn
from habitat_sim.agent.controls.controls import ActuationSpec, SceneNodeControl
from habitat_sim.agent.controls.default_controls import _move_along, _rotate_local
from habitat_sim.registry import registry
from habitat_sim.scene import SceneNode


_X_AXIS = 0
_Y_AXIS = 1
_Z_AXIS = 2


@attr.s(auto_attribs=True)  # TODO check significance of this decorator
class ActuationVecSpec(ActuationSpec):
    """Inherits from Meta's habitat-sim class.

    Expects a list of lists.

    Enables passing in two lists to set_pose --> the first is the xyz absolute positions
    for the agent, and the second list contains the coefficients of a quaternion
    specifying absolute rotation
    """

    amount: list[list[float]]
    constraint: float | None = None


def _move_along_diagonal(
    scene_node: SceneNode, distance: float, direction: list
) -> None:
    ax = mn.Vector3(direction)
    scene_node.translate_local(ax * distance)


@registry.register_move_fn(body_action=True)
class SetYaw(SceneNodeControl):
    """Custom habitat-sim action used to set the agent body absolute yaw rotation.

    :class:`ActuationSpec` amount contains the new absolute yaw rotation in degrees.
    """

    def __call__(self, scene_node: SceneNode, actuation_spec: ActuationSpec) -> None:
        angle = mn.Deg(actuation_spec.amount)

        # Since z+ is out of the page, x+ is "right", and y+ is "up", then changes
        # in yaw should presumably be about the y-axis, otherwise we might change
        # the roll. TODO investigate this further and update the original
        # implementation if necessary.
        new_rotation = mn.Quaternion.rotation(angle, mn.Vector3.z_axis())
        scene_node.rotation = new_rotation.normalized()


