""" Author: Charlie """

from hei_fastapi_ddd.contexts.sys.application.job.registry import HANDLERS, load_handlers

EXPECTED_HANDLERS = {
    "sys_job_sample",
    "sys_job_log_cleanup",
    "sys_banner_status_sync",
    "sys_banner_flush_interactions",
    "sys_audit_alert",
    "sys_audit_log_cleanup",
    "iam_account_purge_cancelled",
}


def test_load_handlers_registers_expected_keys():
    load_handlers()
    assert EXPECTED_HANDLERS.issubset(HANDLERS.keys())
    assert "sys_file_cleanup_local_orphans" not in HANDLERS
