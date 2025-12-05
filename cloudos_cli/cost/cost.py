"""
Cost module for retrieving and displaying job cost information.
"""

from datetime import datetime
from rich.console import Console
from rich.table import Table
from cloudos_cli.utils.errors import BadRequestException
from cloudos_cli.utils.requests import retry_requests_get
import csv
import json
import os


class CostViewer:
    """Handles cost information retrieval and display."""

    def __init__(self, cloudos_url, apikey):
        self.cloudos_url = cloudos_url
        self.apikey = apikey
        self.console = Console()

    def get_job_costs(self, job_id, workspace_id, page=1, limit=100, verify=True):
        """
        Get cost information for a specific job.

        Parameters
        ----------
        job_id : str
            The job ID to get costs for
        workspace_id : str
            The workspace ID
        page : int
            Page number for pagination (default: 1)
        limit : int
            Number of results per page (default: 100)
        verify : bool or str
            SSL verification setting

        Returns
        -------
        dict
            JSON response containing cost data
        """
        headers = {
            "Content-type": "application/json",
            "apikey": self.apikey
        }

        url = f"{self.cloudos_url}/api/v1/jobs/{job_id}/costs/compute"
        params = {
            "page": page,
            "limit": limit,
            "teamId": workspace_id
        }

        r = retry_requests_get(url, headers=headers, params=params, verify=verify)

        if r.status_code >= 400:
            raise BadRequestException(r)

        return r.json()

    def _calculate_runtime(self, start_time_str, end_time_str):
        """Calculate runtime between two timestamp strings."""
        try:
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
            runtime = end_time - start_time

            total_seconds = int(runtime.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60

            if hours > 0:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        except Exception:
            return "N/A"

    def _format_storage(self, storage_info):
        """Format storage information."""
        if not storage_info or 'usageQuantity' not in storage_info:
            return "N/A"

        quantity = storage_info.get('usageQuantity', 0)
        unit = storage_info.get('usageUnit', '')
        return f"{quantity} {unit}"

    def _format_price(self, price_info, total=False):
        """Format price information."""
        if not price_info or 'amount' not in price_info:
            return "N/A"

        amount = price_info.get('amount', 0)
        if total:
            return f"${amount:.4f}"
        else:
            return f"${amount:.4f}/hr"

    def _format_lifecycle_type(self, is_cost_saving):
        """Format lifecycle type based on isCostSaving flag."""
        return "spot" if is_cost_saving else "on demand"

    def display_costs(self, job_id, workspace_id, output_format, verify=True):
        """
        Display cost information for a job with pagination.

        Parameters
        ----------
        job_id : str
            The job ID to display costs for
        output_format : str
            The desired output format (e.g., 'stdout', 'csv', 'json')
        workspace_id : str
            The workspace ID
        verify : bool or str
            SSL verification setting
        """
        limit = 20  # Display 20 rows per page
        current_page = 0

        try:
            # Get cost data
            cost_data = self.get_job_costs(job_id, workspace_id, 1, limit, verify)
            total_pages = (len(cost_data.get('workers', [])) + limit - 1) // limit

            # Prepare data for table
            rows = []

            final_cost = 0
            # Add master instance
            master = cost_data.get('master')
            if master:
                runtime = self._calculate_runtime(master.get('startTime', ''), master.get('endTime', ''))
                rows.append([
                    "Master",
                    master.get('id', 'N/A'),
                    master.get('machineType', 'N/A'),
                    self._format_lifecycle_type(master.get('isCostSaving', False)),
                    runtime,
                    self._format_storage(master.get('storage')),
                    self._format_price(master.get('instancePricePerHour')),
                    self._format_price(master.get('storagePricePerHour')),
                    self._format_price(master.get('totalPrice'), total=True)
                ])
                final_cost += master.get('totalPrice', {}).get('amount', 0)

            # Add worker instances
            workers = cost_data.get('workers', [])
            for worker in workers:
                runtime = self._calculate_runtime(worker.get('startTime', ''), worker.get('endTime', ''))
                rows.append([
                    "Worker",
                    worker.get('id', 'N/A'),
                    worker.get('machineType', 'N/A'),
                    self._format_lifecycle_type(worker.get('isCostSaving', False)),
                    runtime,
                    self._format_storage(worker.get('storage')),
                    self._format_price(worker.get('instancePricePerHour')),
                    self._format_price(worker.get('storagePricePerHour')),
                    self._format_price(worker.get('totalPrice'), total=True)
                ])
                final_cost += worker.get('totalPrice', {}).get('amount', 0)

            if output_format == "stdout":
                while True:
                    start = current_page * limit
                    end = start + limit

                    # Create and display table
                    table = Table(title=f"Job Cost Details - Job ID: {job_id}")

                    table.add_column("Type", style="cyan", no_wrap=True)
                    table.add_column("Instance id", style="blue", overflow="fold")
                    table.add_column("Instance", style="green", overflow="fold")
                    table.add_column("Life-cycle type", style="yellow", overflow="fold")
                    table.add_column("Run time", style="white", overflow="fold")
                    table.add_column("Compute storage", style="magenta", overflow="fold")
                    table.add_column("Instance price", style="red", overflow="fold")
                    table.add_column("Compute storage price", style="red", overflow="fold")
                    table.add_column("Total", style="bright_red", no_wrap=True)

                    page_rows = rows[start:end]

                    for row in page_rows:
                        table.add_row(*row)

                    if current_page == total_pages - 1:
                        table.add_row(*[""] * 9, end_section=True)
                        table.add_row(*[""] * 8 + [f"${final_cost:.4f}"])
                    self.console.clear()
                    self.console.print(table)

                    # Show pagination info
                    if total_pages > 1 and current_page < total_pages - 1:
                        self.console.print(f"On page {current_page+1}/{total_pages}: [bold cyan]n[/] = next, [bold cyan]p[/] = prev, [bold cyan]q[/] = quit")

                        # Controls
                        choice = input(">>> ").strip().lower()
                        if choice in ("n", "next") and current_page < total_pages - 1:
                            current_page += 1
                        elif choice in ("p", "prev") and current_page > 0:
                            current_page -= 1
                        elif choice in ("p", "prev") and current_page == 0:
                            self.console.print("[red]Invalid choice. Already on the first page.[/red]")
                        elif choice in ("q", "quit"):
                            break
                        else:
                            self.console.print("[red]Invalid choice. Please enter 'n' (next), 'p' (prev), or 'q' (quit).[/red]")
                    else:
                        # Only one page, no need for input, just exit
                        break
            headers = [
                "Type",
                "Instance id",
                "Instance",
                "Life-cycle type",
                "Run time",
                "Compute storage",
                "Instance price",
                "Compute storage price",
                "Total"
            ]
            if output_format == "csv":
                csv_filename = f"{job_id}_costs.csv"
                # Save as CSV
                with open(csv_filename, "w", newline="") as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(headers)
                    for row in rows:
                        writer.writerow(row)
                self.console.print(f"[green]Saved all cost rows to CSV: {os.path.abspath(csv_filename)}[/green]")

            if output_format == "json":
                # Save as JSON
                json_filename = f"{job_id}_costs.json"
                json_data = [dict(zip(headers, row)) for row in rows]
                # Add final cost as a separate field
                output_json = {
                    "job_id": job_id, "cost_table": json_data, "final_cost": f"${final_cost:.4f}"
                }
                with open(json_filename, "w") as jsonfile:
                    json.dump(output_json, jsonfile, indent=2)
                self.console.print(f"[green]Saved all cost rows to JSON: {os.path.abspath(json_filename)}[/green]")

        except BadRequestException as e:
            if '401' in str(e) or 'Forbidden' in str(e):
                raise ValueError("API can only show cost details of your own jobs, cannot see other user's job details.")
            elif '400' in str(e) or 'Not Found' in str(e):
                raise ValueError("Job not found or cost data not available for this job.")
            else:
                raise ValueError(f"{str(e)}")
        except Exception as e:
            raise ValueError(f"An unexpected error occurred. {str(e)}")
