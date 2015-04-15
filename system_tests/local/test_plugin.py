########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

# Built-in Imports
import os

# Cloudify Imports
from ec2 import (
    utils,
    securitygroup,
    keypair,
    elasticip,
    instance
)
from cloudify.state import current_ctx
from cloudify.exceptions import NonRecoverableError
from ec2_test_utils import (
    EC2LocalTestUtils,
    EXTERNAL_RESOURCE_ID,
    SIMPLE_IP, SIMPLE_SG, SIMPLE_KP, SIMPLE_VM,
    PAIR_A_IP, PAIR_A_VM,
    PAIR_B_SG, PAIR_B_VM
)


class TestWorkflowClean(EC2LocalTestUtils):

    def tearDown(self):
        super(TestWorkflowClean, self).tearDown()
        self.localenv.execute('uninstall', task_retries=10)

    def test_simple_resources(self):
        client = self._get_ec2_client()

        test_name = 'test_simple_resources'

        inputs = self._get_inputs(test_name=test_name)
        self._set_up(inputs=inputs)

        # execute install workflow
        self.localenv.execute('install', task_retries=10)

        instance_storage = self._get_instances(self.localenv.storage)

        self.assertEquals(4, len(instance_storage))

        for node_instance in self._get_instances(self.localenv.storage):
            self.assertIn(EXTERNAL_RESOURCE_ID,
                          node_instance.runtime_properties)

        elastic_ip_node = \
            self._get_instance_node(
                SIMPLE_IP, self.localenv.storage)
        elastic_ip_address = \
            elastic_ip_node.runtime_properties[EXTERNAL_RESOURCE_ID]
        elastic_ip_object_list = \
            client.get_all_addresses(addresses=elastic_ip_address)
        self.assertEqual(1, len(elastic_ip_object_list))

        security_group_node = \
            self._get_instance_node(SIMPLE_SG, self.localenv.storage)
        security_group_id = \
            security_group_node.runtime_properties[EXTERNAL_RESOURCE_ID]
        security_group_object_list = \
            client.get_all_security_groups(group_ids=security_group_id)
        self.assertEqual(1, len(security_group_object_list))

        key_pair_node = \
            self._get_instance_node(SIMPLE_KP, self.localenv.storage)
        key_pair_name = \
            key_pair_node.runtime_properties[EXTERNAL_RESOURCE_ID]
        key_pair_object_list = \
            client.get_all_key_pairs(keynames=key_pair_name)
        self.assertEqual(1, len(key_pair_object_list))

        instance_node = \
            self._get_instance_node(SIMPLE_VM, self.localenv.storage)
        instance_id = \
            instance_node.runtime_properties[EXTERNAL_RESOURCE_ID]
        reservation_list = \
            client.get_all_reservations(instance_ids=instance_id)
        instance_list = reservation_list[0].instances
        self.assertEqual(1, len(instance_list))

    def test_simple_relationships(self):

        client = self._get_ec2_client()

        test_name = 'test_simple_relationships'

        inputs = self._get_inputs(test_name=test_name)

        self._set_up(
            inputs=inputs,
            filename='relationships-blueprint.yaml')

        # execute install workflow
        self.localenv.execute('install', task_retries=10)

        instance_storage = self._get_instances(self.localenv.storage)
        self.assertEquals(4, len(instance_storage))

        instance_node = \
            self._get_instance_node(PAIR_A_VM, self.localenv.storage)
        instance_id = \
            instance_node.runtime_properties[EXTERNAL_RESOURCE_ID]
        reservation_list = \
            client.get_all_reservations(instance_ids=instance_id)
        instance_list_ip = reservation_list[0].instances

        self.assertEquals(4, len(instance_storage))
        elastic_ip_node = \
            self._get_instance_node(
                PAIR_A_IP, self.localenv.storage)
        elastic_ip_address = \
            elastic_ip_node.runtime_properties[EXTERNAL_RESOURCE_ID]
        elastic_ip_object_list = \
            client.get_all_addresses(addresses=elastic_ip_address)

        self.assertEqual(
            str(elastic_ip_object_list[0].instance_id),
            str(instance_list_ip[0].id))

        instance_node = \
            self._get_instance_node(PAIR_B_VM, self.localenv.storage)
        instance_id = \
            instance_node.runtime_properties[EXTERNAL_RESOURCE_ID]
        reservation_list = \
            client.get_all_reservations(instance_ids=instance_id)
        instance_list = reservation_list[0].instances

        security_group_node = \
            self._get_instance_node(PAIR_B_SG, self.localenv.storage)
        security_group_id = \
            security_group_node.runtime_properties[EXTERNAL_RESOURCE_ID]
        security_group_object_list = \
            client.get_all_security_groups(group_ids=security_group_id)

        self.assertIn(
            str(security_group_object_list[0].instances()[0].id),
            str(instance_list[0].id))


