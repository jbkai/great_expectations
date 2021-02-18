import os
import shutil
import subprocess
from typing import List
from unittest import mock

import pytest
from click.testing import CliRunner, Result
from ruamel.yaml import YAML

from great_expectations import DataContext
from great_expectations.cli import cli
from great_expectations.core import ExpectationSuite
from great_expectations.data_context.types.base import DataContextConfigDefaults
from tests.cli.utils import (
    LEGACY_CONFIG_DEFAULT_CHECKPOINT_STORE_MESSAGE,
    VALIDATION_OPERATORS_DEPRECATION_MESSAGE,
    assert_no_logging_messages_or_tracebacks,
)

yaml = YAML()
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.default_flow_style = False


@pytest.fixture
def titanic_checkpoint(
    titanic_data_context_stats_enabled_config_version_2, titanic_expectation_suite
):
    csv_path = os.path.join(
        titanic_data_context_stats_enabled_config_version_2.root_directory,
        "..",
        "data",
        "Titanic.csv",
    )
    return {
        "validation_operator_name": "action_list_operator",
        "batches": [
            {
                "batch_kwargs": {
                    "path": csv_path,
                    "datasource": "mydatasource",
                    "reader_method": "read_csv",
                },
                "expectation_suite_names": [
                    titanic_expectation_suite.expectation_suite_name
                ],
            },
        ],
    }


@pytest.fixture
def titanic_data_context_v2_with_checkpoint_suite_and_stats_enabled(
    titanic_data_context_stats_enabled_config_version_2,
    titanic_checkpoint,
    titanic_expectation_suite,
):
    yaml = YAML()
    context: DataContext = titanic_data_context_stats_enabled_config_version_2
    context.save_expectation_suite(titanic_expectation_suite)
    # TODO context should save a checkpoint
    checkpoint_path = os.path.join(
        context.root_directory,
        DataContextConfigDefaults.CHECKPOINTS_BASE_DIRECTORY.value,
        "my_checkpoint.yml",
    )
    with open(checkpoint_path, "w") as f:
        yaml.dump(titanic_checkpoint, f)
    assert os.path.isfile(checkpoint_path)
    assert context.list_expectation_suite_names() == ["Titanic.warning"]
    assert context.list_checkpoints() == ["my_checkpoint"]
    return context


@mock.patch(
    "great_expectations.core.usage_statistics.usage_statistics.UsageStatisticsHandler.emit"
)
def test_checkpoint_list_with_no_checkpoints_with_ge_config_v3(
    mock_emit, caplog, empty_data_context_stats_enabled
):
    context: DataContext = empty_data_context_stats_enabled
    root_dir = context.root_directory
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        cli,
        f"checkpoint list -d {root_dir}",
        catch_exceptions=False,
    )
    stdout = result.stdout
    assert result.exit_code == 0
    assert "No checkpoints found." in stdout
    assert "Use the command `great_expectations checkpoint new` to create one" in stdout

    assert mock_emit.call_count == 2
    assert mock_emit.call_args_list == [
        mock.call(
            {"event_payload": {}, "event": "data_context.__init__", "success": True}
        ),
        mock.call(
            {"event": "cli.checkpoint.list", "event_payload": {}, "success": True}
        ),
    ]

    assert_no_logging_messages_or_tracebacks(caplog, result)


@mock.patch(
    "great_expectations.core.usage_statistics.usage_statistics.UsageStatisticsHandler.emit"
)
def test_checkpoint_list_with_single_checkpoint_with_ge_config_v3(
    mock_emit,
    caplog,
    empty_context_with_checkpoint_v1_stats_enabled,
):
    context: DataContext = empty_context_with_checkpoint_v1_stats_enabled
    root_dir: str = context.root_directory
    runner: CliRunner = CliRunner(mix_stderr=False)
    result: Result = runner.invoke(
        cli,
        f"checkpoint list -d {root_dir}",
        catch_exceptions=False,
    )
    stdout: str = result.stdout
    assert result.exit_code == 0
    assert "Found 1 checkpoint." in stdout
    assert "my_v1_checkpoint" in stdout

    assert mock_emit.call_count == 2
    assert mock_emit.call_args_list == [
        mock.call(
            {"event_payload": {}, "event": "data_context.__init__", "success": True}
        ),
        mock.call(
            {"event": "cli.checkpoint.list", "event_payload": {}, "success": True}
        ),
    ]

    assert_no_logging_messages_or_tracebacks(
        caplog,
        result,
    )


