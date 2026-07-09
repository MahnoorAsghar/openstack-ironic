# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from unittest import mock

from ironic.common import states
from ironic.conductor import task_manager
from ironic.drivers.modules.inspector import interface as inspector_iface
from ironic.tests.unit.db import base as db_base
from ironic.tests.unit.objects import utils as obj_utils


class TearDownManagedBootTestCase(db_base.DbTestCase):
    def setUp(self):
        super().setUp()
        self.node = obj_utils.create_test_node(
            self.context,
            driver_internal_info={'inspector_manage_boot': True})
        self.config(power_off=True, group='inspector')

    @staticmethod
    def _mock_driver(task, capabilities=None):
        task.driver = mock.Mock(
            spec=['boot', 'network', 'power'],
            boot=mock.Mock(capabilities=capabilities or []),
            network=mock.Mock(),
            power=mock.Mock())

    @mock.patch('ironic.common.utils.fast_track_enabled', autospec=True)
    @mock.patch('ironic.conductor.utils.is_fast_track', autospec=True)
    @mock.patch('ironic.conductor.utils.node_power_action', autospec=True)
    def test_pxe_skips_soft_power_off(
            self, node_power_action_mock, is_fast_track_mock,
            fast_track_enabled_mock):
        is_fast_track_mock.return_value = False
        fast_track_enabled_mock.return_value = False
        with task_manager.acquire(
                self.context, self.node.uuid, shared=False) as task:
            self._mock_driver(
                task, capabilities=['ramdisk_boot', 'pxe_boot',
                                    'can_clean_up_ramdisk_while_on'])
            errors = inspector_iface.tear_down_managed_boot(task)

            self.assertEqual([], errors)
            task.driver.boot.clean_up_ramdisk.assert_called_once_with(task)
            task.driver.network.remove_inspection_network.assert_called_once_with(  # noqa
                task)
            node_power_action_mock.assert_called_once_with(
                task, states.POWER_OFF)

    @mock.patch('ironic.common.utils.fast_track_enabled', autospec=True)
    @mock.patch('ironic.conductor.utils.is_fast_track', autospec=True)
    @mock.patch('ironic.conductor.utils.node_power_action', autospec=True)
    def test_pxe_cleans_ramdisk_on_disable_power_off(
            self, node_power_action_mock, is_fast_track_mock,
            fast_track_enabled_mock):
        is_fast_track_mock.return_value = False
        fast_track_enabled_mock.return_value = False
        with task_manager.acquire(
                self.context, self.node.uuid, shared=False) as task:
            task.node.disable_power_off = True
            self._mock_driver(
                task, capabilities=['ramdisk_boot', 'pxe_boot',
                                    'can_clean_up_ramdisk_while_on'])
            errors = inspector_iface.tear_down_managed_boot(task)

            self.assertEqual([], errors)
            task.driver.boot.clean_up_ramdisk.assert_called_once_with(task)
            task.driver.network.remove_inspection_network.assert_called_once_with(  # noqa
                task)
            node_power_action_mock.assert_called_once_with(task, states.REBOOT)

    @mock.patch('ironic.common.utils.fast_track_enabled', autospec=True)
    @mock.patch('ironic.conductor.utils.is_fast_track', autospec=True)
    @mock.patch('ironic.conductor.utils.node_power_action', autospec=True)
    def test_pxe_cleans_ramdisk_on_fast_track(
            self, node_power_action_mock, is_fast_track_mock,
            fast_track_enabled_mock):
        is_fast_track_mock.return_value = True
        fast_track_enabled_mock.return_value = True
        with task_manager.acquire(
                self.context, self.node.uuid, shared=False) as task:
            self._mock_driver(
                task, capabilities=['ramdisk_boot', 'pxe_boot',
                                    'can_clean_up_ramdisk_while_on'])
            errors = inspector_iface.tear_down_managed_boot(task)

            self.assertEqual([], errors)
            task.driver.boot.clean_up_ramdisk.assert_called_once_with(task)
            task.driver.network.remove_inspection_network.assert_called_once_with(  # noqa
                task)
            node_power_action_mock.assert_not_called()

    @mock.patch('ironic.common.utils.fast_track_enabled', autospec=True)
    @mock.patch('ironic.conductor.utils.is_fast_track', autospec=True)
    @mock.patch('ironic.conductor.utils.node_power_action', autospec=True)
    def test_https_cleans_ramdisk_on_disable_power_off(
            self, node_power_action_mock, is_fast_track_mock,
            fast_track_enabled_mock):
        # Redfish HTTPS / UEFI HTTP is neither PXE nor vmedia, but cleanup
        # is conductor-side only and safe while powered on.
        is_fast_track_mock.return_value = False
        fast_track_enabled_mock.return_value = False
        with task_manager.acquire(
                self.context, self.node.uuid, shared=False) as task:
            task.node.disable_power_off = True
            self._mock_driver(
                task,
                capabilities=['ramdisk_boot',
                              'can_clean_up_ramdisk_while_on'])
            errors = inspector_iface.tear_down_managed_boot(task)

            self.assertEqual([], errors)
            task.driver.boot.clean_up_ramdisk.assert_called_once_with(task)
            task.driver.network.remove_inspection_network.assert_called_once_with(  # noqa
                task)
            node_power_action_mock.assert_called_once_with(task, states.REBOOT)

    @mock.patch('ironic.common.utils.fast_track_enabled', autospec=True)
    @mock.patch('ironic.conductor.utils.is_fast_track', autospec=True)
    @mock.patch('ironic.conductor.utils.node_power_action', autospec=True)
    def test_vmedia_soft_power_off_before_eject(
            self, node_power_action_mock, is_fast_track_mock,
            fast_track_enabled_mock):
        is_fast_track_mock.return_value = False
        fast_track_enabled_mock.return_value = False
        with task_manager.acquire(
                self.context, self.node.uuid, shared=False) as task:
            self._mock_driver(task)
            errors = inspector_iface.tear_down_managed_boot(task)

            self.assertEqual([], errors)
            self.assertEqual(
                mock.call(task, states.SOFT_POWER_OFF),
                node_power_action_mock.call_args_list[0])
            task.driver.boot.clean_up_ramdisk.assert_called_once_with(task)
            task.driver.network.remove_inspection_network.assert_called_once_with(  # noqa
                task)
            self.assertEqual(
                mock.call(task, states.POWER_OFF),
                node_power_action_mock.call_args_list[1])

    @mock.patch('ironic.common.utils.fast_track_enabled', autospec=True)
    @mock.patch('ironic.conductor.utils.is_fast_track', autospec=True)
    @mock.patch('ironic.conductor.utils.node_power_action', autospec=True)
    def test_vmedia_skips_cleanup_on_fast_track(
            self, node_power_action_mock, is_fast_track_mock,
            fast_track_enabled_mock):
        is_fast_track_mock.return_value = True
        fast_track_enabled_mock.return_value = True
        with task_manager.acquire(
                self.context, self.node.uuid, shared=False) as task:
            self._mock_driver(task)
            errors = inspector_iface.tear_down_managed_boot(task)

            self.assertEqual([], errors)
            task.driver.boot.clean_up_ramdisk.assert_not_called()
            task.driver.network.remove_inspection_network.assert_called_once_with(  # noqa
                task)
            node_power_action_mock.assert_not_called()

    @mock.patch('ironic.common.utils.fast_track_enabled', autospec=True)
    @mock.patch('ironic.conductor.utils.is_fast_track', autospec=True)
    @mock.patch('ironic.conductor.utils.node_power_action', autospec=True)
    def test_vmedia_skips_cleanup_on_disable_power_off(
            self, node_power_action_mock, is_fast_track_mock,
            fast_track_enabled_mock):
        is_fast_track_mock.return_value = False
        fast_track_enabled_mock.return_value = False
        with task_manager.acquire(
                self.context, self.node.uuid, shared=False) as task:
            task.node.disable_power_off = True
            self._mock_driver(task)
            errors = inspector_iface.tear_down_managed_boot(task)

            self.assertEqual([], errors)
            task.driver.boot.clean_up_ramdisk.assert_not_called()
            task.driver.network.remove_inspection_network.assert_called_once_with(  # noqa
                task)
            node_power_action_mock.assert_called_once_with(task, states.REBOOT)
