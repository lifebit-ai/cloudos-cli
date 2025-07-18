from datetime import datetime, timezone


def _parse_iso8601_z(dt_str):
    """
    Parse an ISO8601 timestamp string that may end with 'Z' (UTC).
    Returns a timezone-aware datetime, or None if parsing fails.
    """
    if not dt_str:
        return None
    if dt_str.endswith('Z'):
        dt_str = dt_str[:-1] + '+00:00'
    try:
        return datetime.fromisoformat(dt_str)
    except ValueError:
        return None


def youngest_workflow_id_by_name(content, target_name, ignore_case=False, return_workflow=True):
    """
    Find the most recently created workflow whose .name matches `target_name`.
    
    Parameters
    ----------
    content : dict
        API response dict containing top-level "workflows".
    target_name : str
        Name to match.
    ignore_case : bool, default False
        If True, case-insensitive comparison.
    return_workflow : bool, default False
        If True, return the whole workflow dict; else return its _id.
    
    Returns
    -------
    str | dict | None
        _id (default), full workflow dict (if return_workflow=True), or None if no match.
    """
    workflows = content.get('workflows') or []
    if ignore_case:
        target_cmp = target_name.lower()
        matches = [wf for wf in workflows if wf.get('name', '').lower() == target_cmp]
    else:
        matches = [wf for wf in workflows if wf.get('name') == target_name]
    
    if not matches:
        return None
    
    def sort_key(wf):
        created = _parse_iso8601_z(wf.get('createdAt'))
        updated = _parse_iso8601_z(wf.get('updatedAt'))
        # Prefer createdAt; fall back to updatedAt; else epoch 0
        return created or updated or datetime.fromtimestamp(0, tz=timezone.utc)
    
    youngest = max(matches, key=sort_key)
    # keep structure as dictionary, will return inner dictionary just for the selected workflow
    youngest_d = {"workflows":[ youngest ]}
    youngest_id = youngest.get('_id')

    return youngest_d if return_workflow else youngest_id