@mock.patch(
    "great_expectations.core.usage_statistics.usage_statistics.UsageStatisticsHandler.emit"
)
def test_checkpoint_list_with_eight_checkpoints_with_ge_config_v3(
    mock_emit,
    caplog,
    titanic_pandas_data_context_with_v013_datasource_stats_enabled_with_checkpoints_v1_with_templates,
):
    context: DataContext = titanic_pandas_data_context_with_v013_datasource_stats_enabled_with_checkpoints_v1_with_templates
    root_dir: str = context.root_directory
    runner: CliRunner = CliRunner(mix_stderr=False)
    result: Result = runner.invoke(
        cli,
        f"checkpoint list -d {root_dir}",
        catch_exceptions=False,
    )
    stdout: str = result.stdout
    assert result.exit_code == 0
    assert "Found 8 checkpoints." in stdout
    checkpoint_names_list: List[str] = [
        "my_simple_checkpoint_with_slack_and_notify_with_all",
        "my_nested_checkpoint_template_1",
        "my_nested_checkpoint_template_3",
        "my_nested_checkpoint_template_2",
        "my_simple_checkpoint_with_site_names",
        "my_minimal_simple_checkpoint",
        "my_simple_checkpoint_with_slack",
        "my_simple_template_checkpoint",
    ]
    assert all([checkpoint_name in stdout for checkpoint_name in checkpoint_names_list])

    assert mock_emit.call_count == 2
    assert mock_emit.call_args_list == [
        mock.call(
            {"event_payload": {}, "event": "data_context.__init__", "success": True}
        ),
        mock.call(
            {"event": "cli.checkpoint.list", "event_payload": {}, "success": True}
        ),
    ]

    assert_no_logging_messages_or_tracebacks(
        caplog,
        result,
    )


@mock.patch(
    "great_expectations.core.usage_statistics.usage_statistics.UsageStatisticsHandler.emit"
)
def test_checkpoint_new_raises_error_on_no_suite_found_with_ge_config_v2(
    mock_emit, caplog, titanic_data_context_stats_enabled_config_version_2
):
    context: DataContext = titanic_data_context_stats_enabled_config_version_2
    root_dir = context.root_directory
    assert context.list_expectation_suite_names() == []
    mock_emit.reset_mock()

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        cli,
        f"checkpoint new foo not_a_suite -d {root_dir}",
        catch_exceptions=False,
    )
    stdout = result.stdout
    assert result.exit_code == 1
    assert "Could not find a suite named `not_a_suite`" in stdout

    assert mock_emit.call_count == 2
    assert mock_emit.call_args_list == [
        mock.call(
            {"event_payload": {}, "event": "data_context.__init__", "success": True}
        ),
        mock.call(
            {"event": "cli.checkpoint.new", "event_payload": {}, "success": False}
        ),
    ]

    assert_no_logging_messages_or_tracebacks(
        my_caplog=caplog,
        click_result=result,
        allowed_deprecation_message=LEGACY_CONFIG_DEFAULT_CHECKPOINT_STORE_MESSAGE,
    )


@mock.patch(
    "great_expectations.core.usage_statistics.usage_statistics.UsageStatisticsHandler.emit"
)
def test_checkpoint_new_raises_error_on_existing_checkpoint_with_ge_config_v2(
    mock_emit,
    caplog,
    titanic_data_context_stats_enabled_config_version_2_with_checkpoint,
):
    context: DataContext = (
        titanic_data_context_stats_enabled_config_version_2_with_checkpoint
    )
    root_dir = context.root_directory
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        cli,
        f"checkpoint new my_checkpoint suite -d {root_dir}",
        catch_exceptions=False,
    )
    stdout = result.stdout
    assert result.exit_code == 1
    assert (
        "A checkpoint named `my_checkpoint` already exists. Please choose a new name."
        in stdout
    )

    assert mock_emit.call_count == 2
    assert mock_emit.call_args_list == [
        mock.call(
            {"event_payload": {}, "event": "data_context.__init__", "success": True}
        ),
        mock.call(
            {"event": "cli.checkpoint.new", "event_payload": {}, "success": False}
        ),
    ]

    assert_no_logging_messages_or_tracebacks(
        caplog,
        result,
        allowed_deprecation_message=LEGACY_CONFIG_DEFAULT_CHECKPOINT_STORE_MESSAGE,
    )


@mock.patch(
    "great_expectations.core.usage_statistics.usage_statistics.UsageStatisticsHandler.emit"
)
def test_checkpoint_new_happy_path_generates_checkpoint_yml_with_comments_with_ge_config_v2(
    mock_emit,
    caplog,
    titanic_data_context_stats_enabled_config_version_2,
    titanic_expectation_suite,
):
    context: DataContext = titanic_data_context_stats_enabled_config_version_2
    root_dir = context.root_directory
    assert context.list_checkpoints() == []
    context.save_expectation_suite(titanic_expectation_suite)
    assert context.list_expectation_suite_names() == ["Titanic.warning"]
    mock_emit.reset_mock()

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        cli,
        f"checkpoint new passengers Titanic.warning -d {root_dir}",
        input="1\n1\n",
        catch_exceptions=False,
    )
    stdout = result.stdout
    assert result.exit_code == 0
    assert "A checkpoint named `passengers` was added to your project" in stdout

    assert mock_emit.call_count == 2
    assert mock_emit.call_args_list == [
        mock.call(
            {"event_payload": {}, "event": "data_context.__init__", "success": True}
        ),
        mock.call(
            {"event": "cli.checkpoint.new", "event_payload": {}, "success": True}
        ),
    ]
    expected_checkpoint = os.path.join(
        root_dir,
        DataContextConfigDefaults.CHECKPOINTS_BASE_DIRECTORY.value,
        "passengers.yml",
    )
    assert os.path.isfile(expected_checkpoint)

    # Newup a context for additional assertions
    context: DataContext = DataContext(root_dir)
    assert context.list_checkpoints() == ["passengers"]

    with open(expected_checkpoint) as f:
        obs_file = f.read()

        # This is snapshot-ish to prove that comments remain in place
        # TODO: <Alex>ALEX</Alex>
        #     assert (
        #         """\
        # # This checkpoint was created by the command `great_expectations checkpoint new`.
        # #
        # # A checkpoint is a list of one or more batches paired with one or more
        # # Expectation Suites and a configurable Validation Operator.
        # #
        # # It can be run with the `great_expectations checkpoint run` command.
        # # You can edit this file to add batches of data and expectation suites.
        # #
        # # For more details please see
        # # https://docs.greatexpectations.io/en/latest/guides/how_to_guides/validation/how_to_add_validations_data_or_suites_to_a_checkpoint.html
        # validation_operator_name: action_list_operator
        # # Batches are a list of batch_kwargs paired with a list of one or more suite
        # # names. A checkpoint can have one or more batches. This makes deploying
        # # Great Expectations in your pipelines easy!
        # batches:
        #   - batch_kwargs:"""
        #         in obs_file
        #     )
        assert (
            """\
batches:
  - batch_kwargs:"""
            in obs_file
        )

    assert "/data/Titanic.csv" in obs_file

    assert (
        """datasource: mydatasource
      data_asset_name: Titanic
    expectation_suite_names:
      - Titanic.warning
"""
        in obs_file
    )

    assert_no_logging_messages_or_tracebacks(
        my_caplog=caplog,
        click_result=result,
        allowed_deprecation_message=LEGACY_CONFIG_DEFAULT_CHECKPOINT_STORE_MESSAGE,
    )


