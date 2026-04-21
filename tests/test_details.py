"""Tests for job list table utilities in details.py."""

import pytest
from cloudos_cli.utils.details import (
    _fit_columns_to_terminal,
    _calculate_table_width,
    _build_job_row_values
)
from cloudos_cli.constants import (
    JOB_STATUS_SYMBOLS,
    COLUMN_CONFIGS
)


class TestFitColumnsToTerminal:
    """Test cases for _fit_columns_to_terminal function."""
    
    def test_preserve_order_all_columns_fit(self):
        """Test that user-specified order is preserved when all columns fit."""
        cols = ['cost', 'run_time', 'name']
        terminal_w = 100  # Wide enough for all columns
        
        result = _fit_columns_to_terminal(cols, terminal_w, COLUMN_CONFIGS, preserve_order=True)
        
        assert result == ['cost', 'run_time', 'name']
        assert len(result) == 3
    
    def test_preserve_order_some_columns_dropped(self):
        """Test that columns are dropped in order when terminal is narrow."""
        cols = ['id', 'name', 'project', 'pipeline']
        terminal_w = 50  # Narrow terminal
        
        result = _fit_columns_to_terminal(cols, terminal_w, COLUMN_CONFIGS, preserve_order=True)
        
        # Should include columns in order until width is exceeded
        assert len(result) >= 1  # At least one column
        assert result[0] == 'id'  # First column preserved
        assert len(result) < len(cols)  # Some columns dropped
    
    def test_preserve_order_empty_list(self):
        """Test that empty list returns empty list."""
        result = _fit_columns_to_terminal([], 100, COLUMN_CONFIGS, preserve_order=True)
        
        assert result == []
    
    def test_preserve_order_very_narrow_terminal(self):
        """Test that at least one column is shown even on very narrow terminal."""
        cols = ['id', 'name']
        terminal_w = 10  # Too narrow for anything
        
        result = _fit_columns_to_terminal(cols, terminal_w, COLUMN_CONFIGS, preserve_order=True)
        
        assert len(result) == 1
        assert result[0] == 'name'  # Narrowest requested column chosen as fallback
    
    def test_auto_selection_reorders_by_priority(self):
        """Test that auto-selection reorders columns by priority."""
        cols = ['cost', 'status', 'pipeline', 'name', 'id']
        terminal_w = 100  # Wide enough
        
        result = _fit_columns_to_terminal(cols, terminal_w, COLUMN_CONFIGS, preserve_order=False)
        
        # Should reorder: status, id, name, pipeline are essential and come first
        assert result[0] == 'status'
        assert 'id' in result
        assert 'name' in result
    
    def test_auto_selection_skips_wide_columns(self):
        """Test that auto-selection can skip wide columns to fit narrower ones."""
        cols = ['status', 'id', 'name', 'pipeline']
        terminal_w = 35  # Narrow - id is 24 chars, won't fit with others
        
        result = _fit_columns_to_terminal(cols, terminal_w, COLUMN_CONFIGS, preserve_order=False)
        
        # Should include status (narrow) and possibly name, but might skip id
        assert 'status' in result
        assert len(result) >= 1
    
    def test_auto_selection_fills_terminal_optimally(self):
        """Test that auto-selection maximizes columns within width."""
        cols = ['status', 'name', 'project', 'pipeline', 'owner']
        terminal_w = 80
        
        result = _fit_columns_to_terminal(cols, terminal_w, COLUMN_CONFIGS, preserve_order=False)
        
        # Should fit multiple columns
        assert len(result) >= 2
        # Width should not exceed terminal
        actual_width = _calculate_table_width(result, COLUMN_CONFIGS)
        assert actual_width <= terminal_w
    
    def test_auto_selection_always_shows_status_minimum(self):
        """Test that auto-selection always shows at least status on narrow terminal."""
        cols = ['status', 'id', 'name']
        terminal_w = 10  # Too narrow for anything
        
        result = _fit_columns_to_terminal(cols, terminal_w, COLUMN_CONFIGS, preserve_order=False)
        
        assert len(result) >= 1
        assert 'status' in result