class EC2UtilsUnitTests(EC2LocalTestUtils):

    def test_utils_get_resource_id(self):

        ctx = self.mock_cloudify_context(
            'test_utils_get_resource_id')
        current_ctx.set(ctx=ctx)

        ctx.node.properties['resource_id'] = \
            'test_utils_get_resource_id'

        resource_id = utils.get_resource_id()

        self.assertEquals(
            'test_utils_get_resource_id', resource_id)

    def test_utils_get_resource_id_dynamic(self):

        ctx = self.mock_cloudify_context(
            'test_utils_get_resource_id')
        current_ctx.set(ctx=ctx)

        ctx.node.properties['resource_id'] = ''

        resource_id = utils.get_resource_id()

        self.assertEquals('None-test_utils_get_resource_id', resource_id)

    def test_utils_get_resource_id_from_key_path(self):

        ctx = self.mock_cloudify_context(
            'test_utils_get_resource_id_from_key_path')
        current_ctx.set(ctx=ctx)

        ctx.node.properties['private_key_path'] = \
            '~/.ssh/test_utils_get_resource_id_from_key_path.pem'

        resource_id = utils.get_resource_id()

        self.assertEquals(
            'test_utils_get_resource_id_from_key_path', resource_id)

    def test_utils_validate_node_properties_missing_key(self):
        ctx = self.mock_cloudify_context(
            'test_utils_validate_node_properties_missing_key')
        current_ctx.set(ctx=ctx)

        ex = self.assertRaises(
            NonRecoverableError, utils.validate_node_property,
            'missing_key',
            ctx.node.properties)

        self.assertIn(
            'missing_key is a required input. Unable to create.',
            ex.message)

    def test_utils_log_available_resources(self):

        ctx = self.mock_cloudify_context(
            'test_utils_log_available_resources')
        current_ctx.set(ctx=ctx)

        client = self._get_ec2_client()

        key_pairs = client.get_all_key_pairs()

        utils.log_available_resources(key_pairs)

    def test_utils_get_external_resource_id_or_raise_no_id(self):

        ctx = self.mock_cloudify_context(
            'test_utils_get_external_resource_id_or_raise_no_id')
        current_ctx.set(ctx=ctx)

        ctx.instance.runtime_properties['prop'] = None

        ex = self.assertRaises(
            NonRecoverableError,
            utils.get_external_resource_id_or_raise,
            'test_operation', ctx.instance)

        self.assertIn(
            'Cannot test_operation because {0} is not assigned'
            .format(EXTERNAL_RESOURCE_ID),
            ex.message)

    def test_utils_get_external_resource_id_or_raise(self):

        ctx = self.mock_cloudify_context(
            'test_utils_get_external_resource_id_or_raise')
        current_ctx.set(ctx=ctx)

        ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID] = \
            'test_utils_get_external_resource_id_or_raise'

        output = utils.get_external_resource_id_or_raise(
            'test_operation', ctx.instance)

        self.assertEquals(
            'test_utils_get_external_resource_id_or_raise', output)

    def test_utils_set_external_resource_id_cloudify(self):

        ctx = self.mock_cloudify_context(
            'test_utils_set_external_resource_id_cloudify')
        current_ctx.set(ctx=ctx)

        utils.set_external_resource_id(
            'id-value',
            ctx.instance,
            external=False)

        self.assertEquals(
            'id-value',
            ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID])

    def test_utils_set_external_resource_id_external(self):

        ctx = self.mock_cloudify_context(
            'test_utils_set_external_resource_id_external')
        current_ctx.set(ctx=ctx)

        utils.set_external_resource_id(
            'id-value',
            ctx.instance)

        self.assertEquals(
            'id-value',
            ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID])

    def test_utils_unassign_runtime_property_from_resource(self):

        ctx = self.mock_cloudify_context(
            'test_utils_unassign_runtime_property_from_resource')
        current_ctx.set(ctx=ctx)

        ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID] = \
            'test_utils_unassign_runtime_property_from_resource'

        utils.unassign_runtime_property_from_resource(
            EXTERNAL_RESOURCE_ID,
            ctx.instance)

        self.assertNotIn(
            EXTERNAL_RESOURCE_ID,
            ctx.instance.runtime_properties)

    def test_utils_use_external_resource_not_external(self):

        ctx = self.mock_cloudify_context(
            'test_utils_use_external_resource_not_external')
        current_ctx.set(ctx=ctx)

        self.assertEquals(
            False,
            utils.use_external_resource(ctx.node.properties))

    def test_utils_use_external_resource_external(self):

        ctx = self.mock_cloudify_context(
            'test_utils_use_external_resource_external')
        current_ctx.set(ctx=ctx)

        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = \
            'test_utils_use_external_resource_external'

        self.assertEquals(
            True,
            utils.use_external_resource(ctx.node.properties))

    def test_get_target_external_resource_ids(self):

        ctx = self.mock_cloudify_context(
            'get_target_external_resource_ids')
        current_ctx.set(ctx=ctx)

        output = utils.get_target_external_resource_ids(
            'instance_connected_to_keypair',
            ctx.instance)

        self.assertEquals(0, len(output))

    def test_get_target_external_resource_ids_no_attr(self):

        ctx = self.mock_cloudify_context(
            'get_target_external_resource_ids')
        current_ctx.set(ctx=ctx)

        delattr(ctx.instance, 'relationships')

        output = utils.get_target_external_resource_ids(
            'instance_connected_to_keypair',
            ctx.instance)

        self.assertEquals(0, len(output))