@mock.patch(
    "great_expectations.core.usage_statistics.usage_statistics.UsageStatisticsHandler.emit"
)
def test_checkpoint_new_specify_datasource_with_ge_config_v2(
    mock_emit,
    caplog,
    titanic_data_context_stats_enabled_config_version_2,
    titanic_expectation_suite,
):
    context: DataContext = titanic_data_context_stats_enabled_config_version_2
    root_dir = context.root_directory
    assert context.list_checkpoints() == []
    context.save_expectation_suite(titanic_expectation_suite)
    assert context.list_expectation_suite_names() == ["Titanic.warning"]
    mock_emit.reset_mock()

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        cli,
        f"checkpoint new passengers Titanic.warning -d {root_dir} --datasource mydatasource",
        input="1\n1\n",
        catch_exceptions=False,
    )
    stdout = result.stdout
    assert result.exit_code == 0
    assert "A checkpoint named `passengers` was added to your project" in stdout

    assert mock_emit.call_count == 2
    assert mock_emit.call_args_list == [
        mock.call(
            {"event_payload": {}, "event": "data_context.__init__", "success": True}
        ),
        mock.call(
            {"event": "cli.checkpoint.new", "event_payload": {}, "success": True}
        ),
    ]
    expected_checkpoint = os.path.join(
        root_dir,
        DataContextConfigDefaults.CHECKPOINTS_BASE_DIRECTORY.value,
        "passengers.yml",
    )
    assert os.path.isfile(expected_checkpoint)

    # Newup a context for additional assertions
    context: DataContext = DataContext(root_dir)
    assert context.list_checkpoints() == ["passengers"]

    assert_no_logging_messages_or_tracebacks(
        my_caplog=caplog,
        click_result=result,
        allowed_deprecation_message=LEGACY_CONFIG_DEFAULT_CHECKPOINT_STORE_MESSAGE,
    )


@mock.patch(
    "great_expectations.core.usage_statistics.usage_statistics.UsageStatisticsHandler.emit"
)
def test_checkpoint_new_raises_error_if_checkpoints_directory_is_missing_with_ge_config_v2(
    mock_emit,
    caplog,
    titanic_data_context_stats_enabled_config_version_2,
    titanic_expectation_suite,
):
    context: DataContext = titanic_data_context_stats_enabled_config_version_2
    root_dir = context.root_directory
    checkpoints_dir = os.path.join(
        root_dir, DataContextConfigDefaults.CHECKPOINTS_BASE_DIRECTORY.value
    )
    shutil.rmtree(checkpoints_dir)
    assert not os.path.isdir(checkpoints_dir)

    context.save_expectation_suite(titanic_expectation_suite)
    assert context.list_expectation_suite_names() == ["Titanic.warning"]
    mock_emit.reset_mock()

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        cli,
        f"checkpoint new passengers Titanic.warning -d {root_dir}",
        input="1\n1\n",
        catch_exceptions=False,
    )
    stdout = result.stdout
    assert result.exit_code == 1
    assert (
        'Attempted to access the "checkpoint_store_name" field with a legacy config version (2.0) and no `checkpoints` directory.'
        in stdout
    )

    assert mock_emit.call_count == 2
    assert mock_emit.call_args_list == [
        mock.call(
            {"event_payload": {}, "event": "data_context.__init__", "success": True}
        ),
        mock.call(
            {"event": "cli.checkpoint.new", "event_payload": {}, "success": False}
        ),
    ]

    assert_no_logging_messages_or_tracebacks(
        my_caplog=caplog,
        click_result=result,
    )


