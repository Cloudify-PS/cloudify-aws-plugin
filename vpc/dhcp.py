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

# Cloudify imports
from . import constants
from core.base import AwsBaseNode, AwsBaseRelationship
from cloudify import ctx
from cloudify.decorators import operation


@operation
def creation_validation(**_):
    return DhcpOptions().creation_validation()


@operation
def create_dhcp_options(**_):
    return DhcpOptions().created()


@operation
def start_dhcp_options(**_):
    return DhcpOptions().started()


@operation
def delete_dhcp_options(**_):
    return DhcpOptions().deleted()


@operation
def associate_dhcp_options(**_):
    return DhcpAssociation().associated()


@operation
def restore_dhcp_options(**_):
    return DhcpAssociation().disassociated()


class DhcpAssociation(AwsBaseRelationship):

    def __init__(self):
        super(DhcpAssociation, self).__init__()
        self.source_get_all_handler = {
            'function': self.client.get_all_dhcp_options,
            'argument':
            '{0}_ids'.format(constants.DHCP_OPTIONS['AWS_RESOURCE_TYPE'])
        }

    def associate(self):
        associate_args = dict(
            dhcp_options_id=self.source_resource_id,
            vpc_id=self.target_resource_id
        )
        return self.execute(self.client.associate_dhcp_options,
                            associate_args, raise_on_falsy=True)

    def disassociate(self):
        disassociate_args = self.generate_disassociate_args()
        return self.execute(self.client.associate_dhcp_options,
                            disassociate_args, raise_on_falsy=True)

    def generate_disassociate_args(self):

        return dict(
            dhcp_options_id=ctx.target.instance.runtime_properties[
                'default_dhcp_options_id'],
            vpc_id=self.target_resource_id
        )


class DhcpOptions(AwsBaseNode):

    def __init__(self):
        super(DhcpOptions, self).__init__(
            constants.DHCP_OPTIONS['AWS_RESOURCE_TYPE'],
            constants.DHCP_OPTIONS['REQUIRED_PROPERTIES']
        )
        self.not_found_error = constants.DHCP_OPTIONS['NOT_FOUND_ERROR']
        self.get_all_handler = {
            'function': self.client.get_all_dhcp_options,
            'argument':
            '{0}_ids'.format(constants.DHCP_OPTIONS['AWS_RESOURCE_TYPE'])
        }

    def create(self):
        create_args = self.generate_create_args()
        dhcp_options = self.execute(self.client.create_dhcp_options,
                                    create_args, raise_on_falsy=True)
        self.resource_id = dhcp_options.id
        return True

    def generate_create_args(self):
        return dict(
            domain_name=ctx.node.properties['domain_name'],
            domain_name_servers=ctx.node.properties['domain_name_servers'],
            ntp_servers=ctx.node.properties['ntp_servers'],
            netbios_name_servers=ctx.node.properties['netbios_name_servers'],
            netbios_node_type=ctx.node.properties['netbios_node_type']
        )

    def start(self):
        return True

    def delete(self):
        delete_args = dict(dhcp_options_id=self.resource_id)
        return self.execute(self.client.delete_dhcp_options,
                            delete_args, raise_on_falsy=True)
