# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock
import stevedore

from sushy import exceptions
from sushy.resources import base as res_base
from sushy.resources.oem import base as oem_base
from sushy.resources.oem import common as oem_common
from sushy.tests.unit import base


class ContosoResourceOEMExtension(oem_base.OEMExtensionResourceBase):

    def __init__(self, resource, *args, **kwargs):
        super(ContosoResourceOEMExtension, self).__init__(
            resource, 'Contoso', *args, **kwargs)


class FauxResourceOEMExtension(oem_base.OEMExtensionResourceBase):

    def __init__(self, resource, *args, **kwargs):
        super(FauxResourceOEMExtension, self).__init__(
            resource, 'Faux', *args, **kwargs)


class ResourceOEMCommonMethodsTestCase(base.TestCase):

    def setUp(self):
        super(ResourceOEMCommonMethodsTestCase, self).setUp()
        # We use ExtensionManager.make_test_instance() and instantiate the
        # test instance outside of the test cases in setUp. Inside of the
        # test cases we set this as the return value of the mocked
        # constructor. Also note that this instrumentation has been done
        # only for one specific resource namespace which gets passed in the
        # constructor of ExtensionManager. Moreover, this setUp also enables
        # us to verify that the constructor is called correctly while still
        # using a more realistic ExtensionManager.
        contoso_ep = mock.Mock()
        contoso_ep.module_name = __name__
        contoso_ep.attrs = ['ContosoResourceOEMExtension']
        self.contoso_extn = stevedore.extension.Extension(
            'contoso', contoso_ep, ContosoResourceOEMExtension, None)
        self.contoso_extn_dup = stevedore.extension.Extension(
            'contoso_dup', contoso_ep, ContosoResourceOEMExtension, None)

        faux_ep = mock.Mock()
        faux_ep.module_name = __name__
        faux_ep.attrs = ['FauxResourceOEMExtension']
        self.faux_extn = stevedore.extension.Extension(
            'faux', faux_ep, FauxResourceOEMExtension, None)
        self.faux_extn_dup = stevedore.extension.Extension(
            'faux_dup', faux_ep, FauxResourceOEMExtension, None)

        self.fake_ext_mgr = (
            stevedore.extension.ExtensionManager.make_test_instance(
                [self.contoso_extn, self.faux_extn]))
        self.fake_ext_mgr2 = (
            stevedore.extension.ExtensionManager.make_test_instance(
                [self.contoso_extn_dup, self.faux_extn_dup]))

    def tearDown(self):
        super(ResourceOEMCommonMethodsTestCase, self).tearDown()
        if oem_common._global_extn_mgrs_by_resource:
            oem_common._global_extn_mgrs_by_resource = {}

    @mock.patch.object(stevedore, 'ExtensionManager', autospec=True)
    def test__create_extension_manager(self, ExtensionManager_mock):
        system_resource_oem_ns = 'sushy.resources.system.oems'
        ExtensionManager_mock.return_value = self.fake_ext_mgr

        result = oem_common._create_extension_manager(system_resource_oem_ns)

        self.assertEqual(self.fake_ext_mgr, result)
        ExtensionManager_mock.assert_called_once_with(
            system_resource_oem_ns, propagate_map_exceptions=True,
            on_load_failure_callback=oem_common._raise)

    @mock.patch.object(stevedore, 'ExtensionManager', autospec=True)
    def test__create_extension_manager_no_extns(self, ExtensionManager_mock):
        system_resource_oem_ns = 'sushy.resources.system.oems'
        ExtensionManager_mock.return_value.names.return_value = []

        self.assertRaisesRegex(
            exceptions.ExtensionError, 'No extensions found',
            oem_common._create_extension_manager,
            system_resource_oem_ns)

    @mock.patch.object(stevedore, 'ExtensionManager', autospec=True)
    def test__get_extension_manager_of_resource(self, ExtensionManager_mock):
        ExtensionManager_mock.return_value = self.fake_ext_mgr

        result = oem_common._get_extension_manager_of_resource('system')
        self.assertEqual(self.fake_ext_mgr, result)
        ExtensionManager_mock.assert_called_once_with(
            namespace='sushy.resources.system.oems',
            propagate_map_exceptions=True,
            on_load_failure_callback=oem_common._raise)
        ExtensionManager_mock.reset_mock()

        result = oem_common._get_extension_manager_of_resource('manager')
        self.assertEqual(self.fake_ext_mgr, result)
        ExtensionManager_mock.assert_called_once_with(
            namespace='sushy.resources.manager.oems',
            propagate_map_exceptions=True,
            on_load_failure_callback=oem_common._raise)
        for name, extension in result.items():
            self.assertTrue(name in ('contoso', 'faux'))
            self.assertTrue(extension in (self.contoso_extn,
                                          self.faux_extn))

    def test__get_resource_vendor_extension_obj_lazy_plugin_invoke(self):
        resource_instance_mock = mock.Mock()
        extension_mock = mock.MagicMock()
        extension_mock.obj = None

        result = oem_common._get_resource_vendor_extension_obj(
            extension_mock, resource_instance_mock)
        self.assertEqual(extension_mock.plugin.return_value, result)
        extension_mock.plugin.assert_called_once_with(resource_instance_mock)
        extension_mock.reset_mock()

        # extension_mock.obj is not None anymore
        result = oem_common._get_resource_vendor_extension_obj(
            extension_mock, resource_instance_mock)
        self.assertEqual(extension_mock.plugin.return_value, result)
        self.assertFalse(extension_mock.plugin.called)

    @mock.patch.object(stevedore, 'ExtensionManager', autospec=True)
    def test_get_resource_extension_by_vendor(self, ExtensionManager_mock):
        resource_instance_mock = mock.Mock(spec=res_base.ResourceBase)
        ExtensionManager_mock.side_effect = [self.fake_ext_mgr,
                                             self.fake_ext_mgr2]

        result = oem_common.get_resource_extension_by_vendor(
            'system', 'Faux', resource_instance_mock)
        self.assertIsInstance(result, FauxResourceOEMExtension)
        ExtensionManager_mock.assert_called_once_with(
            'sushy.resources.system.oems', propagate_map_exceptions=True,
            on_load_failure_callback=oem_common._raise)
        ExtensionManager_mock.reset_mock()

        result = oem_common.get_resource_extension_by_vendor(
            'system', 'Contoso', resource_instance_mock)
        self.assertIsInstance(result, ContosoResourceOEMExtension)
        self.assertFalse(ExtensionManager_mock.called)
        ExtensionManager_mock.reset_mock()

        result = oem_common.get_resource_extension_by_vendor(
            'manager', 'Faux_dup', resource_instance_mock)
        self.assertIsInstance(result, FauxResourceOEMExtension)
        ExtensionManager_mock.assert_called_once_with(
            'sushy.resources.manager.oems', propagate_map_exceptions=True,
            on_load_failure_callback=oem_common._raise)
        ExtensionManager_mock.reset_mock()

        result = oem_common.get_resource_extension_by_vendor(
            'manager', 'Contoso_dup', resource_instance_mock)
        self.assertIsInstance(result, ContosoResourceOEMExtension)
        self.assertFalse(ExtensionManager_mock.called)
        ExtensionManager_mock.reset_mock()

    @mock.patch.object(stevedore, 'ExtensionManager', autospec=True)
    def test_get_resource_extension_by_vendor_fail(
            self, ExtensionManager_mock):
        resource_instance_mock = mock.Mock(spec=res_base.ResourceBase)
        # ``fake_ext_mgr2`` has extension names as ``faux_dup``
        # and ``contoso_dup``.
        ExtensionManager_mock.return_value = self.fake_ext_mgr2

        self.assertRaisesRegex(
            exceptions.OEMExtensionNotFoundError,
            'No sushy.resources.system.oems OEM extension found '
            'by name "faux"',
            oem_common.get_resource_extension_by_vendor,
            'sushy.resources.system.oems', 'Faux', resource_instance_mock)