@mock.patch(
    "great_expectations.core.usage_statistics.usage_statistics.UsageStatisticsHandler.emit"
)
# TODO: <Alex>ALEX Delete "_with_ge_config_v3" when all done</Alex>
def test_checkpoint_run_raises_error_if_checkpoint_is_not_found_with_ge_config_v3(
    mock_emit, caplog, empty_context_with_checkpoint_v1_stats_enabled
):
    context: DataContext = empty_context_with_checkpoint_v1_stats_enabled
    root_dir: str = context.root_directory
    mock_emit.reset_mock()

    runner: CliRunner = CliRunner(mix_stderr=False)
    result: Result = runner.invoke(
        cli,
        f"checkpoint run my_checkpoint -d {root_dir}",
        catch_exceptions=False,
    )
    stdout: str = result.stdout
    assert result.exit_code == 1
    assert "Could not find checkpoint `my_checkpoint`" in stdout
    assert "Try running" in stdout

    assert mock_emit.call_count == 2
    assert mock_emit.call_args_list == [
        mock.call(
            {"event_payload": {}, "event": "data_context.__init__", "success": True}
        ),
        mock.call(
            {"event": "cli.checkpoint.run", "event_payload": {}, "success": False}
        ),
    ]

    assert_no_logging_messages_or_tracebacks(
        my_caplog=caplog,
        click_result=result,
    )


@mock.patch(
    "great_expectations.core.usage_statistics.usage_statistics.UsageStatisticsHandler.emit"
)
def test_checkpoint_run_on_checkpoint_with_not_found_suite_raises_error_with_ge_config_v3(
    mock_emit,
    caplog,
    titanic_pandas_data_context_with_v013_datasource_stats_enabled_with_checkpoints_v1_with_templates,
    monkeypatch,
):
    monkeypatch.setenv("VAR", "test")
    monkeypatch.setenv("MY_PARAM", "1")
    monkeypatch.setenv("OLD_PARAM", "2")

    context: DataContext = titanic_pandas_data_context_with_v013_datasource_stats_enabled_with_checkpoints_v1_with_templates
    root_dir: str = context.root_directory

    runner: CliRunner = CliRunner(mix_stderr=False)
    result: Result = runner.invoke(
        cli,
        f"checkpoint run my_nested_checkpoint_template_1 -d {root_dir}",
        catch_exceptions=False,
    )
    stdout: str = result.stdout
    assert result.exit_code == 1

    assert "expectation_suite suite_from_template_1 not found" in stdout

    assert mock_emit.call_count == 2
    assert mock_emit.call_args_list == [
        mock.call(
            {"event_payload": {}, "event": "data_context.__init__", "success": True}
        ),
        mock.call(
            {"event": "cli.checkpoint.run", "event_payload": {}, "success": False}
        ),
    ]

    assert_no_logging_messages_or_tracebacks(
        my_caplog=caplog,
        click_result=result,
    )

    monkeypatch.delenv("VAR")
    monkeypatch.delenv("MY_PARAM")
    monkeypatch.delenv("OLD_PARAM")


@mock.patch(
    "great_expectations.core.usage_statistics.usage_statistics.UsageStatisticsHandler.emit"
)
def test_checkpoint_run_on_checkpoint_with_batch_load_problem_raises_error_with_ge_config_v3(
    mock_emit,
    caplog,
    titanic_pandas_data_context_with_v013_datasource_with_checkpoints_v1_with_empty_store_stats_enabled,
    monkeypatch,
):
    monkeypatch.setenv("VAR", "test")
    monkeypatch.setenv("MY_PARAM", "1")
    monkeypatch.setenv("OLD_PARAM", "2")

    context: DataContext = titanic_pandas_data_context_with_v013_datasource_with_checkpoints_v1_with_empty_store_stats_enabled
    suite: ExpectationSuite = context.create_expectation_suite(
        expectation_suite_name="bar"
    )
    context.save_expectation_suite(expectation_suite=suite)
    assert context.list_expectation_suite_names() == ["bar"]
    mock_emit.reset_mock()

    root_dir: str = context.root_directory
    checkpoint_file_path: str = os.path.join(
        context.root_directory,
        DataContextConfigDefaults.CHECKPOINTS_BASE_DIRECTORY.value,
        "bad_batch.yml",
    )

    checkpoint_yaml_config: str = f"""
    name: bad_batch
    config_version: 1
    class_name: Checkpoint
    run_name_template: "%Y-%M-foo-bar-template-$VAR"
    validations:
      - batch_request:
          datasource_name: my_datasource
          data_connector_name: my_special_data_connector
          data_asset_name: users
          partition_request:
            index: -1
          batch_spec_passthrough:
            path: /totally/not/a/file.csv
            reader_method: read_csv
        expectation_suite_name: bar
        action_list:
            - name: store_validation_result
              action:
                class_name: StoreValidationResultAction
            - name: store_evaluation_params
              action:
                class_name: StoreEvaluationParametersAction
            - name: update_data_docs
              action:
                class_name: UpdateDataDocsAction
        evaluation_parameters:
          param1: "$MY_PARAM"
          param2: 1 + "$OLD_PARAM"
        runtime_configuration:
          result_format:
            result_format: BASIC
            partial_unexpected_count: 20
    """
    config: dict = dict(yaml.load(checkpoint_yaml_config))

    _write_checkpoint_dict_to_file(config, checkpoint_file_path)

    runner: CliRunner = CliRunner(mix_stderr=False)
    result: Result = runner.invoke(
        cli,
        f"checkpoint run bad_batch -d {root_dir}",
        catch_exceptions=False,
    )
    stdout: str = result.stdout
    assert result.exit_code == 1

    # TODO: <Alex>ALEX -- Investigate how to make Abe's suggestion a reality.</Alex>
    # Note: Abe : 2020/09: This was a better error message, but it should live in DataContext.get_batch, not a random CLI method.
    # assert "There was a problem loading a batch:" in stdout
    # assert (
    #     "{'path': '/totally/not/a/file.csv', 'datasource': 'mydatasource', 'reader_method': 'read_csv'}"
    #     in stdout
    # )
    # assert (
    #     "Please verify these batch kwargs in checkpoint bad_batch`"
    #     in stdout
    # )
    # assert "No such file or directory" in stdout
    assert ("No such file or directory" in stdout) or ("does not exist" in stdout)

    assert mock_emit.call_count == 2
    assert mock_emit.call_args_list == [
        mock.call(
            {"event_payload": {}, "event": "data_context.__init__", "success": True}
        ),
        mock.call(
            {"event": "cli.checkpoint.run", "event_payload": {}, "success": False}
        ),
    ]

    assert_no_logging_messages_or_tracebacks(
        my_caplog=caplog,
        click_result=result,
    )

    monkeypatch.delenv("VAR")
    monkeypatch.delenv("MY_PARAM")
    monkeypatch.delenv("OLD_PARAM")