class EC2SecurityGroupUnitTests(EC2LocalTestUtils):

    def test_get_all_security_groups(self):

        ctx = self.mock_cloudify_context(
            'test_get_all_security_groups')
        current_ctx.set(ctx=ctx)

        client = self._get_ec2_client()
        groups_from_test = client.get_all_security_groups()

        groups_from_plugin = securitygroup._get_all_security_groups()

        self.assertEqual(len(groups_from_test), len(groups_from_plugin))

    def test_get_all_security_groups_not_found(self):

        ctx = self.mock_cloudify_context(
            'test_get_all_security_groups_not_found')
        current_ctx.set(ctx=ctx)

        not_found_names = ['test_get_all_security_groups_not_found']

        groups_from_plugin = securitygroup._get_all_security_groups(
            list_of_group_names=not_found_names)

        self.assertIsNone(groups_from_plugin)

    def test_get_security_group_from_name(self):

        ctx = self.mock_cloudify_context(
            'test_get_security_group_from_name')
        current_ctx.set(ctx=ctx)

        client = self._get_ec2_client()
        group = client.create_security_group(
            'test_get_security_group_from_name',
            'some description')
        group_from_plugin = securitygroup._get_security_group_from_id(
            group_id=group.id)
        self.assertEqual(group.name, group_from_plugin.name)
        group.delete()

    def test_get_security_group_from_id(self):

        ctx = self.mock_cloudify_context(
            'test_get_security_group_from_id')
        current_ctx.set(ctx=ctx)

        client = self._get_ec2_client()
        group = client.create_security_group(
            'test_get_security_group_from_id',
            'some description')
        group_from_plugin = securitygroup._get_security_group_from_name(
            group_name=group.name)
        self.assertEqual(group.id, group_from_plugin.id)
        group.delete()

    def test_get_security_group_from_name_but_really_id(self):

        ctx = self.mock_cloudify_context(
            'test_get_security_group_from_name_but_really_id')
        current_ctx.set(ctx=ctx)

        client = self._get_ec2_client()
        group = client.create_security_group(
            'test_get_security_group_from_name_but_really_id',
            'some description')
        group_from_plugin = securitygroup._get_security_group_from_name(
            group_name=group.id)
        self.assertEqual(group.name, group_from_plugin.name)
        group.delete()

    def test_get_security_group_from_id_but_really_name(self):

        ctx = self.mock_cloudify_context(
            'test_get_security_group_from_id_but_really_name')
        current_ctx.set(ctx=ctx)

        client = self._get_ec2_client()
        group = client.create_security_group(
            'test_get_security_group_from_id_but_really_name',
            'some description')
        group_from_plugin = securitygroup._get_security_group_from_id(
            group_id=group.name)
        self.assertEqual(group.id, group_from_plugin.id)
        group.delete()

    def test_delete_external_securitygroup_external(self):

        ctx = self.mock_cloudify_context(
            'test_delete_external_securitygroup_external')
        current_ctx.set(ctx=ctx)

        ctx.node.properties['use_external_resource'] = True
        ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID] = \
            'sg-blahblah'

        output = securitygroup._delete_external_securitygroup()
        self.assertEqual(True, output)
        self.assertNotIn(
            EXTERNAL_RESOURCE_ID, ctx.instance.runtime_properties)

    def test_delete_external_securitygroup_not_external(self):

        ctx = self.mock_cloudify_context(
            'test_delete_external_securitygroup_not_external')
        current_ctx.set(ctx=ctx)

        ctx.node.properties['use_external_resource'] = False

        output = securitygroup._delete_external_securitygroup()
        self.assertEqual(False, output)

    def test_create_external_securitygroup_external(self):

        ctx = self.mock_cloudify_context(
            'test_create_external_securitygroup_external')
        current_ctx.set(ctx=ctx)

        client = self._get_ec2_client()
        group = client.create_security_group(
            'test_create_external_securitygroup_external',
            'some description')

        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = group.id

        output = securitygroup._create_external_securitygroup(group.name)
        self.assertEqual(True, output)
        self.assertEqual(
            ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID],
            group.id)
        group.delete()

    def test_create_external_securitygroup_external_bad_id(self):

        ctx = self.mock_cloudify_context(
            'test_create_external_securitygroup_external_bad_id')
        current_ctx.set(ctx=ctx)

        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = 'sg-73cd3f1e'

        ex = self.assertRaises(
            NonRecoverableError,
            securitygroup._create_external_securitygroup,
            'sg-73cd3f1e')
        self.assertIn('security group does not exist', ex.message)

    def test_create_external_securitygroup_not_external(self):

        ctx = self.mock_cloudify_context(
            'test_create_external_securitygroup_not_external')
        current_ctx.set(ctx=ctx)

        ctx.node.properties['use_external_resource'] = False

        output = securitygroup._delete_external_securitygroup()
        self.assertEqual(False, output)

    def test_create_group_rules_ruleset(self):

        ctx = self.mock_cloudify_context(
            'test_create_group_rules_ruleset')
        ctx.node.properties['rules'] = [
            {
                'ip_protocol': 'tcp',
                'from_port': 22,
                'to_port': 22,
                'cidr_ip': '0.0.0.0/0'
            }
        ]

        current_ctx.set(ctx=ctx)

        client = self._get_ec2_client()
        group = client.create_security_group(
            'test_create_group_rules',
            'some description')
        securitygroup._create_group_rules(group)
        groups_from_test = \
            client.get_all_security_groups(groupnames=[group.name])
        self.assertEqual(group.id, groups_from_test[0].id)
        self.assertEqual(
            str(groups_from_test[0].rules[0]),
            'IPPermissions:tcp(22-22)'
        )
        group.delete()

    def test_delete_security_group_bad_group(self):
        ctx = self.mock_cloudify_context(
            'test_delete_security_group_bad_group')
        current_ctx.set(ctx=ctx)

        ex = self.assertRaises(
            NonRecoverableError,
            securitygroup._delete_security_group, 'sg-73cd3f1e')

        self.assertIn(
            'because the group does not exist in the account', ex.message)