class TestCalculateTableWidth:
    """Test cases for _calculate_table_width function."""
    
    def test_single_column(self):
        """Test width calculation for single column."""
        columns = ['status']
        width = _calculate_table_width(columns, COLUMN_CONFIGS)
        
        # borders_and_separators = 2 + (1-1) = 2
        # column_widths = (6 + 2) = 8
        # buffer = 2
        # Total: 2 + 8 + 2 = 12
        assert width == 12
    
    def test_multiple_columns(self):
        """Test width calculation for multiple columns."""
        columns = ['status', 'name']
        width = _calculate_table_width(columns, COLUMN_CONFIGS)
        
        # borders_and_separators = 2 + (2-1) = 3
        # column_widths = (6+2) + (14+2) = 24
        # buffer = 2
        # Total: 3 + 24 + 2 = 29
        assert width == 29
    
    def test_empty_column_list(self):
        """Test width calculation for empty column list."""
        columns = []
        width = _calculate_table_width(columns, COLUMN_CONFIGS)
        
        # borders_and_separators = 2 + (0-1) = 1
        # column_widths = 0
        # buffer = 2
        # Total: 1 + 0 + 2 = 3
        assert width == 3


class TestBuildJobRowValues:
    """Test cases for _build_job_row_values function."""
    
    def test_status_symbols_all_types(self):
        """Test that all status types map to correct symbols."""
        status_tests = [
            ('completed', '✓'),
            ('running', '◐'),
            ('failed', '✗'),
            ('aborted', '■'),
            ('aborting', '⊡'),
            ('initialising', '○'),
            ('scheduled', '◷'),
        ]
        
        for status_value, expected_symbol in status_tests:
            job = {
                '_id': 'test-id',
                'name': 'test-job',
                'status': status_value,
                'project': {'name': 'test'},
                'user': {'name': 'User', 'surname': 'Name'},
                'workflow': {'name': 'pipeline'},
                'createdAt': '2026-04-16T07:16:30Z',
                'revision': {'commit': 'abc'},
                'masterInstance': {'usedInstance': {'type': 't3.small'}},
                'storageMode': 'regular',
                'jobType': 'nextflow'
            }
            
            row_values = _build_job_row_values(
                job, 
                'https://cloudos.lifebit.ai', 
                80, 
                ['status']
            )
            
            assert expected_symbol in row_values[0], f"Status '{status_value}' should contain symbol '{expected_symbol}'"
    
    def test_status_missing_shows_unknown(self):
        """Test that missing status field shows unknown symbol."""
        job = {
            '_id': 'test-id',
            'name': 'test-job',
            # NO status field
            'project': {'name': 'test'},
            'user': {'name': 'User', 'surname': 'Name'},
            'workflow': {'name': 'pipeline'},
            'createdAt': '2026-04-16T07:16:30Z',
            'revision': {'commit': 'abc'},
            'masterInstance': {'usedInstance': {'type': 't3.small'}},
            'storageMode': 'regular',
            'jobType': 'nextflow'
        }
        
        row_values = _build_job_row_values(
            job, 
            'https://cloudos.lifebit.ai', 
            80, 
            ['status']
        )
        
        assert '?' in row_values[0], "Missing status should show '?' symbol"
    
    def test_multiple_columns_correct_order(self):
        """Test that multiple columns are returned in correct order."""
        job = {
            '_id': 'test-id-123',
            'name': 'my-job',
            'status': 'completed',
            'project': {'name': 'my-project'},
            'user': {'name': 'John', 'surname': 'Doe'},
            'workflow': {'name': 'my-pipeline'},
            'createdAt': '2026-04-16T07:16:30Z',
            'revision': {'commit': 'abc123'},
            'masterInstance': {'usedInstance': {'type': 't3.small'}},
            'storageMode': 'regular',
            'jobType': 'nextflow'
        }
        
        columns = ['status', 'name', 'project']
        row_values = _build_job_row_values(
            job, 
            'https://cloudos.lifebit.ai', 
            80, 
            columns
        )
        
        assert len(row_values) == 3
        # Status should contain symbol
        assert '✓' in row_values[0]
        # Name should match
        assert 'my-job' in row_values[1]
        # Project should match
        assert 'my-project' in row_values[2]
    
    def test_owner_formatting(self):
        """Test that owner is formatted correctly."""
        job = {
            '_id': 'test-id',
            'name': 'test-job',
            'status': 'completed',
            'project': {'name': 'test'},
            'user': {'name': 'John', 'surname': 'Doe'},
            'workflow': {'name': 'pipeline'},
            'createdAt': '2026-04-16T07:16:30Z',
            'revision': {'commit': 'abc'},
            'masterInstance': {'usedInstance': {'type': 't3.small'}},
            'storageMode': 'regular',
            'jobType': 'nextflow'
        }
        
        row_values = _build_job_row_values(
            job, 
            'https://cloudos.lifebit.ai', 
            80, 
            ['owner']
        )
        
        assert row_values[0] == 'John Doe'
    
    def test_job_id_has_hyperlink(self):
        """Test that job ID includes hyperlink markup."""
        job = {
            '_id': 'test-id-123',
            'name': 'test-job',
            'status': 'completed',
            'project': {'name': 'test'},
            'user': {'name': 'User', 'surname': 'Name'},
            'workflow': {'name': 'pipeline'},
            'createdAt': '2026-04-16T07:16:30Z',
            'revision': {'commit': 'abc'},
            'masterInstance': {'usedInstance': {'type': 't3.small'}},
            'storageMode': 'regular',
            'jobType': 'nextflow'
        }
        
        row_values = _build_job_row_values(
            job, 
            'https://cloudos.lifebit.ai', 
            80, 
            ['id']
        )
        
        # Should contain both the ID and link markup
        assert 'test-id-123' in row_values[0]
        assert '[link=' in row_values[0]
        assert 'cloudos.lifebit.ai' in row_values[0]


