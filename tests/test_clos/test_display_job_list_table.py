import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock, call
from cloudos_cli.clos import Cloudos


class TestDisplayJobListTable:
    """Test cases for the display_job_list_table static method."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.sample_data = [
            {
                'status': 'completed',
                'name': 'RNA-seq Analysis',
                'project.name': 'Cancer Research',
                'user.name': 'Alice'
            },
            {
                'status': 'running',
                'name': 'Variant Calling',
                'project.name': 'Genomics Lab',
                'user.name': 'Bob'
            },
            {
                'status': 'failed',
                'name': 'ChIP-seq Pipeline',
                'project.name': 'Epigenomics',
                'user.name': 'Carol'
            }
        ]
        self.sample_df = pd.DataFrame(self.sample_data)

    @patch('cloudos_cli.clos.Console')
    @patch('cloudos_cli.clos.Table')
    def test_function_calls_console_and_table(self, mock_table_class, mock_console_class):
        """Test that the function calls Console and Table correctly."""
        mock_console = MagicMock()
        mock_table = MagicMock()
        mock_console_class.return_value = mock_console
        mock_table_class.return_value = mock_table
        
        # Call the function
        Cloudos.display_job_list_table(self.sample_df)
        
        # Verify Console was created
        mock_console_class.assert_called_once()
        
        # Verify Table was created
        mock_table_class.assert_called_once_with(title="CloudOS Jobs List", show_lines=True)
        
        # Verify console.print was called with the table
        mock_console.print.assert_called_once_with(mock_table)

    @patch('cloudos_cli.clos.Console')
    @patch('cloudos_cli.clos.Table')
    def test_columns_are_added_correctly(self, mock_table_class, mock_console_class):
        """Test that columns are added correctly with proper styling."""
        mock_console = MagicMock()
        mock_table = MagicMock()
        mock_console_class.return_value = mock_console
        mock_table_class.return_value = mock_table
        
        Cloudos.display_job_list_table(self.sample_df)
        
        # Check that add_column was called for each column
        assert mock_table.add_column.call_count == len(self.sample_df.columns)
        
        # Check column styling
        for call_args in mock_table.add_column.call_args_list:
            args, kwargs = call_args
            assert kwargs.get('style') == 'cyan'
            assert kwargs.get('no_wrap') == False
            assert kwargs.get('overflow') == 'fold'

    @patch('cloudos_cli.clos.Console')
    @patch('cloudos_cli.clos.Table')
    def test_rows_are_added_correctly(self, mock_table_class, mock_console_class):
        """Test that rows are added correctly."""
        mock_console = MagicMock()
        mock_table = MagicMock()
        mock_console_class.return_value = mock_console
        mock_table_class.return_value = mock_table
        
        Cloudos.display_job_list_table(self.sample_df)
        
        # Check that add_row was called for each row
        assert mock_table.add_row.call_count == len(self.sample_df)

    @patch('cloudos_cli.clos.Console')
    @patch('cloudos_cli.clos.Table')
    def test_status_color_coding(self, mock_table_class, mock_console_class):
        """Test that status values are colored correctly."""
        mock_console = MagicMock()
        mock_table = MagicMock()
        mock_console_class.return_value = mock_console
        mock_table_class.return_value = mock_table
        
        Cloudos.display_job_list_table(self.sample_df)
        
        # Get all row calls
        row_calls = mock_table.add_row.call_args_list
        
        # Check status colors
        for i, call_args in enumerate(row_calls):
            args, kwargs = call_args
            status = self.sample_df.iloc[i]['status']
            status_arg = args[0]  # First argument should be the status
            
            if status == 'completed':
                assert '[green]completed[/green]' == status_arg
            elif status == 'running':
                assert '[blue]running[/blue]' == status_arg
            elif status == 'failed':
                assert '[red]failed[/red]' == status_arg

    @patch('cloudos_cli.clos.Console')
    @patch('cloudos_cli.clos.Table')
    def test_non_status_values_are_magenta(self, mock_table_class, mock_console_class):
        """Test that non-status values are colored magenta."""
        mock_console = MagicMock()
        mock_table = MagicMock()
        mock_console_class.return_value = mock_console
        mock_table_class.return_value = mock_table
        
        Cloudos.display_job_list_table(self.sample_df)
        
        # Check first row non-status values
        first_row_call = mock_table.add_row.call_args_list[0]
        args, kwargs = first_row_call
        
        # Skip status (first column), check others are magenta
        for value in args[1:]:
            assert value.startswith('[magenta]')
            assert value.endswith('[/magenta]')

    @patch('cloudos_cli.clos.Console')
    @patch('cloudos_cli.clos.Table')
    def test_handles_nan_values(self, mock_table_class, mock_console_class):
        """Test that NaN and None values are handled correctly."""
        # Create DataFrame with NaN/None values
        data_with_nan = [
            {'status': 'completed', 'name': None},
            {'status': np.nan, 'name': 'Test'}
        ]
        df_with_nan = pd.DataFrame(data_with_nan)
        
        mock_console = MagicMock()
        mock_table = MagicMock()
        mock_console_class.return_value = mock_console
        mock_table_class.return_value = mock_table
        
        Cloudos.display_job_list_table(df_with_nan)
        
        # Check that NaN/None values become "N/A"
        row_calls = mock_table.add_row.call_args_list
        
        # First row: completed status, None name
        first_row_args = row_calls[0][0]
        assert first_row_args[1] == "N/A"  # None name becomes N/A
        
        # Second row: NaN status, Test name
        second_row_args = row_calls[1][0]
        assert second_row_args[0] == "N/A"  # NaN status becomes N/A

    @patch('cloudos_cli.clos.Console')
    @patch('cloudos_cli.clos.Table')
    def test_handles_empty_dataframe(self, mock_table_class, mock_console_class):
        """Test that empty DataFrames are handled gracefully."""
        empty_df = pd.DataFrame(columns=['status', 'name'])
        
        mock_console = MagicMock()
        mock_table = MagicMock()
        mock_console_class.return_value = mock_console
        mock_table_class.return_value = mock_table
        
        Cloudos.display_job_list_table(empty_df)
        
        # Should still create columns
        assert mock_table.add_column.call_count == 2
        
        # Should not add any rows
        assert mock_table.add_row.call_count == 0
        
        # Should still print the table
        mock_console.print.assert_called_once_with(mock_table)

    def test_function_is_static_method(self):
        """Test that the function can be called without creating an instance."""
        sample_data = pd.DataFrame({'status': ['completed'], 'name': ['test']})
        
        # Should not raise an error when called as static method
        with patch('cloudos_cli.clos.Console'), patch('cloudos_cli.clos.Table'):
            try:
                Cloudos.display_job_list_table(sample_data)
            except AttributeError as e:
                pytest.fail(f"Function should be static: {e}")

    @patch('cloudos_cli.clos.Console')
    @patch('cloudos_cli.clos.Table')
    def test_all_status_color_combinations(self, mock_table_class, mock_console_class):
        """Test all possible status color combinations."""
        data = [
            {'status': 'completed', 'name': 'job1'},
            {'status': 'failed', 'name': 'job2'},
            {'status': 'aborted', 'name': 'job3'},
            {'status': 'running', 'name': 'job4'},
            {'status': 'pending', 'name': 'job5'},
            {'status': 'queued', 'name': 'job6'},  # Should be blue
            {'status': 'unknown', 'name': 'job7'}  # Should be blue
        ]
        df = pd.DataFrame(data)
        
        mock_console = MagicMock()
        mock_table = MagicMock()
        mock_console_class.return_value = mock_console
        mock_table_class.return_value = mock_table
        
        Cloudos.display_job_list_table(df)
        
        row_calls = mock_table.add_row.call_args_list
        expected_colors = {
            'completed': 'green',
            'failed': 'red',
            'aborted': 'yellow',
            'running': 'blue',
            'pending': 'blue',
            'queued': 'blue',
            'unknown': 'blue'
        }
        
        for i, call_args in enumerate(row_calls):
            args, kwargs = call_args
            status = df.iloc[i]['status']
            status_arg = args[0]
            expected_color = expected_colors[status]
            expected_colored_status = f'[{expected_color}]{status}[/{expected_color}]'
            assert status_arg == expected_colored_status