class EC2KeyPairUnitTests(EC2LocalTestUtils):

    def test_search_for_key_file_no_file(self):

        output = keypair._search_for_key_file(
            '~/.ssh/test_search_for_key_file.pem')

        self.assertEquals(
            False,
            output
        )

    def test_get_path_to_key_folder_no_private_key_path(self):

        ctx = self.mock_cloudify_context(
            'test_get_path_to_key_folder_no_private_key_path')
        current_ctx.set(ctx=ctx)
        ex = self.assertRaises(
            NonRecoverableError,
            keypair._get_path_to_key_file)

        self.assertIn(
            'private_key_path not set',
            ex.message
        )

    def test_get_path_to_key_folder(self):

        ctx = self.mock_cloudify_context(
            'test_get_path_to_key_folder')
        current_ctx.set(ctx=ctx)
        ctx.node.properties['private_key_path'] = \
            '~/.ssh/test_get_path_to_key_folder.pem'

        full_key_path = os.path.expanduser(
            ctx.node.properties['private_key_path']
        )

        key_directory, key_filename = os.path.split(full_key_path)

        output = keypair._get_path_to_key_folder()

        self.assertEqual(key_directory, output)

    def test_get_path_to_key_file_no_private_key_path(self):

        ctx = self.mock_cloudify_context(
            'test_get_path_to_key_folder_no_private_key_path')
        current_ctx.set(ctx=ctx)
        ex = self.assertRaises(
            NonRecoverableError,
            keypair._get_path_to_key_file)

        self.assertIn(
            'private_key_path not set',
            ex.message
        )

    def test_get_path_to_key_file(self):

        ctx = self.mock_cloudify_context(
            'test_get_path_to_key_folder')
        current_ctx.set(ctx=ctx)
        ctx.node.properties['private_key_path'] = \
            '~/.ssh/test_get_path_to_key_folder.pem'

        full_key_path = os.path.expanduser(
            ctx.node.properties['private_key_path']
        )

        output = keypair._get_path_to_key_file()

        self.assertEqual(full_key_path, output)

    def test_get_key_pair_by_id_no_kp(self):

        ctx = self.mock_cloudify_context(
            'test_get_key_pair_by_id_no_kp')
        current_ctx.set(ctx=ctx)

        ex = self.assertRaises(
            NonRecoverableError,
            keypair._get_key_pair_by_id,
            'test_get_key_pair_by_id_no_kp')

        self.assertIn(
            'InvalidKeyPair.NotFound',
            ex.message)

    def test_get_key_pair_by_id(self):

        ctx = self.mock_cloudify_context(
            'test_get_key_pair_by_id')
        current_ctx.set(ctx=ctx)

        client = self._get_ec2_client()
        kp = client.create_key_pair(
            'test_get_key_pair_by_id')

        output = keypair._get_key_pair_by_id(kp.name)
        self.assertEqual(kp.name, output.name)
        kp.delete()


