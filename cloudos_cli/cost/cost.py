"""
Cost module for retrieving and displaying job cost information.
"""

from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from cloudos_cli.utils.errors import BadRequestException
from cloudos_cli.utils.requests import retry_requests_get


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

    def _format_price(self, price_info):
        """Format price information."""
        if not price_info or 'amount' not in price_info:
            return "N/A"

        amount = price_info.get('amount', 0)
        currency = price_info.get('currencyCode', 'USD')
        return f"{amount:.4f} {currency}"

    def _format_lifecycle_type(self, is_cost_saving):
        """Format lifecycle type based on isCostSaving flag."""
        return "Cost-saving" if is_cost_saving else "On-demand"

    def display_costs(self, job_id, workspace_id, verify=True):
        """
        Display cost information for a job with pagination.

        Parameters
        ----------
        job_id : str
            The job ID to display costs for
        workspace_id : str
            The workspace ID
        verify : bool or str
            SSL verification setting
        """
        page = 1
        limit = 20 # Display 20 rows per page

        while True:
            try:
                # Get cost data
                cost_data = self.get_job_costs(job_id, workspace_id, page, limit, verify)

                # Prepare data for table
                rows = []

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
                        self._format_price(master.get('totalPrice'))
                    ])

                # Add worker instances
                workers = cost_data.get('workers', [])
                for i, worker in enumerate(workers):
                    runtime = self._calculate_runtime(worker.get('startTime', ''), worker.get('endTime', ''))
                    rows.append([
                        f"Worker {i+1}",
                        worker.get('id', 'N/A'),
                        worker.get('machineType', 'N/A'),
                        self._format_lifecycle_type(worker.get('isCostSaving', False)),
                        runtime,
                        self._format_storage(worker.get('storage')),
                        self._format_price(worker.get('instancePricePerHour')),
                        self._format_price(worker.get('storagePricePerHour')),
                        self._format_price(worker.get('totalPrice'))
                    ])

                # Create and display table
                table = Table(title=f"Job Cost Details - Job ID: {job_id}")

                table.add_column("Node Type", style="cyan", no_wrap=True)
                table.add_column("Instance ID", style="blue")
                table.add_column("Instance Type", style="green")
                table.add_column("Life-cycle Type", style="yellow")
                table.add_column("Run Time", style="white")
                table.add_column("Compute Storage", style="magenta")
                table.add_column("Instance Price", style="red")
                table.add_column("Storage Price", style="red")
                table.add_column("Total", style="bright_red", no_wrap=True)

                for row in rows:
                    table.add_row(*row)

                self.console.print(table)

                # Get pagination metadata
                pagination = cost_data.get('paginationMetadata', {})
                current_page = pagination.get('Pagination-Page', 1)
                total_count = pagination.get('Pagination-Count', 0)
                page_limit = pagination.get('Pagination-Limit', limit)

                total_pages = (total_count + page_limit - 1) // page_limit if total_count > 0 else 1

                # Show pagination info
                if total_pages > 1:
                    self.console.print(f"\nPage {current_page} of {total_pages} (Total instances: {total_count})")

                    # Pagination controls
                    if total_pages > 1:
                        choices = []
                        if current_page > 1:
                            choices.append("previous")
                        if current_page < total_pages:
                            choices.append("next")
                        choices.append("quit")

                        if len(choices) > 1:
                            choice = Prompt.ask(
                                "Navigation options",
                                choices=choices,
                                default="quit"
                            )

                            if choice == "next" and current_page < total_pages:
                                page += 1
                                continue
                            elif choice == "previous" and current_page > 1:
                                page -= 1
                                continue
                            elif choice == "quit":
                                break
                        else:
                            # Only quit option available
                            break
                    else:
                        break
                else:
                    break

            except BadRequestException as e:
                if '403' in str(e) or 'Forbidden' in str(e):
                    self.console.print("[red][Error] API can only show cost details of your own jobs, cannot see other user's job details.[/red]")
                    break
                elif '404' in str(e) or 'Not Found' in str(e):
                    self.console.print("[red][Error] Job not found or cost data not available for this job.[/red]")
                    break
                else:
                    self.console.print(f"[red][Error] {str(e)}[/red]")
                    break
            except Exception as e:
                self.console.print(f"[red][Error] An unexpected error occurred: {str(e)}[/red]")
                break
