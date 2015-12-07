# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Hewlett Packard Enterprise Development LP <asicapi@hp.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""
topology_docker base node module.
"""

from __future__ import unicode_literals, absolute_import
from __future__ import print_function, division

from abc import ABCMeta, abstractmethod

from docker import Client
from six import add_metaclass

from topology.platforms.base import CommonNode


@add_metaclass(ABCMeta)
class DockerNode(CommonNode):
    """
    An instance of this class will create a detached Docker container.

    :param str identifier: The unique identifier of the node.
    :param str image: The image to run on this node.
    :param str command: The command to run when the container is brought up.
    """

    @abstractmethod
    def __init__(
            self, identifier,
            image='ubuntu', command='bash',
            binds=None, network_mode='none', **kwargs):

        super(DockerNode, self).__init__(identifier, **kwargs)

        self._pid = None
        self._image = image
        self._command = command
        self._client = Client()

        self._host_config = self._client.create_host_config(
            # Container is given access to all devices
            privileged=True,
            # Avoid connecting to host bridge, usually docker0
            network_mode=network_mode,
            binds=binds
        )

        self.container_id = self._client.create_container(
            image=self._image,
            command=self._command,
            name='{}_{}'.format(identifier, str(id(self))),
            detach=True,
            tty=True,
            host_config=self._host_config
        )['Id']

    def notify_add_biport(self, node, biport):
        """
        Get notified that a new biport was added to this engine node.

        :param node: The specification node that spawn this engine node.
        :type node: pynml.nml.Node
        :param biport: The specification bidirectional port added.
        :type biport: pynml.nml.BidirectionalPort
        :rtype: str
        :return: The assigned interface name of the port.
        """
        return biport.metadata.get('label', biport.identifier)

    def notify_add_bilink(self, nodeport, bilink):
        """
        Get notified that a new bilink was added to a port of this engine node.

        :param nodeport: A tuple with the specification node and port being
         linked.
        :type nodeport: (pynml.nml.Node, pynml.nml.BidirectionalPort)
        :param bilink: The specification bidirectional link added.
        :type bilink: pynml.nml.BidirectionalLink
        """

    def notify_post_build(self):
        """
        Get notified that the post build stage of the topology build was
        reached.
        """

    def start(self):
        """
        Start the docker node and configures a netns for it.
        """
        self._client.start(self.container_id)
        self._pid = self._client.inspect_container(
            self.container_id)['State']['Pid']

    def stop(self):
        """
        Request container to stop.
        """
        self._client.stop(self.container_id)
        self._client.wait(self.container_id)
        self._client.remove_container(self.container_id)

    def pause(self):
        """
        Pause the current node.
        """
        for portlbl in self.ports:
            self.port_state(portlbl, False)
        self._client.pause(self.container_id)

    def unpause(self):
        """
        Unpause the current node.
        """
        self._client.unpause(self.container_id)
        for portlbl in self.ports:
            self.port_state(portlbl, True)

    def port_state(self, portlbl, state):
        """
        Set the given port label to the given state.

        :param str portlbl: The label of the port.
        :param bool state: True for up, False for down.
        """
        # Given the fact that bash is the default command in the constructor,
        # it is a good assumption that the node has a bash shell. Is not
        # guaranteed, but if it is not the case, the node has the capability
        # to override this function to provide the correct logic.
        iface = self.ports[portlbl]
        self(
            'ip link set dev {} {}'.format(iface, 'up' if state else 'down'),
            shell='bash'
        )


__all__ = ['DockerNode']