class EC2ElasticIPUnitTests(EC2LocalTestUtils):

    def test_get_all_addresses_bad_address(self):

        ctx = self.mock_relationship_context(
            'test_get_address_by_id')
        current_ctx.set(ctx=ctx)

        output = elasticip._get_all_addresses('127.0.0.1')

        self.assertIsNone(output)

    def test_get_address_object_by_id(self):

        ctx = self.mock_relationship_context(
            'test_get_address_by_id')
        current_ctx.set(ctx=ctx)

        client = self._get_ec2_client()
        address = client.allocate_address()
        address_object = \
            elasticip._get_address_object_by_id(address.public_ip)
        self.assertEqual(
            address.public_ip, address_object.public_ip)
        address_object.delete()

    def test_get_address_by_id(self):

        ctx = self.mock_relationship_context(
            'test_get_address_by_id')
        current_ctx.set(ctx=ctx)

        client = self._get_ec2_client()
        address_object = client.allocate_address()
        address = elasticip._get_address_by_id(address_object.public_ip)
        self.assertEqual(address, address_object.public_ip)
        address_object.delete()

    def test_disassociate_external_elasticip_or_instance(self):

        ctx = self.mock_relationship_context(
            'test_disassociate_external_elasticip_or_instance')
        current_ctx.set(ctx=ctx)
        ctx.source.node.properties['use_external_resource'] = False

        output = \
            elasticip._disassociate_external_elasticip_or_instance()

        self.assertEqual(False, output)

    def test_disassociate_external_elasticip_or_instance_external(self):

        ctx = self.mock_relationship_context(
            'test_disassociate_external_elasticip_or_instance_external')
        current_ctx.set(ctx=ctx)
        ctx.source.node.properties['use_external_resource'] = True
        ctx.target.node.properties['use_external_resource'] = True
        ctx.source.instance.runtime_properties['public_ip_address'] = \
            '127.0.0.1'

        output = \
            elasticip._disassociate_external_elasticip_or_instance()

        self.assertEqual(True, output)
        self.assertNotIn(
            'public_ip_address',
            ctx.source.instance.runtime_properties)

    def test_associate_external_elasticip_or_instance(self):

        ctx = self.mock_relationship_context(
            'test_associate_external_elasticip_or_instance')
        current_ctx.set(ctx=ctx)
        ctx.source.node.properties['use_external_resource'] = False

        output = \
            elasticip._associate_external_elasticip_or_instance(
                '127.0.0.1')

        self.assertEqual(False, output)

    def test_associate_external_elasticip_or_instance_external(self):

        ctx = self.mock_relationship_context(
            'test_associate_external_elasticip_or_instance_external')
        current_ctx.set(ctx=ctx)
        client = self._get_ec2_client()
        address_object = client.allocate_address()

        ctx.source.node.properties['use_external_resource'] = True
        ctx.target.node.properties['use_external_resource'] = True
        ctx.source.instance.runtime_properties['public_ip_address'] = \
            '127.0.0.1'

        output = \
            elasticip._associate_external_elasticip_or_instance(
                address_object.public_ip)

        self.assertEqual(True, output)

        self.assertIn(
            'public_ip_address',
            ctx.source.instance.runtime_properties)
        self.assertEqual(
            address_object.public_ip,
            ctx.source.instance.runtime_properties['public_ip_address'])
        address_object.delete()

    def test_release_external_elasticip(self):

        ctx = self.mock_cloudify_context(
            'test_release_external_elasticip')
        current_ctx.set(ctx=ctx)
        ctx.node.properties['use_external_resource'] = False

        output = \
            elasticip._release_external_elasticip()

        self.assertEqual(False, output)

    def test_release_external_elasticip_external(self):

        ctx = self.mock_cloudify_context(
            'test_release_external_elasticip')
        current_ctx.set(ctx=ctx)
        ctx.node.properties['use_external_resource'] = True
        ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID] = \
            '127.0.0.1'

        output = \
            elasticip._release_external_elasticip()

        self.assertEqual(True, output)
        self.assertNotIn(
            EXTERNAL_RESOURCE_ID,
            ctx.instance.runtime_properties)

    def test_allocate_external_elasticip(self):

        ctx = self.mock_cloudify_context(
            'test_allocate_external_elasticip')
        current_ctx.set(ctx=ctx)
        ctx.node.properties['use_external_resource'] = False

        output = \
            elasticip._allocate_external_elasticip()

        self.assertEqual(False, output)

    def test_allocate_external_elasticip_external(self):

        ctx = self.mock_cloudify_context(
            'test_allocate_external_elasticip_external')
        current_ctx.set(ctx=ctx)
        client = self._get_ec2_client()
        address_object = client.allocate_address()

        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = address_object.public_ip

        output = \
            elasticip._allocate_external_elasticip()

        self.assertEqual(True, output)
        self.assertIn(
            EXTERNAL_RESOURCE_ID,
            ctx.instance.runtime_properties)
        self.assertEqual(
            address_object.public_ip,
            ctx.instance.runtime_properties[EXTERNAL_RESOURCE_ID])

        address_object.delete()

    def test_allocate_external_elasticip_external_bad_id(self):

        ctx = self.mock_cloudify_context(
            'test_allocate_external_elasticip_external')
        current_ctx.set(ctx=ctx)
        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = '127.0.0.1'

        ex = self.assertRaises(
            NonRecoverableError,
            elasticip._allocate_external_elasticip)

        self.assertIn(
            'the given elasticip does not exist in the account',
            ex.message)