class TestColumnValidation:
    """Test cases for column validation in create_job_list_table."""
    
    def test_duplicate_columns_are_deduplicated(self):
        """Test that duplicate column names are automatically deduplicated."""
        from cloudos_cli.utils.details import create_job_list_table
        import io
        import sys
        
        # Create a test job
        job = {
            '_id': 'test-id',
            'name': 'test-job',
            'status': 'completed',
            'project': {'name': 'test'},
            'user': {'name': 'User', 'surname': 'Name'},
            'workflow': {'name': 'pipeline'},
            'createdAt': '2026-04-16T07:16:30Z',
            'startTime': '2026-04-16T07:16:45Z',
            'endTime': '2026-04-16T07:20:51Z',
            'revision': {'commit': 'abc'},
            'computeCostSpent': 2700,
            'masterInstance': {'usedInstance': {'type': 't3.small'}},
            'storageMode': 'regular',
            'jobType': 'nextflow'
        }
        
        pagination_metadata = {
            'Pagination-Count': 1,
            'Pagination-Page': 1,
            'Pagination-Limit': 10
        }
        
        # Capture output
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        try:
            # Test with duplicate columns
            create_job_list_table(
                [job],
                'https://cloudos.lifebit.ai',
                pagination_metadata,
                selected_columns='status,name,status'  # 'status' appears twice
            )
            
            output = captured_output.getvalue()
            
            # Should show warning about duplicates
            assert 'Warning: Duplicate columns removed' in output or 'Duplicate' in output
            
            # Should only show 2 columns in the table (status and name, not status twice)
            # Count occurrences of "Status" header - should be 1, not 2
            # Note: This is a basic check; full validation would require parsing Rich output
            
        finally:
            sys.stdout = sys.__stdout__
    
    def test_no_warning_when_no_duplicates(self):
        """Test that no warning is shown when there are no duplicate columns."""
        from cloudos_cli.utils.details import create_job_list_table
        import io
        import sys
        
        job = {
            '_id': 'test-id',
            'name': 'test-job',
            'status': 'completed',
            'project': {'name': 'test'},
            'user': {'name': 'User', 'surname': 'Name'},
            'workflow': {'name': 'pipeline'},
            'createdAt': '2026-04-16T07:16:30Z',
            'revision': {'commit': 'abc'},
            'masterInstance': {'usedInstance': {'type': 't3.small'}},
            'storageMode': 'regular',
            'jobType': 'nextflow'
        }
        
        pagination_metadata = {
            'Pagination-Count': 1,
            'Pagination-Page': 1,
            'Pagination-Limit': 10
        }
        
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        try:
            # Test with no duplicates
            create_job_list_table(
                [job],
                'https://cloudos.lifebit.ai',
                pagination_metadata,
                selected_columns='status,name,cost'  # All unique
            )
            
            output = captured_output.getvalue()
            
            # Should NOT show duplicate warning
            assert 'Duplicate columns removed' not in output
            
        finally:
            sys.stdout = sys.__stdout__