@mock.patch(
    "great_expectations.core.usage_statistics.usage_statistics.UsageStatisticsHandler.emit"
)
def test_checkpoint_run_on_checkpoint_with_empty_suite_list_raises_error_with_ge_config_v3(
    mock_emit,
    caplog,
    titanic_pandas_data_context_with_v013_datasource_with_checkpoints_v1_with_empty_store_stats_enabled,
    monkeypatch,
):
    monkeypatch.setenv("VAR", "test")
    monkeypatch.setenv("MY_PARAM", "1")
    monkeypatch.setenv("OLD_PARAM", "2")

    context: DataContext = titanic_pandas_data_context_with_v013_datasource_with_checkpoints_v1_with_empty_store_stats_enabled
    assert context.list_expectation_suite_names() == []

    root_dir: str = context.root_directory
    print(f"\n[ALEX_TEST] ROOT_DIR: {root_dir}")
    checkpoint_file_path: str = os.path.join(
        context.root_directory,
        DataContextConfigDefaults.CHECKPOINTS_BASE_DIRECTORY.value,
        "no_suite.yml",
    )

    checkpoint_yaml_config: str = f"""
    name: my_base_checkpoint
    config_version: 1
    class_name: Checkpoint
    run_name_template: "%Y-%M-foo-bar-template-$VAR"
    action_list:
    - name: store_validation_result
      action:
        class_name: StoreValidationResultAction
    - name: store_evaluation_params
      action:
        class_name: StoreEvaluationParametersAction
    - name: update_data_docs
      action:
        class_name: UpdateDataDocsAction
    evaluation_parameters:
      param1: "$MY_PARAM"
      param2: 1 + "$OLD_PARAM"
    runtime_configuration:
        result_format:
          result_format: BASIC
          partial_unexpected_count: 20
    """
    config: dict = dict(yaml.load(checkpoint_yaml_config))

    _write_checkpoint_dict_to_file(config, checkpoint_file_path)

    runner: CliRunner = CliRunner(mix_stderr=False)
    result: Result = runner.invoke(
        cli,
        f"checkpoint run no_suite -d {root_dir}",
        catch_exceptions=False,
    )
    stdout: str = result.stdout
    assert result.exit_code == 1

    assert "Checkpoint 'no_suite does not contain any validations." in stdout

    assert mock_emit.call_count == 2
    assert mock_emit.call_args_list == [
        mock.call(
            {"event_payload": {}, "event": "data_context.__init__", "success": True}
        ),
        mock.call(
            {"event": "cli.checkpoint.run", "event_payload": {}, "success": False}
        ),
    ]

    assert_no_logging_messages_or_tracebacks(
        my_caplog=caplog,
        click_result=result,
    )

    monkeypatch.delenv("VAR")
    monkeypatch.delenv("MY_PARAM")
    monkeypatch.delenv("OLD_PARAM")


