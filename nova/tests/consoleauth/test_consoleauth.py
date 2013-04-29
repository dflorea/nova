# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack Foundation
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""
Tests for Consoleauth Code.

"""

from nova.consoleauth import manager
from nova import context
from nova.openstack.common import log as logging
from nova.openstack.common import timeutils
from nova import test

LOG = logging.getLogger(__name__)


class ConsoleauthTestCase(test.TestCase):
    """Test Case for consoleauth."""

    def setUp(self):
        super(ConsoleauthTestCase, self).setUp()
        self.manager = manager.ConsoleAuthManager()
        self.context = context.get_admin_context()

    def test_tokens_expire(self):
        # Test that tokens expire correctly.
        self.useFixture(test.TimeOverride())
        token = 'mytok'
        self.flags(console_token_ttl=1)

        self._stub_validate_console_port(True)

        self.manager.authorize_console(self.context, token, 'novnc',
                                         '127.0.0.1', '8080', 'host',
                                         'instance')
        self.assertTrue(self.manager.check_token(self.context, token))
        timeutils.advance_time_seconds(1)
        self.assertFalse(self.manager.check_token(self.context, token))

    def _stub_validate_console_port(self, result):
        def fake_validate_console_port(ctxt, instance, port, console_type):
            return result

        self.stubs.Set(self.manager.compute_rpcapi,
                       'validate_console_port',
                       fake_validate_console_port)

    def test_multiple_tokens_for_instance(self):
        tokens = ["token" + str(i) for i in xrange(10)]
        instance = "12345"

        self._stub_validate_console_port(True)

        for token in tokens:
            self.manager.authorize_console(self.context, token, 'novnc',
                                          '127.0.0.1', '8080', 'host',
                                          instance)

        for token in tokens:
            self.assertTrue(self.manager.check_token(self.context, token))

    def test_delete_tokens_for_instance(self):
        instance = "12345"
        tokens = ["token" + str(i) for i in xrange(10)]
        for token in tokens:
            self.manager.authorize_console(self.context, token, 'novnc',
                                          '127.0.0.1', '8080', 'host',
                                          instance)
        self.manager.delete_tokens_for_instance(self.context, instance)
        stored_tokens = self.manager._get_tokens_for_instance(instance)

        self.assertEqual(len(stored_tokens), 0)

        for token in tokens:
            self.assertFalse(self.manager.check_token(self.context, token))

    def test_wrong_token_has_port(self):
        token = 'mytok'

        self._stub_validate_console_port(False)

        self.manager.authorize_console(self.context, token, 'novnc',
                                        '127.0.0.1', '8080', 'host',
                                        instance_uuid='instance')
        self.assertFalse(self.manager.check_token(self.context, token))

    def test_console_no_instance_uuid(self):
        self.manager.authorize_console(self.context, "token", 'novnc',
                                        '127.0.0.1', '8080', 'host',
                                        instance_uuid=None)
        self.assertFalse(self.manager.check_token(self.context, "token"))

    def test_get_backdoor_port(self):
        self.manager.backdoor_port = 59697
        port = self.manager.get_backdoor_port(self.context)
        self.assertEqual(port, self.manager.backdoor_port)


class CellsConsoleauthTestCase(ConsoleauthTestCase):
    """Test Case for consoleauth w/ cells enabled."""

    def setUp(self):
        super(CellsConsoleauthTestCase, self).setUp()
        self.flags(enable=True, group='cells')

    def _stub_validate_console_port(self, result):
        def fake_validate_console_port(ctxt, instance_uuid, console_port,
                                       console_type):
            return result

        self.stubs.Set(self.manager.cells_rpcapi,
                       'validate_console_port',
                       fake_validate_console_port)
