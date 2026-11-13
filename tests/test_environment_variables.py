"""Tests for Nextflow runtime environment variable parsing and validation."""

import pytest
from cloudos_cli.utils.environment_variables import (
    parse_environment_variables,
    merge_environment_variables,
    validate_environment_variables
)

SYNTAX_PARSER_V2 = [{'name': 'NXF_SYNTAX_PARSER', 'value': 'v2'}]


class TestParseEnvironmentVariables:
    """Tests for parse_environment_variables."""

    def test_empty_input_returns_empty_list(self):
        assert parse_environment_variables(()) == []
        assert parse_environment_variables(None) == []

    def test_parses_name_value_pairs(self):
        assert parse_environment_variables(('NXF_SYNTAX_PARSER=v2',)) == SYNTAX_PARSER_V2

    def test_single_string_is_one_variable(self):
        assert parse_environment_variables('NXF_SYNTAX_PARSER=v2') == SYNTAX_PARSER_V2

    def test_value_can_contain_equals(self):
        assert parse_environment_variables(('NAME=a=b',)) == [{'name': 'NAME', 'value': 'a=b'}]

    def test_strips_whitespace(self):
        assert parse_environment_variables((' NXF_SYNTAX_PARSER = v2 ',)) == SYNTAX_PARSER_V2

    @pytest.mark.parametrize('env_var', ['NXF_SYNTAX_PARSER', 'NXF_SYNTAX_PARSER=', '=v2', ''])
    def test_malformed_variable_raises(self, env_var):
        with pytest.raises(ValueError, match='Use the form NAME=VALUE'):
            parse_environment_variables((env_var,))

    def test_duplicate_name_raises(self):
        with pytest.raises(ValueError, match='provided more than once'):
            parse_environment_variables(('NXF_SYNTAX_PARSER=v1', 'NXF_SYNTAX_PARSER=v2'))

    def test_more_than_maximum_raises(self):
        env_vars = tuple(f'VAR_{i}=x' for i in range(21))
        with pytest.raises(ValueError, match='The maximum is 20'):
            parse_environment_variables(env_vars)


class TestMergeEnvironmentVariables:
    """Tests for merge_environment_variables."""

    def test_override_replaces_same_name(self):
        original = [{'name': 'NXF_SYNTAX_PARSER', 'value': 'v1'}]
        assert merge_environment_variables(original, SYNTAX_PARSER_V2) == SYNTAX_PARSER_V2

    def test_new_name_is_added(self):
        original = [{'name': 'OTHER', 'value': 'x'}]
        assert merge_environment_variables(original, SYNTAX_PARSER_V2) == original + SYNTAX_PARSER_V2

    def test_no_overrides_keeps_original(self):
        assert merge_environment_variables(SYNTAX_PARSER_V2, []) == SYNTAX_PARSER_V2

    def test_no_original(self):
        assert merge_environment_variables(None, SYNTAX_PARSER_V2) == SYNTAX_PARSER_V2

    def test_does_not_modify_original(self):
        original = [{'name': 'NXF_SYNTAX_PARSER', 'value': 'v1'}]
        merge_environment_variables(original, SYNTAX_PARSER_V2)
        assert original == [{'name': 'NXF_SYNTAX_PARSER', 'value': 'v1'}]


class TestValidateEnvironmentVariables:
    """Tests for validate_environment_variables."""

    @pytest.mark.parametrize('version', ['25.04.8', '25.10.4', 'latest'])
    @pytest.mark.parametrize('value', ['v1', 'v2'])
    def test_supported_version_and_value(self, version, value):
        validate_environment_variables([{'name': 'NXF_SYNTAX_PARSER', 'value': value}], version)

    def test_no_variables_skips_all_checks(self):
        validate_environment_variables([], '22.10.8', workflow_type='docker')

    def test_unsupported_name_raises(self):
        with pytest.raises(ValueError, match="'NXF_OTHER' is not supported. Supported environment "
                                             "variables: NXF_SYNTAX_PARSER"):
            validate_environment_variables([{'name': 'NXF_OTHER', 'value': 'v2'}], '25.10.4')

    def test_invalid_value_lists_allowed_values(self):
        with pytest.raises(ValueError, match="Invalid value 'v3'.*Allowed values: v1, v2"):
            validate_environment_variables([{'name': 'NXF_SYNTAX_PARSER', 'value': 'v3'}], '25.10.4')

    @pytest.mark.parametrize('version', ['22.10.8', '24.04.4'])
    def test_old_version_raises_with_supported_versions(self, version):
        with pytest.raises(ValueError, match=f'requires Nextflow 25.04.0 or later, but the job uses '
                                             f'Nextflow {version}. Use one of these Nextflow versions: '
                                             '25.04.8, 25.10.4'):
            validate_environment_variables(SYNTAX_PARSER_V2, version)

    def test_version_note_is_included(self):
        with pytest.raises(ValueError, match='24.04.4. It is the default. Use one of'):
            validate_environment_variables(SYNTAX_PARSER_V2, '24.04.4', version_note='It is the default.')

    def test_azure_explains_platform_limit(self):
        with pytest.raises(ValueError, match="azure execution platform only supports Nextflow 22.11.1-edge"):
            validate_environment_variables(SYNTAX_PARSER_V2, '22.11.1-edge', execution_platform='azure')

    def test_azure_latest_resolves_to_azure_version(self):
        with pytest.raises(ValueError, match='uses Nextflow 22.11.1-edge'):
            validate_environment_variables(SYNTAX_PARSER_V2, 'latest', execution_platform='azure')

    def test_hpc_explains_platform_limit(self):
        with pytest.raises(ValueError, match="hpc execution platform only supports Nextflow 22.10.8"):
            validate_environment_variables(SYNTAX_PARSER_V2, '22.10.8', execution_platform='hpc')

    def test_unparsable_version_raises(self):
        with pytest.raises(ValueError, match='requires Nextflow 25.04.0 or later'):
            validate_environment_variables(SYNTAX_PARSER_V2, None)

    @pytest.mark.parametrize('workflow_type', ['wdl', 'docker'])
    def test_non_nextflow_workflow_raises(self, workflow_type):
        with pytest.raises(ValueError, match='only supported for Nextflow workflows'):
            validate_environment_variables(SYNTAX_PARSER_V2, '25.10.4', workflow_type=workflow_type)
