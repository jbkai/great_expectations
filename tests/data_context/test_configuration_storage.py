import logging
logger = logging.getLogger(__name__)
import pytest
from six import PY2

import os


@pytest.fixture()
def data_context_config_string():
    config_str = \
        """
# This is a comment
# it should be preserved.
datasources:
  # this comments should also be preserved
  default:
    type: pandas
    generators:
      # The name default is read if no datasource or generator is specified
      default:
        type: filesystem
        base_dir: /data
"""


def test_preserve_comments(data_context):
    print(data_context._project_config)
    context_root_dir = data_context.root_directory

    config_filepath = os.path.join(context_root_dir, "great_expectations.yml")
    print(config_filepath)

    with open(config_filepath, "r") as infile:
        content = infile.read()

    print("++++++++++++++++++++++++++++++++++++++++")
    print(content)
    print("----------------------------------------")

    data_context.add_datasource("test_datasource", "pandas")

    with open(config_filepath, "r") as infile:

        content = infile.read()

        print("++++++++++++++++++++++++++++++++++++++++")
        print(content)
        print("----------------------------------------")

        if PY2:
            assert content == """\
plugins_directory: plugins/
stores: {}
datasources:
  # For example, this one.
  mydatasource:
    type: pandas
    generators:
      # The name default is read if no datasource or generator is specified
      mygenerator:
        type: subdir_reader
        base_directory: ../data


  test_datasource:
    generators:
      default:
        reader_options:
          engine: python
          sep:
        base_directory: /data
        type: subdir_reader
    data_asset_type:
      class_name: PandasDataset
    type: pandas
data_docs:
  sites:
"""
        else:
          content_lines = set(content.split("\n"))
          test_content_lines = set(content.split("\n"))
          assert content_lines == test_content_lines
