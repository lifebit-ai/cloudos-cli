"""
Cost module for job cost utility helpers.
"""

from datetime import datetime


class CostViewer:
    """Handles cost information utility methods."""

    def __init__(self, cloudos_url, apikey):
        self.cloudos_url = cloudos_url
        self.apikey = apikey

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
