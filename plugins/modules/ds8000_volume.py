#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (C) 2021 IBM CORPORATION
# Apache License, Version 2.0 (see https://opensource.org/licenses/Apache-2.0)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r'''
---
module: ds8000_volume
short_description: Manage DS8000 volumes
description:
  - Manage DS8000 volumes.
version_added: "1.0.0"
author: Matan Carmeli (@matancarmeli7)
options:
  name:
    description:
      - The name of the DS8000 volume to work with.
      - Required when I(state=present)
    type: str
  state:
    description:
    - Specify the state the DS8000 volume should be in.
    type: str
    default: present
    choices:
      - present
      - absent
  volume_id:
    description:
      - The volume ID of the DS8000 volume to work with.
      - Required when I(state=absent)
    type: str
  volume_type:
    description:
      - The volume type that will be created.
      - Valid value is fixed block C(fb) or count key data C(ckd).
    choices:
      - fb
      - ckd
    type: str
    default: fb
  capacity:
    description:
      - The size of the volume.
      - Required when I(state=present)
    type: str
  capacity_type:
    description:
      - The units of measurement of the size of the volume.
    choices:
      - gib
      - bytes
      - cyl
      - mod1
    type: str
    default: gib
  lss:
    description:
      - The logical subsystem (lss) that the volume will be created on.
    type: str
  pool:
    description:
      - The pool id that the volume will be created on.
      - Required when I(state=present)
    type: str
  storage_allocation_method:
    description:
      - Choose the storage allocation method that the DS8000 will use in creating your volume.
      - Valid value is C(none), extent space-efficient C(ese), track space-efficient C(tse).  # TODO remove tse?
    choices:
      - none
      - ese
      - tse
    type: str
    default: none
notes:
  - Does not support C(check_mode).
  - Is not idempotent.
extends_documentation_fragment:
  - ibm.ds8000.ds8000.documentation
'''

EXAMPLES = r'''
- name: Ensure that a volume exists in the storage
  ibm.ds8000.ds8000_volume:
    hostname: "{{ ds8000_host }}"
    username: "{{ ds8000_username }}"
    password: "{{ ds8000_password }}"
    name: volume_name_test
    state: present
    pool: P1
    capacity: "1"
  register: volume
- debug:
  var: volume.id

- name: Ensure that a volume does not exist in the storage
  ibm.ds8000.ds8000_volume:
    hostname: "{{ ds8000_host }}"
    username: "{{ ds8000_username }}"
    password: "{{ ds8000_password }}"
    name: volume_name_test
    state: absent
'''

RETURN = r'''
volumes:
    description: A list of dictionaries describing the volumes.
    returned: I(state=present) changed
    type: list
    contains:
      volume:
        description: A dictionary describing the volume properties.
        type: dict
        contains:
          id:
            description: Volume ID.
            type: str
            sample: "1000"
          name:
            description: Volume name.
            type: str
            sample: "ansible"
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_native
from ansible_collections.ibm.ds8000.plugins.module_utils.ds8000 import Ds8000ManagerBase, ds8000_argument_spec, ABSENT, PRESENT


class VolumeManager(Ds8000ManagerBase):
    def volume_present(self):
        self._create_volume()
        return {'changed': self.changed, 'failed': self.failed, 'volumes': self.volume_facts}

    def volume_absent(self, volume_id=''):
        self._delete_ds8000_volume(volume_id)
        return {'changed': self.changed, 'failed': self.failed}

    def _create_volume(self):
        volume_type = self.params['volume_type']
        try:
            kwargs = dict(
                name=self.params['name'],
                cap=self.params['capacity'],
                pool=self.params['pool'],
                tp=self.params['storage_allocation_method'],
                captype=self.params['capacity_type'],
                lss=self.params['lss'],
            )
            volumes = []
            if volume_type == 'fb':
                volumes = self.client.create_volume_fb(**kwargs)
            elif volume_type == 'ckd':
                volumes = self.client.create_volume_ckd(**kwargs)
            self.volume_facts = self.get_ds8000_objects_from_command_output(volumes)
            self.changed = True
        except Exception as generic_exc:
            self.failed = True
            self.module.fail_json(msg="Failed to create volume on the DS8000 storage system. ERR: {error}".format(error=to_native(generic_exc)))

    def _delete_ds8000_volume(self, volume_id):
        try:
            self.client.delete_volume(volume_id)
            self.changed = True
        except Exception as generic_exc:
            self.failed = True
            self.module.fail_json(
                msg="Failed to delete the volume {volume_id} from the DS8000 storage system. "
                "ERR: {error}".format(volume_id=volume_id, error=to_native(generic_exc))
            )


def main():
    argument_spec = ds8000_argument_spec()
    argument_spec.update(
        name=dict(type='str'),
        state=dict(type='str', default=PRESENT, choices=[ABSENT, PRESENT]),
        volume_type=dict(type='str', default='fb', choices=['fb', 'ckd']),
        pool=dict(type='str'),
        capacity=dict(type='str'),
        capacity_type=dict(type='str', default='gib', choices=['gib', 'bytes', 'cyl', 'mod1']),
        lss=dict(type='str'),
        storage_allocation_method=dict(type='str', default='none', choices=['none', 'ese', 'tse']),
        volume_id=dict(type='str'),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[
            ['state', PRESENT, ('name', 'capacity', 'pool')],
            ['state', ABSENT, ('volume_id',)],
        ],
        supports_check_mode=False,
    )

    volume_manager = VolumeManager(module)

    if module.params['state'] == PRESENT:
        result = volume_manager.volume_present()
    elif module.params['state'] == ABSENT:
        result = volume_manager.volume_absent(volume_id=module.params['volume_id'])

    if result['failed']:
        module.fail_json(**result)
    else:
        module.exit_json(**result)


if __name__ == '__main__':
    main()