@mock.patch(
    "great_expectations.core.usage_statistics.usage_statistics.UsageStatisticsHandler.emit"
)
def test_checkpoint_run_on_non_existent_validation_operator_with_ge_config_v2(
    mock_emit, caplog, titanic_data_context_stats_enabled_config_version_2
):
    context: DataContext = titanic_data_context_stats_enabled_config_version_2
    root_dir = context.root_directory
    csv_path = os.path.join(root_dir, "..", "data", "Titanic.csv")

    suite = context.create_expectation_suite("iceberg")
    context.save_expectation_suite(suite)
    assert context.list_expectation_suite_names() == ["iceberg"]
    mock_emit.reset_mock()

    checkpoint_file_path = os.path.join(
        context.root_directory,
        DataContextConfigDefaults.CHECKPOINTS_BASE_DIRECTORY.value,
        "bad_operator.yml",
    )
    bad = {
        "validation_operator_name": "foo",
        "batches": [
            {
                "batch_kwargs": {
                    "path": csv_path,
                    "datasource": "mydatasource",
                    "reader_method": "read_csv",
                },
                "expectation_suite_names": ["iceberg"],
            },
        ],
    }
    _write_checkpoint_dict_to_file(bad, checkpoint_file_path)

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        cli,
        f"checkpoint run bad_operator -d {root_dir}",
        catch_exceptions=False,
    )
    stdout = result.stdout
    assert result.exit_code == 1

    assert (
        f"No validation operator `foo` was found in your project. Please verify this in your great_expectations.yml"
        in stdout
    )
    usage_emits = mock_emit.call_args_list

    assert mock_emit.call_count == 3
    assert usage_emits[0][0][0]["success"] is True
    assert usage_emits[1][0][0]["success"] is False
    assert usage_emits[2][0][0]["success"] is False

    assert_no_logging_messages_or_tracebacks(
        my_caplog=caplog,
        click_result=result,
        allowed_deprecation_message=LEGACY_CONFIG_DEFAULT_CHECKPOINT_STORE_MESSAGE,
    )


@mock.patch(
    "great_expectations.core.usage_statistics.usage_statistics.UsageStatisticsHandler.emit"
)
def test_checkpoint_run_happy_path_with_successful_validation_with_ge_config_v2(
    mock_emit, caplog, titanic_data_context_v2_with_checkpoint_suite_and_stats_enabled
):
    context: DataContext = (
        titanic_data_context_v2_with_checkpoint_suite_and_stats_enabled
    )
    root_dir = context.root_directory
    mock_emit.reset_mock()

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        cli,
        f"checkpoint run my_checkpoint -d {root_dir}",
        catch_exceptions=False,
    )
    stdout = result.stdout
    assert result.exit_code == 0
    assert "Validation succeeded!" in stdout

    assert mock_emit.call_count == 5
    usage_emits = mock_emit.call_args_list
    assert usage_emits[0] == mock.call(
        {"event_payload": {}, "event": "data_context.__init__", "success": True}
    )
    assert usage_emits[1][0][0]["event"] == "data_asset.validate"
    assert usage_emits[1][0][0]["success"] is True

    assert usage_emits[2][0][0]["event"] == "data_context.build_data_docs"
    assert usage_emits[2][0][0]["success"] is True

    assert usage_emits[4] == mock.call(
        {"event": "cli.checkpoint.run", "event_payload": {}, "success": True}
    )

    assert_no_logging_messages_or_tracebacks(
        my_caplog=caplog,
        click_result=result,
        allowed_deprecation_message=LEGACY_CONFIG_DEFAULT_CHECKPOINT_STORE_MESSAGE,
    )


@mock.patch(
    "great_expectations.core.usage_statistics.usage_statistics.UsageStatisticsHandler.emit"
)
def test_checkpoint_run_happy_path_with_failed_validation_with_ge_config_v2(
    mock_emit, caplog, titanic_data_context_v2_with_checkpoint_suite_and_stats_enabled
):
    context: DataContext = (
        titanic_data_context_v2_with_checkpoint_suite_and_stats_enabled
    )
    root_dir = context.root_directory
    # mangle the csv
    csv_path = os.path.join(context.root_directory, "..", "data", "Titanic.csv")
    with open(csv_path, "w") as f:
        f.write("foo,bar\n1,2\n")

    mock_emit.reset_mock()

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        cli,
        f"checkpoint run my_checkpoint -d {root_dir}",
        catch_exceptions=False,
    )
    stdout = result.stdout
    print(stdout)
    assert result.exit_code == 1
    assert "Validation failed!" in stdout

    assert mock_emit.call_count == 5
    usage_emits = mock_emit.call_args_list
    assert usage_emits[0] == mock.call(
        {"event_payload": {}, "event": "data_context.__init__", "success": True}
    )
    assert usage_emits[1][0][0]["event"] == "data_asset.validate"
    assert usage_emits[1][0][0]["success"] is True

    assert usage_emits[2][0][0]["event"] == "data_context.build_data_docs"
    assert usage_emits[2][0][0]["success"] is True

    assert usage_emits[4] == mock.call(
        {"event": "cli.checkpoint.run", "event_payload": {}, "success": True}
    )

    assert_no_logging_messages_or_tracebacks(
        my_caplog=caplog,
        click_result=result,
        allowed_deprecation_message=LEGACY_CONFIG_DEFAULT_CHECKPOINT_STORE_MESSAGE,
    )


@mock.patch(
    "great_expectations.core.usage_statistics.usage_statistics.UsageStatisticsHandler.emit"
)
def test_checkpoint_script_raises_error_if_checkpoint_not_found_with_ge_config_v2(
    mock_emit, caplog, titanic_data_context_v2_with_checkpoint_suite_and_stats_enabled
):
    context: DataContext = (
        titanic_data_context_v2_with_checkpoint_suite_and_stats_enabled
    )
    root_dir = context.root_directory
    assert context.list_checkpoints() == ["my_checkpoint"]
    mock_emit.reset_mock()

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        cli,
        f"checkpoint script not_a_checkpoint -d {root_dir}",
        catch_exceptions=False,
    )
    stdout = result.stdout
    assert "Could not find checkpoint `not_a_checkpoint`." in stdout
    assert "Try running" in stdout
    assert result.exit_code == 1

    assert mock_emit.call_count == 2
    assert mock_emit.call_args_list == [
        mock.call(
            {"event_payload": {}, "event": "data_context.__init__", "success": True}
        ),
        mock.call(
            {"event": "cli.checkpoint.script", "event_payload": {}, "success": False}
        ),
    ]

    assert_no_logging_messages_or_tracebacks(
        my_caplog=caplog,
        click_result=result,
        allowed_deprecation_message=LEGACY_CONFIG_DEFAULT_CHECKPOINT_STORE_MESSAGE,
    )


