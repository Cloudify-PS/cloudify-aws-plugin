########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
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

# Third-party Imports
import boto.exception

# Cloudify Imports
from ec2 import connection
from cloudify.exceptions import NonRecoverableError, RecoverableError


def save_key_pair(key_pair_object, ctx):
    """ Saves the key pair to the file specified in the blueprint. """

    ctx.logger.debug('Attempting to save the key_pair_object.')

    try:
        key_pair_object.save(ctx.node.properties['private_key_path'])
    except OSError:
        raise NonRecoverableError('Unable to save key pair to file: {0}.'
                                  'OS Returned: {1}'.format(
                                      ctx.node.properties['private_key_path'],
                                      OSError))


def delete_key_pair(key_pair_name, ctx):
    """ Deletes the key pair in the file specified in the blueprint. """

    ctx.logger.debug('Attempting to save the key_pair_object.')

    path = os.path.expanduser(ctx.node.properties['private_key_path'])
    file = os.path.join(path,
                        '{0}{1}'.format(
                            ctx.node.properties['resource_id'],
                            '.pem'))
    if os.path.exists(file):
        try:
            os.remove(file)
        except OSError:
            raise NonRecoverableError('Unable to save key pair to file: {0}.'
                                      'OS Returned: {1}'.format(path,
                                                                str(OSError)))


def search_for_key_file(ctx):
    """ Indicates whether the file exists locally. """

    path = os.path.expanduser(ctx.node.properties['private_key_path'])
    file = os.path.join(path,
                        '{0}{1}'.format(
                            ctx.node.properties['resource_id'],
                            '.pem'))
    if os.path.exists(file):
        return True
    else:
        return False


def get_instance_attribute(instance_id, attribute, check_interval, ctx):
    """ given the related instance object
        the given variable can be retrieved and returned
    """

    instance = get_instance_from_id(instance_id, ctx=ctx)
    if 'running' not in instance.update():
        raise RecoverableError('Waiting for server to be running. '
                               'Retrying...', retry_after=check_interval)

    attribute = getattr(instance, attribute)
    return attribute


def get_private_dns_name(instance, check_interval, ctx):
    """ returns the private_dns_name variable for a given instance
    """
    return get_instance_attribute(instance, 'private_dns_name',
                                  check_interval, ctx=ctx)


def get_public_dns_name(instance, check_interval, ctx):
    """ returns the public_dns_name variable for a given instance
    """
    return get_instance_attribute(instance, 'public_dns_name',
                                  check_interval, ctx=ctx)


def get_private_ip_address(instance, check_interval, ctx):
    """ returns the private_ip_address variable for a given instance
    """
    return get_instance_attribute(instance, 'private_ip_address',
                                  check_interval, ctx=ctx)


def get_public_ip_address(instance, check_interval, ctx):
    """ returns the public_ip_address variable for a given instance
    """
    return get_instance_attribute(instance, 'ip_address',
                                  check_interval, ctx=ctx)


def get_instance_state(ctx):
    instance = get_instance_from_id(ctx=ctx)
    ctx.logger.debug('Checking the instance state for {0}.'
                     .format(instance.id))
    state = instance.update()
    ctx.logger.debug('Instance state is {0}.'
                     .format(state))
    return instance.state_code


def get_instance_from_id(ctx):
    """ using the instance_id retrieves the instance object
        from the API and returns the object.
    """
    instance_id = ctx.node.properties['resource_id']
    ec2_client = connection.EC2ConnectionClient().client()

    try:
        reservations = ec2_client.get_all_reservations(instance_id)
    except boto.exception.EC2ResponseError as e:
        report_all_instances(ctx=ctx)
        raise NonRecoverableError('Error. '
                                  'Failed to get instance by id: '
                                  'API returned: {0}.'
                                  .format(ctx.instance.id, str(e)))
    except boto.exception.BotoServerError as e:
        raise NonRecoverableError('Error. '
                                  'Failed to get instance by id: '
                                  'API returned: {0}.'
                                  .format(ctx.instance.id, str(e)))

    instance = reservations[0].instances[0]

    return instance


def get_security_group_from_id(ctx):
    ec2_client = connection.EC2ConnectionClient().client()
    group = ctx.node.properties['resource_id']
    ctx.logger.debug('Getting Security Group by ID: {0}'.format(group))

    try:
        group = ec2_client.get_all_security_groups(group_ids=group)
    except boto.exception.EC2ResponseError as e:
        report_all_security_groups(ctx=ctx)
        raise NonRecoverableError('Error. '
                                  'Failed to group by id: '
                                  'API returned: {0}.'
                                  .format(str(e)))
    except boto.exception.BotoServerError as e:
        raise NonRecoverableError('Error. '
                                  'Failed to group by id: '
                                  'API returned: {0}.'
                                  .format(str(e)))
    return group.id


def report_all_instances(ctx):
    ec2_client = connection.EC2ConnectionClient().client()

    try:
        reservations = ec2_client.get_all_reservations()
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('Error. '
                                  'Failed to get instances: '
                                  'API returned: {1}.'
                                  .format(ctx.instance.id, str(e)))

    instances = [instance for res in reservations
                 for instance in res.instances]

    message = []
    for instance in instances:
        message.append('{}\n'.format(instance))

    ctx.logger.info('Available instances: {0}'.format(message))


def report_all_security_groups(ctx):
    ec2_client = connection.EC2ConnectionClient().client()

    try:
        groups = ec2_client.get_all_security_groups()
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('Error. '
                                  'Failed to get security groups: '
                                  'API returned: {0}.'
                                  .format(str(e)))
    message = []
    for group in groups:
        message.append('{}\n'.format(group))

    ctx.logger.info('Available groups: {0}'.format(message))


def get_key_pair_by_id(ctx):
    ec2_client = connection.EC2ConnectionClient().client()

    try:
        key = ec2_client.get_key_pair(ctx.node.properties['resource_id'])
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('Error. '
                                  'Failed to get key pair: '
                                  'API returned: {0}.'
                                  .format(str(e)))

    return key.name


def get_address_by_id(id, ctx):
    ec2_client = connection.EC2ConnectionClient().client()
    try:
        address = ec2_client.get_all_addresses(id)
    except boto.exception.EC2ResponseError as e:
        report_all_addresses(ctx=ctx)
        raise NonRecoverableError('Error. '
                                  'Failed to get instances: '
                                  'API returned: {1}.'
                                  .format(ctx.instance.id, str(e)))
    except (boto.exception.BotoServerError) as e:
        raise NonRecoverableError('Error. '
                                  'Failed to get instances: '
                                  'API returned: {1}.'
                                  .format(ctx.instance.id, str(e)))
    return address.public_ip


def report_all_addresses(ctx):
    ec2_client = connection.EC2ConnectionClient().client()
    try:
        addresses = ec2_client.get_all_addresses()
    except (boto.exception.EC2ResponseError,
            boto.exception.BotoServerError) as e:
        raise NonRecoverableError('Error. '
                                  'Failed to get key pair: '
                                  'API returned: {0}.'
                                  .format(str(e)))
    message = []
    for address in addresses:
        message.append('{}\n'.format(address))

    ctx.logger.info('Available addresses: {0}'.format(message))
