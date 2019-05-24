# Copyright (C) 2018 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions
# and limitations under the License.
#
#
# SPDX-License-Identifier: Apache-2.0

from wca.runners import Runner
from wca import components
from wca import config
from prm.model_distribution.build import BuilderRunner
from prm.model_distribution.db import ModelDatabase
import ruamel.yaml as yaml
import logging

log = logging.getLogger(__name__)

def instantiate_from_yaml_and_start_runner():
    """test code witout building pex
    """
    # -r register this components
    components.register_components(
        ['prm.model_distribution.build:BuilderRunner', 'prm.model_distribution.db:ModelDatabase', 'prm.model_distribution.model:DistriModel'])

    with open("model_distribution_config.yaml", 'r') as stream:
        try:
            log.info("yaml instantiate success")
            configuration = yaml.safe_load(stream)
            if 'runner' in configuration:
                runner = configuration['runner']

                exit_code = runner.run()
                exit(exit_code)

        except yaml.YAMLError as exc:
            log.error(exc)