class EC2InstanceUnitTests(EC2LocalTestUtils):

    def test_instance_invalid_ami(self):
        ctx = self.mock_cloudify_context(
            'test_instance_invalid_ami')
        current_ctx.set(ctx=ctx)

        image_id = 'ami-65b95565'

        ex = self.assertRaises(
            NonRecoverableError, instance._get_image, image_id)

        self.assertIn('InvalidAMIID.NotFound', ex.message)

    def test_instance_get_image_id(self):

        ctx = self.mock_cloudify_context(
            'test_instance_get_image_id')
        current_ctx.set(ctx=ctx)

        image_object = instance._get_image(
            self.env.ubuntu_trusty_image_id)
        self.assertEqual(image_object.id,
                         self.env.ubuntu_trusty_image_id)

    def test_instance_external_invalid_instance(self):

        ctx = self.mock_cloudify_context(
            'test_instance_external_invalid_instance')
        current_ctx.set(ctx=ctx)

        ctx.node.properties['use_external_resource'] = True
        ctx.node.properties['resource_id'] = 'i-00z0zz0z'

        ex = self.assertRaises(
            NonRecoverableError, instance._create_external_instance)

        self.assertIn('is not in this account', ex.message)

    def test_get_instance_keypair(self):

        ctx = self.mock_cloudify_context(
            'test_get_instance_keypair')
        current_ctx.set(ctx=ctx)

        provider_variables = {
            'agents_keypair': '',
            'agents_security_group': ''
        }
        output = instance._get_instance_keypair(provider_variables)
        self.assertEqual(None, output)

    def test_get_instance_parameters(self):

        ctx = self.mock_cloudify_context(
            'test_get_instance_parameters')
        current_ctx.set(ctx=ctx)
        ctx.node.properties['image_id'] = 'abc'
        ctx.node.properties['instance_type'] = 'efg'
        ctx.node.properties['parameters']['image_id'] = 'abcd'
        ctx.node.properties['parameters']['key_name'] = 'xyz'
        parameters = instance._get_instance_parameters()
        self.assertIn('abcd', parameters['image_id'])
        self.assertIn('xyz', parameters['key_name'])
        self.assertIn('efg', parameters['instance_type'])