class TestBugFixes:
    
    def test_bug8_date_format_uses_actual_terminal_width(self):
        """
        Bug #8: Date format regression with effective_width.
        
        Issue: effective_width = terminal_width - 5 was passed to date formatting,
        causing terminals with 90-94 chars to show short dates (no year).
        
        Fix: Pass actual terminal_width (not effective_width) to _build_job_row_values.
        """
        job = {
            '_id': 'test-id',
            'name': 'test-job',
            'status': 'completed',
            'project': {'name': 'test'},
            'user': {'name': 'User', 'surname': 'Name'},
            'workflow': {'name': 'pipeline'},
            'createdAt': '2026-04-16T07:16:30Z',
            'startTime': '2026-04-16T07:16:45Z',
            'endTime': '2026-04-16T07:20:51Z',
            'revision': {'commit': 'abc'},
            'masterInstance': {'usedInstance': {'type': 't3.small'}},
            'storageMode': 'regular',
            'jobType': 'nextflow'
        }
        
        # Terminal width 92 should show FULL dates with year (not short format)
        row_values = _build_job_row_values(
            job, 
            'https://cloudos.lifebit.ai', 
            92,  # Pass actual terminal width
            ['submit_time', 'end_time']
        )
        
        # Should show full date format with year (YYYY-mm-dd HH:MM)
        assert '2026' in row_values[0], "Submit time should include year for 92-char terminal"
        assert '2026' in row_values[1], "End time should include year for 92-char terminal"
        
        # Terminal width 89 should show SHORT dates (no year)
        row_values = _build_job_row_values(
            job, 
            'https://cloudos.lifebit.ai', 
            89,
            ['submit_time', 'end_time']
        )
        
        # Should show short date format (mm-dd HH:MM)
        assert '2026' not in row_values[0], "Submit time should NOT include year for 89-char terminal"
        assert '2026' not in row_values[1], "End time should NOT include year for 89-char terminal"
    
    def test_bug9_truncation_warning_uses_original_column_count(self):
        """
        Bug #9: Misleading truncation warning after deduplication.
        
        Issue: When user requests duplicate columns (e.g., 'status,name,status,id,owner'),
        deduplication happens first, then the truncation warning uses the deduplicated
        count instead of the original request count, confusing users.
        
        Fix: Store original_column_count before deduplication and use it in warning.
        """
        from cloudos_cli.utils.details import create_job_list_table
        import io
        import sys
        
        job = {
            '_id': 'test-id',
            'name': 'test-job',
            'status': 'completed',
            'project': {'name': 'test'},
            'user': {'name': 'User', 'surname': 'Name'},
            'workflow': {'name': 'pipeline'},
            'createdAt': '2026-04-16T07:16:30Z',
            'startTime': '2026-04-16T07:16:45Z',
            'endTime': '2026-04-16T07:20:51Z',
            'revision': {'commit': 'abc'},
            'masterInstance': {'usedInstance': {'type': 't3.small'}},
            'storageMode': 'regular',
            'jobType': 'nextflow'
        }
        
        pagination_metadata = {
            'Pagination-Count': 1,
            'Pagination-Page': 1,
            'Pagination-Limit': 10
        }
        
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        try:
            # Mock narrow terminal (40 chars)
            import os
            original_fn = os.get_terminal_size
            with unittest.mock.patch('os.get_terminal_size', return_value=os.terminal_size((40, 24))):
                create_job_list_table(
                    [job],
                    'https://cloudos.lifebit.ai',
                    pagination_metadata,
                    selected_columns='status,name,status,id,owner'  # 5 columns, 1 duplicate
                )
            
            output = captured_output.getvalue()
            
            # Should show original count (5), not deduplicated count (4)
            assert 'of 5' in output, "Warning should show original count (5) not deduplicated (4)"
            assert 'of 4' not in output, "Warning should NOT show deduplicated count"
            
        finally:
            sys.stdout = sys.__stdout__
