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
                'user.name': 'Alice',
                'user.surname': 'Smith'  # Add surname to test user fusion
            },
            {
                'status': 'running',
                'name': 'Variant Calling',
                'project.name': 'Genomics Lab',
                'user.name': 'Bob',
                'user.surname': 'Johnson'
            },
            {
                'status': 'failed',
                'name': 'ChIP-seq Pipeline',
                'project.name': 'Epigenomics',
                'user.name': 'Carol',
                'user.surname': 'Williams'
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
        
        # Call the function with default max_jobs
        Cloudos.display_job_list_table(self.sample_df)
        
        # Verify Console was created
        mock_console_class.assert_called_once()
        
        # Verify Table was created with appropriate title
        mock_table_class.assert_called_once()
        call_args = mock_table_class.call_args
        assert "CloudOS Jobs List" in call_args[1]["title"]
        
        # Verify console.print was called with the table
        mock_console.print.assert_called_once_with(mock_table)

    @patch('cloudos_cli.clos.Console')
    @patch('cloudos_cli.clos.Table')
    def test_columns_are_added_correctly(self, mock_table_class, mock_console_class):
        """Test that columns are added correctly with proper styling (transposed)."""
        mock_console = MagicMock()
        mock_table = MagicMock()
        mock_console_class.return_value = mock_console
        mock_table_class.return_value = mock_table
        
        Cloudos.display_job_list_table(self.sample_df)
        
        # In transposed view: 1 attribute column + N job columns
        expected_columns = 1 + len(self.sample_df)  # 1 + 3 = 4 columns total
        assert mock_table.add_column.call_count == expected_columns
        
        # Check that first column is for attributes
        first_call = mock_table.add_column.call_args_list[0]
        args, kwargs = first_call
        assert args[0] == "Attribute"
        assert kwargs.get('style') == 'cyan'

    @patch('cloudos_cli.clos.Console')
    @patch('cloudos_cli.clos.Table')
    def test_rows_are_added_correctly(self, mock_table_class, mock_console_class):
        """Test that rows are added correctly (transposed)."""
        mock_console = MagicMock()
        mock_table = MagicMock()
        mock_console_class.return_value = mock_console
        mock_table_class.return_value = mock_table
        
        Cloudos.display_job_list_table(self.sample_df)
        
        # In transposed view: number of rows = number of attributes from desired_order that exist in the data
        # The sample_df has: status, name, project.name, user.name
        # After processing: Status, Name, Project (from project.name), Owner (from user.name fusion)
        # From desired_order, only Status, Name, Project, Owner are present in processed DataFrame
        expected_rows = 4  # Status, Name, Project, Owner
        assert mock_table.add_row.call_count == expected_rows

    @patch('cloudos_cli.clos.Console')
    @patch('cloudos_cli.clos.Table')
    def test_status_color_coding(self, mock_table_class, mock_console_class):
        """Test that status values are colored correctly (transposed)."""
        mock_console = MagicMock()
        mock_table = MagicMock()
        mock_console_class.return_value = mock_console
        mock_table_class.return_value = mock_table
        
        Cloudos.display_job_list_table(self.sample_df)
        
        # Get all row calls
        row_calls = mock_table.add_row.call_args_list
        
        # Find the status row (first column is 'Status' attribute name, not 'status')
        status_row_call = None
        for call_args in row_calls:
            args, kwargs = call_args
            if args[0] == 'Status':  # First argument is attribute name (renamed)
                status_row_call = args
                break
        
        assert status_row_call is not None, "Status row not found"
        
        # Check that status values are properly colored
        # args[1:] are the job values (skipping attribute name)
        status_values = status_row_call[1:]
        expected_colors = ['[green]completed[/green]', '[blue]running[/blue]', '[red]failed[/red]']
        
        for i, status_value in enumerate(status_values):
            assert status_value == expected_colors[i]

    @patch('cloudos_cli.clos.Console')
    @patch('cloudos_cli.clos.Table')
    def test_non_status_values_are_magenta(self, mock_table_class, mock_console_class):
        """Test that non-status values are colored magenta (transposed)."""
        mock_console = MagicMock()
        mock_table = MagicMock()
        mock_console_class.return_value = mock_console
        mock_table_class.return_value = mock_table
        
        Cloudos.display_job_list_table(self.sample_df)
        
        # Get row calls and find a non-status row (e.g., 'Name' row)
        row_calls = mock_table.add_row.call_args_list
        
        name_row_call = None
        for call_args in row_calls:
            args, kwargs = call_args
            if args[0] == 'Name':  # First argument is attribute name (renamed)
                name_row_call = args
                break
        
        assert name_row_call is not None, "Name row not found"
        
        # Check that non-status values are magenta (skip first arg which is attribute name)
        for value in name_row_call[1:]:
            assert value.startswith('[magenta]')
            assert value.endswith('[/magenta]')

    @patch('cloudos_cli.clos.Console')
    @patch('cloudos_cli.clos.Table')
    def test_handles_nan_values(self, mock_table_class, mock_console_class):
        """Test that NaN and None values are handled correctly (transposed)."""
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
        
        # Get all row calls
        row_calls = mock_table.add_row.call_args_list
        
        # Find status and name rows (using renamed column names)
        status_row_call = None
        name_row_call = None
        
        for call_args in row_calls:
            args, kwargs = call_args
            if args[0] == 'Status':  # Renamed column
                status_row_call = args
            elif args[0] == 'Name':  # Renamed column
                name_row_call = args
        
        assert status_row_call is not None and name_row_call is not None
        
        # Check NaN/None handling
        # First job: completed status, None name -> name should be N/A
        assert name_row_call[1] == "N/A"  # None name becomes N/A
        
        # Second job: NaN status, Test name -> status should be N/A
        assert status_row_call[2] == "N/A"  # NaN status becomes N/A

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
        
        # Should create table with "No Jobs Found" message
        mock_table_class.assert_called_once()
        call_args = mock_table_class.call_args
        assert "No Jobs Found" in call_args[1]["title"]
        
        # Should print the table
        mock_console.print.assert_called_once_with(mock_table)

    def test_function_is_static_method(self):
        """Test that the function can be called without creating an instance."""
        sample_data = pd.DataFrame({'status': ['completed'], 'name': ['test']})
        
        # Should not raise an error when called as static method
        with patch('cloudos_cli.clos.Console'), patch('cloudos_cli.clos.Table'):
            try:
                Cloudos.display_job_list_table(sample_data)
                Cloudos.display_job_list_table(sample_data, max_jobs=5)  # Test with parameter
            except AttributeError as e:
                pytest.fail(f"Function should be static: {e}")

    @patch('cloudos_cli.clos.Console')
    @patch('cloudos_cli.clos.Table')
    def test_max_jobs_parameter(self, mock_table_class, mock_console_class):
        """Test that max_jobs parameter limits the number of jobs displayed."""
        # Create more sample data
        extended_data = self.sample_data + [
            {'status': 'pending', 'name': 'Job 4', 'project.name': 'Project D', 'user.name': 'User D'},
            {'status': 'queued', 'name': 'Job 5', 'project.name': 'Project E', 'user.name': 'User E'},
        ]
        extended_df = pd.DataFrame(extended_data)
        
        mock_console = MagicMock()
        mock_table = MagicMock()
        mock_console_class.return_value = mock_console
        mock_table_class.return_value = mock_table
        
        # Test with max_jobs=2
        Cloudos.display_job_list_table(extended_df, max_jobs=2)
        
        # Should have 1 attribute column + 2 job columns = 3 columns total
        assert mock_table.add_column.call_count == 3
        
        # Title should indicate showing 2 jobs
        call_args = mock_table_class.call_args
        assert "Showing 2 most recent jobs" in call_args[1]["title"]

    @patch('cloudos_cli.clos.Console')
    @patch('cloudos_cli.clos.Table')
    def test_all_status_color_combinations(self, mock_table_class, mock_console_class):
        """Test all possible status color combinations (transposed)."""
        data = [
            {'status': 'completed', 'name': 'job1'},
            {'status': 'failed', 'name': 'job2'},
            {'status': 'aborted', 'name': 'job3'},
            {'status': 'running', 'name': 'job4'},
            {'status': 'pending', 'name': 'job5'},
            {'status': 'queued', 'name': 'job6'},
            {'status': 'unknown', 'name': 'job7'}
        ]
        df = pd.DataFrame(data)
        
        mock_console = MagicMock()
        mock_table = MagicMock()
        mock_console_class.return_value = mock_console
        mock_table_class.return_value = mock_table
        
        Cloudos.display_job_list_table(df)
        
        # Get all row calls and find the status row (using renamed column name)
        row_calls = mock_table.add_row.call_args_list
        status_row_call = None
        for call_args in row_calls:
            args, kwargs = call_args
            if args[0] == 'Status':  # Renamed column
                status_row_call = args
                break
        
        assert status_row_call is not None, "Status row not found"
        
        expected_colors = [
            '[green]completed[/green]',
            '[red]failed[/red]', 
            '[yellow]aborted[/yellow]',
            '[blue]running[/blue]',
            '[blue]pending[/blue]',
            '[blue]queued[/blue]',
            '[blue]unknown[/blue]'
        ]
        
        # Check status colors (skip first arg which is attribute name)
        status_values = status_row_call[1:]
        for i, status_value in enumerate(status_values):
            assert status_value == expected_colors[i]

    @patch('cloudos_cli.clos.Console')
    @patch('cloudos_cli.clos.Table')
    def test_handles_array_values(self, mock_table_class, mock_console_class):
        """Test that array values are handled correctly without ValueError."""
        # Create DataFrame with array-like values
        data_with_arrays = [
            {'status': 'completed', 'name': 'job1', 'array_col': [1, 2, 3]},
            {'status': 'running', 'name': 'job2', 'array_col': np.array([4, 5, 6])},
            {'status': 'failed', 'name': None, 'array_col': None}
        ]
        df_with_arrays = pd.DataFrame(data_with_arrays)
        
        mock_console = MagicMock()
        mock_table = MagicMock()
        mock_console_class.return_value = mock_console
        mock_table_class.return_value = mock_table
        
        # This should not raise a ValueError about ambiguous array truth values
        Cloudos.display_job_list_table(df_with_arrays)
        
        # Check that function executed successfully
        mock_console.print.assert_called_once_with(mock_table)
        
        # In transposed view: only columns from desired_order that exist in processed data are shown
        # df_with_arrays has: status, name, array_col
        # After processing: Status, Name (from original columns), array_col is not in desired_order
        # From desired_order, only Status and Name are present, so 2 rows expected
        assert mock_table.add_row.call_count == 2
