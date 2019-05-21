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