@mock.patch(
    "great_expectations.core.usage_statistics.usage_statistics.UsageStatisticsHandler.emit"
)
def test_checkpoint_script_raises_error_if_python_file_exists_with_ge_config_v2(
    mock_emit, caplog, titanic_data_context_v2_with_checkpoint_suite_and_stats_enabled
):
    context: DataContext = (
        titanic_data_context_v2_with_checkpoint_suite_and_stats_enabled
    )
    root_dir = context.root_directory
    assert context.list_checkpoints() == ["my_checkpoint"]
    script_path = os.path.join(
        root_dir, context.GE_UNCOMMITTED_DIR, "run_my_checkpoint.py"
    )
    with open(script_path, "w") as f:
        f.write("script here")
    assert os.path.isfile(script_path)
    mock_emit.reset_mock()

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        cli,
        f"checkpoint script my_checkpoint -d {root_dir}",
        catch_exceptions=False,
    )
    stdout = result.stdout
    assert (
        "Warning! A script named run_my_checkpoint.py already exists and this command will not overwrite it."
        in stdout
    )
    assert result.exit_code == 1

    assert mock_emit.call_count == 2
    assert mock_emit.call_args_list == [
        mock.call(
            {"event_payload": {}, "event": "data_context.__init__", "success": True}
        ),
        mock.call(
            {"event": "cli.checkpoint.script", "event_payload": {}, "success": False}
        ),
    ]

    # assert the script has original contents
    with open(script_path) as f:
        assert f.read() == "script here"

    assert_no_logging_messages_or_tracebacks(
        my_caplog=caplog,
        click_result=result,
        allowed_deprecation_message=LEGACY_CONFIG_DEFAULT_CHECKPOINT_STORE_MESSAGE,
    )


@mock.patch(
    "great_expectations.core.usage_statistics.usage_statistics.UsageStatisticsHandler.emit"
)
def test_checkpoint_script_happy_path_generates_script_with_ge_config_v2(
    mock_emit, caplog, titanic_data_context_v2_with_checkpoint_suite_and_stats_enabled
):
    context: DataContext = (
        titanic_data_context_v2_with_checkpoint_suite_and_stats_enabled
    )
    root_dir = context.root_directory
    mock_emit.reset_mock()

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        cli,
        f"checkpoint script my_checkpoint -d {root_dir}",
        catch_exceptions=False,
    )
    stdout = result.stdout
    assert result.exit_code == 0
    assert (
        "A python script was created that runs the checkpoint named: `my_checkpoint`"
        in stdout
    )
    assert (
        "The script is located in `great_expectations/uncommitted/run_my_checkpoint.py`"
        in stdout
    )
    assert (
        "The script can be run with `python great_expectations/uncommitted/run_my_checkpoint.py`"
        in stdout
    )

    assert mock_emit.call_count == 2
    assert mock_emit.call_args_list == [
        mock.call(
            {"event_payload": {}, "event": "data_context.__init__", "success": True}
        ),
        mock.call(
            {"event": "cli.checkpoint.script", "event_payload": {}, "success": True}
        ),
    ]
    expected_script = os.path.join(
        root_dir, context.GE_UNCOMMITTED_DIR, "run_my_checkpoint.py"
    )
    assert os.path.isfile(expected_script)

    assert_no_logging_messages_or_tracebacks(
        my_caplog=caplog,
        click_result=result,
        allowed_deprecation_message=LEGACY_CONFIG_DEFAULT_CHECKPOINT_STORE_MESSAGE,
    )


def test_checkpoint_script_happy_path_executable_successful_validation_with_ge_config_v2(
    caplog, titanic_data_context_v2_with_checkpoint_suite_and_stats_enabled
):
    """
    We call the "checkpoint script" command on a project with a checkpoint.

    The command should:
    - create the script (note output is tested in other tests)

    When run the script should:
    - execute
    - return a 0 status code
    - print a success message
    """
    context: DataContext = (
        titanic_data_context_v2_with_checkpoint_suite_and_stats_enabled
    )
    root_dir = context.root_directory
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        cli,
        f"checkpoint script my_checkpoint -d {root_dir}",
        catch_exceptions=False,
    )
    stdout = result.stdout
    assert result.exit_code == 0
    assert_no_logging_messages_or_tracebacks(
        my_caplog=caplog,
        click_result=result,
        allowed_deprecation_message=LEGACY_CONFIG_DEFAULT_CHECKPOINT_STORE_MESSAGE,
    )

    script_path = os.path.abspath(
        os.path.join(root_dir, context.GE_UNCOMMITTED_DIR, "run_my_checkpoint.py")
    )
    assert os.path.isfile(script_path)

    # In travis on osx, python may not execute from the build dir
    cmdstring = f"python {script_path}"
    if os.environ.get("TRAVIS_OS_NAME") == "osx":
        build_dir = os.environ.get("TRAVIS_BUILD_DIR")
        print(os.listdir(build_dir))
        cmdstring = f"python3 {script_path}"
    print("about to run: " + cmdstring)
    print(os.curdir)
    print(os.listdir(os.curdir))
    print(os.listdir(os.path.abspath(os.path.join(root_dir, ".."))))

    status, output = subprocess.getstatusoutput(cmdstring)
    print(f"\n\nScript exited with code: {status} and output:\n{output}")

    assert status == 0
    assert "Validation succeeded!" in output


