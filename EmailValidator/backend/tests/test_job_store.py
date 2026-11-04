from app.services.job_store import JobStore


def test_job_lifecycle(test_settings):
    store = JobStore(test_settings)
    job_id = "a" * 32

    store.init_job(job_id, {"status": "uploaded", "total_records": 2})
    assert store.job_exists(job_id) is True

    metadata = store.load_metadata(job_id)
    assert metadata["status"] == "uploaded"

    store.save_progress(job_id, {"processed": 1, "total": 2})
    assert store.load_progress(job_id)["processed"] == 1

    store.truncate_results(job_id)
    store.append_result(job_id, {"email": "a@example.com", "final_status": "valid", "disposable": False, "is_duplicate": False})
    store.append_result(job_id, {"email": "b@example.com", "final_status": "invalid", "disposable": False, "is_duplicate": False})

    rows = list(store.iter_results(job_id))
    assert len(rows) == 2

    store.delete_job(job_id)
    assert store.job_exists(job_id) is False


def test_query_results_filter_and_search(test_settings):
    store = JobStore(test_settings)
    job_id = "b" * 32
    store.init_job(job_id, {"status": "completed", "total_records": 3})
    store.truncate_results(job_id)
    store.append_result(job_id, {"email": "valid@example.com", "final_status": "valid", "disposable": False, "is_duplicate": False})
    store.append_result(job_id, {"email": "trash@mailinator.com", "final_status": "risky", "disposable": True, "is_duplicate": False})
    store.append_result(job_id, {"email": "bad@nowhere.invalid", "final_status": "invalid", "disposable": False, "is_duplicate": False})

    rows, total = store.query_results(job_id, page=1, page_size=10, filter_="valid", search=None)
    assert total == 1
    assert rows[0]["email"] == "valid@example.com"

    rows, total = store.query_results(job_id, page=1, page_size=10, filter_="disposable", search=None)
    assert total == 1
    assert rows[0]["email"] == "trash@mailinator.com"

    rows, total = store.query_results(job_id, page=1, page_size=10, filter_="all", search="bad")
    assert total == 1
    assert rows[0]["email"] == "bad@nowhere.invalid"

    rows, total = store.query_results(job_id, page=1, page_size=2, filter_="all", search=None)
    assert total == 3
    assert len(rows) == 2

    store.delete_job(job_id)


def test_all_job_ids_and_summary(test_settings):
    store = JobStore(test_settings)
    job_id = "c" * 32
    store.init_job(job_id, {"status": "uploaded"})
    assert job_id in store.all_job_ids()

    assert store.load_summary(job_id) is None
    store.save_summary(job_id, {"valid_count": 1})
    assert store.load_summary(job_id)["valid_count"] == 1

    store.delete_job(job_id)