def test_checkpoint_script_happy_path_executable_failed_validation_with_ge_config_v2(
    caplog, titanic_data_context_v2_with_checkpoint_suite_and_stats_enabled
):
    """
    We call the "checkpoint script" command on a project with a checkpoint.

    The command should:
    - create the script (note output is tested in other tests)

    When run the script should:
    - execute
    - return a 1 status code
    - print a failure message
    """
    context: DataContext = (
        titanic_data_context_v2_with_checkpoint_suite_and_stats_enabled
    )
    root_dir = context.root_directory
    # mangle the csv
    csv_path = os.path.join(context.root_directory, "..", "data", "Titanic.csv")
    with open(csv_path, "w") as f:
        f.write("foo,bar\n1,2\n")

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        cli,
        f"checkpoint script my_checkpoint -d {root_dir}",
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert_no_logging_messages_or_tracebacks(
        my_caplog=caplog,
        click_result=result,
        allowed_deprecation_message=LEGACY_CONFIG_DEFAULT_CHECKPOINT_STORE_MESSAGE,
    )

    script_path = os.path.abspath(
        os.path.join(root_dir, context.GE_UNCOMMITTED_DIR, "run_my_checkpoint.py")
    )
    assert os.path.isfile(script_path)

    # In travis on osx, python may not execute from the build dir
    cmdstring = f"python {script_path}"
    if os.environ.get("TRAVIS_OS_NAME") == "osx":
        build_dir = os.environ.get("TRAVIS_BUILD_DIR")
        print(os.listdir(build_dir))
        cmdstring = f"python3 {script_path}"
    print("about to run: " + cmdstring)
    print(os.curdir)
    print(os.listdir(os.curdir))
    print(os.listdir(os.path.abspath(os.path.join(root_dir, ".."))))

    status, output = subprocess.getstatusoutput(cmdstring)
    print(f"\n\nScript exited with code: {status} and output:\n{output}")
    assert status == 1
    assert "Validation failed!" in output


@mock.patch(
    "great_expectations.core.usage_statistics.usage_statistics.UsageStatisticsHandler.emit"
)
def test_checkpoint_new_with_ge_config_3_raises_error(
    mock_emit, caplog, titanic_data_context_stats_enabled
):
    context: DataContext = titanic_data_context_stats_enabled
    root_dir = context.root_directory
    mock_emit.reset_mock()

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        cli,
        f"checkpoint new foo not_a_suite -d {root_dir}",
        catch_exceptions=False,
    )
    stdout = result.stdout
    assert result.exit_code == 1
    assert (
        "The `checkpoint new` CLI command is not yet implemented for GE config versions >= 3."
        in stdout
    )

    assert mock_emit.call_count == 2
    assert mock_emit.call_args_list == [
        mock.call(
            {"event_payload": {}, "event": "data_context.__init__", "success": True}
        ),
        mock.call(
            {"event": "cli.checkpoint.new", "event_payload": {}, "success": False}
        ),
    ]

    assert_no_logging_messages_or_tracebacks(
        my_caplog=caplog,
        click_result=result,
        allowed_deprecation_message=VALIDATION_OPERATORS_DEPRECATION_MESSAGE,
    )


@mock.patch(
    "great_expectations.core.usage_statistics.usage_statistics.UsageStatisticsHandler.emit"
)
def test_checkpoint_script_with_ge_config_3_raises_error(
    mock_emit, caplog, titanic_data_context_stats_enabled
):
    context: DataContext = titanic_data_context_stats_enabled
    root_dir = context.root_directory
    mock_emit.reset_mock()

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        cli,
        f"checkpoint script my_checkpoint -d {root_dir}",
        catch_exceptions=False,
    )
    stdout = result.stdout
    assert result.exit_code == 1
    assert (
        "The `checkpoint script` CLI command is not yet implemented for GE config versions >= 3."
        in stdout
    )

    assert mock_emit.call_count == 2
    assert mock_emit.call_args_list == [
        mock.call(
            {"event_payload": {}, "event": "data_context.__init__", "success": True}
        ),
        mock.call(
            {"event": "cli.checkpoint.script", "event_payload": {}, "success": False}
        ),
    ]

    assert_no_logging_messages_or_tracebacks(
        my_caplog=caplog,
        click_result=result,
        allowed_deprecation_message=VALIDATION_OPERATORS_DEPRECATION_MESSAGE,
    )


def _write_checkpoint_dict_to_file(bad, checkpoint_file_path):
    yaml = YAML()
    with open(checkpoint_file_path, "w") as f:
        yaml.dump(bad, f)
