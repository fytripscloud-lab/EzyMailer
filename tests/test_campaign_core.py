import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlparse

from main import (
    AppState,
    BrowserSessionHandle,
    BrowserTabHandle,
    CampaignSendWorker,
    DashboardPage,
    FairThreadLock,
)


class CampaignCoreTests(unittest.TestCase):
    def test_automatic_no_delay_is_the_default_sending_mode(self) -> None:
        self.assertTrue(AppState().automatic_no_delay)

    def test_browser_connection_gate_serves_all_tabs_in_fifo_order(self) -> None:
        gate = FairThreadLock()
        acquired: list[int] = []
        gate.acquire()

        def enter_gate(tab_index: int) -> None:
            with gate:
                acquired.append(tab_index)

        threads: list[threading.Thread] = []
        for tab_index in range(1, 5):
            thread = threading.Thread(target=enter_gate, args=(tab_index,))
            thread.start()
            threads.append(thread)
            expected_ticket_count = tab_index + 1  # Includes the test's held ticket.
            for _attempt in range(100):
                if gate._next_ticket >= expected_ticket_count:
                    break
                threading.Event().wait(0.001)

        gate.release()
        for thread in threads:
            thread.join(timeout=2)

        self.assertEqual(acquired, [1, 2, 3, 4])
        self.assertTrue(all(not thread.is_alive() for thread in threads))

    def test_campaign_shutdown_releases_paused_workers_and_clears_queue(self) -> None:
        class DashboardStub:
            def __init__(self) -> None:
                self._campaign_cancel_event = threading.Event()
                self._campaign_pause_event = threading.Event()
                self._campaign_worker_queue = [{"lane": 1}]
                self._campaign_active = True
                self._campaign_paused = True
                self.logged: list[str] = []
                self.controls_refreshed = False

            def _log_action(self, message: str) -> None:
                self.logged.append(message)

            def _update_campaign_action_state(self) -> None:
                self.controls_refreshed = True

        dashboard = DashboardStub()
        DashboardPage._request_campaign_workers_stop(dashboard)

        self.assertTrue(dashboard._campaign_cancel_event.is_set())
        self.assertTrue(dashboard._campaign_pause_event.is_set())
        self.assertEqual(dashboard._campaign_worker_queue, [])
        self.assertFalse(dashboard._campaign_paused)
        self.assertTrue(dashboard.controls_refreshed)

    def test_plain_text_editor_clear_preserves_signal_state(self) -> None:
        class Cursor:
            selected = None
            removed = False

            def select(self, selection) -> None:
                self.selected = selection

            def removeSelectedText(self) -> None:
                self.removed = True

        class Editor:
            def __init__(self) -> None:
                self.cursor = Cursor()
                self.blocked = False
                self.block_calls: list[bool] = []
                self.installed_cursor = None

            def blockSignals(self, blocked: bool) -> bool:
                previous = self.blocked
                self.blocked = blocked
                self.block_calls.append(blocked)
                return previous

            def textCursor(self):
                return self.cursor

            def setTextCursor(self, cursor) -> None:
                self.installed_cursor = cursor

        editor = Editor()
        DashboardPage._clear_plain_text_editor(editor)

        self.assertEqual(editor.block_calls, [True, False])
        self.assertTrue(editor.cursor.removed)
        self.assertIs(editor.installed_cursor, editor.cursor)

    def test_send_log_accepts_only_successful_sent_entries(self) -> None:
        self.assertTrue(
            DashboardPage._is_campaign_sent_log(
                "[16:00:20] Window 1 / Tab 4 sent customer@example.com"
            )
        )
        self.assertFalse(
            DashboardPage._is_campaign_sent_log(
                "[16:00:20] Window 1 / Tab 4 preparing customer@example.com (attempt 1/4)"
            )
        )
        self.assertFalse(
            DashboardPage._is_campaign_sent_log(
                "[16:00:20] Window 1 / Tab 4 attempt 1/4 failed for customer@example.com: timeout"
            )
        )
        self.assertFalse(DashboardPage._is_campaign_sent_log("[16:00:20] Campaign complete"))

    def test_browser_windows_expand_into_independent_tab_lanes(self) -> None:
        sessions = [
            BrowserSessionHandle(
                f"window-{index}",
                f"Window {index}",
                "Incognito",
                debug_port=51000 + index,
                tab_count=3,
            )
            for index in (1, 2)
        ]

        lanes = DashboardPage._campaign_tab_lanes(None, sessions)

        self.assertEqual(len(lanes), 6)
        self.assertTrue(all(isinstance(lane, BrowserTabHandle) for lane in lanes))
        self.assertEqual(len({lane.session_id for lane in lanes}), 6)
        self.assertEqual([lane.tab_index for lane in lanes], [1, 2, 3, 1, 2, 3])
        self.assertIsNot(lanes[0].send_lock, lanes[1].send_lock)
        self.assertIs(lanes[0].connect_lock, lanes[1].connect_lock)
        self.assertIsNot(lanes[0].connect_lock, lanes[3].connect_lock)

    def test_app_managed_chromium_is_preferred_over_installed_chrome(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = Path(temp_dir)
            chromium = (
                cache
                / "chromium-1234"
                / "chrome-mac-arm64"
                / "Google Chrome for Testing.app"
                / "Contents"
                / "MacOS"
                / "Google Chrome for Testing"
            )
            chromium.parent.mkdir(parents=True)
            chromium.touch()
            installed_chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
            with mock.patch.dict("os.environ", {"EZYM_MAILER_BROWSER_BINARY": ""}), mock.patch(
                "main._browser_cache_dir", return_value=cache
            ), mock.patch("main._installed_browser_binary", return_value=installed_chrome):
                selected = DashboardPage._browser_binary(None)

        self.assertEqual(selected.resolve(), chromium.resolve())

    def test_bundled_chromium_is_preferred_over_cache_and_installed_browser(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_root = Path(temp_dir)
            chromium = (
                bundle_root
                / "playwright-browsers"
                / "chromium-1234"
                / "chrome-mac-arm64"
                / "Google Chrome for Testing.app"
                / "Contents"
                / "MacOS"
                / "Google Chrome for Testing"
            )
            chromium.parent.mkdir(parents=True)
            chromium.touch()
            with mock.patch.object(__import__("main").sys, "frozen", True, create=True), mock.patch.object(
                __import__("main").sys, "_MEIPASS", str(bundle_root), create=True
            ), mock.patch("main._browser_cache_dir", return_value=Path("/missing/cache")), mock.patch(
                "main._installed_browser_binary", return_value=Path("/installed/chrome")
            ):
                selected = DashboardPage._browser_binary(None)

        self.assertEqual(selected.resolve(), chromium.resolve())

    def test_completed_gmail_attachment_does_not_treat_remove_control_as_progress(self) -> None:
        class VisibleMatch:
            def count(self) -> int:
                return 1

            def nth(self, _index: int):
                return self

            def is_visible(self) -> bool:
                return True

        class NoProgress:
            def count(self) -> int:
                return 0

        class ComposeRoot:
            progress_selector = ""

            def get_by_text(self, text: str, *, exact: bool):
                self.requested_text = text
                self.exact = exact
                return VisibleMatch()

            def locator(self, selector: str):
                self.progress_selector = selector
                return NoProgress()

        class Page:
            waits = 0

            def wait_for_timeout(self, _milliseconds: int) -> None:
                self.waits += 1

        compose_root = ComposeRoot()
        page = Page()
        DashboardPage._wait_for_gmail_attachment_upload(
            None,
            page,
            compose_root,
            ["/tmp/TFA-17-RXFEU.pdf"],
            timeout=1,
        )

        self.assertEqual(compose_root.requested_text, "TFA-17-RXFEU.pdf")
        self.assertFalse(compose_root.exact)
        self.assertNotIn(".vX", compose_root.progress_selector)
        self.assertGreaterEqual(page.waits, 3)

    def test_gmail_attachment_name_can_be_outside_file_input_ancestor(self) -> None:
        class Match:
            def __init__(self, visible: bool):
                self.visible = visible

            def count(self) -> int:
                return 1

            def nth(self, _index: int):
                return self

            def is_visible(self) -> bool:
                return self.visible

        class NoProgress:
            def count(self) -> int:
                return 0

        class NarrowComposeRoot:
            def get_by_text(self, _text: str, *, exact: bool):
                self.exact = exact
                return Match(False)

            def locator(self, _selector: str):
                return NoProgress()

        class Page:
            waits = 0

            def get_by_text(self, text: str, *, exact: bool):
                self.requested_text = text
                self.exact = exact
                return Match(True)

            def wait_for_timeout(self, _milliseconds: int) -> None:
                self.waits += 1

        compose_root = NarrowComposeRoot()
        page = Page()
        DashboardPage._wait_for_gmail_attachment_upload(
            None,
            page,
            compose_root,
            ["/tmp/QQSDOBQ-6U7TPL.pdf"],
            timeout=1,
        )

        self.assertEqual(page.requested_text, "QQSDOBQ-6U7TPL.pdf")
        self.assertFalse(page.exact)
        self.assertGreaterEqual(page.waits, 3)

    def test_compose_url_contains_all_fields_and_is_unique(self) -> None:
        first = DashboardPage._gmail_compose_url(
            None,
            "duplicate@example.com",
            "Subject & value",
            "Line one\nLine two",
        )
        second = DashboardPage._gmail_compose_url(
            None,
            "duplicate@example.com",
            "Subject & value",
            "Line one\nLine two",
        )
        self.assertNotEqual(first, second)
        query = parse_qs(urlparse(first).query)
        self.assertEqual(query["view"], ["cm"])
        self.assertEqual(query["to"], ["duplicate@example.com"])
        self.assertEqual(query["su"], ["Subject & value"])
        self.assertEqual(query["body"], ["Line one\nLine two"])

    def test_unvalidated_duplicates_are_preserved_and_all_are_distributed(self) -> None:
        raw = DashboardPage._extract_email_candidates(
            None,
            "A@example.com\na@EXAMPLE.com\nb@example.com",
        )
        self.assertEqual(
            raw,
            ["a@example.com", "a@example.com", "b@example.com"],
        )

        recipients = ["duplicate@example.com", "duplicate@example.com"] + [
            f"user{index}@example.com" for index in range(1398)
        ]
        chunks = DashboardPage._chunk_campaign_recipients(None, recipients, 3, 1)
        self.assertEqual([len(chunk) for chunk in chunks], [467, 467, 466])
        self.assertEqual([item for chunk in chunks for item in chunk], recipients)

    def test_validation_retains_duplicate_recipient_rows(self) -> None:
        accepted, rejected, duplicates = DashboardPage._validate_email_candidates(
            [
                "same@gmail.com",
                "same@gmail.com",
                "other@gmail.com",
                "blocked@example.com",
            ],
            gmail_only=True,
        )

        self.assertEqual(
            accepted,
            ["same@gmail.com", "same@gmail.com", "other@gmail.com"],
        )
        self.assertEqual(rejected, ["blocked@example.com"])
        self.assertEqual(duplicates, 1)

    def test_worker_processes_a_1400_recipient_disk_queue(self) -> None:
        recipients = [f"user{index}@example.com" for index in range(1400)]
        sent: list[str] = []
        cleaned_sessions: list[str] = []
        pause_event = threading.Event()
        pause_event.set()

        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = Path(temp_dir) / "recipients.txt"
            queue_path.write_text("\n".join(recipients) + "\n", encoding="utf-8")
            worker = CampaignSendWorker(
                BrowserSessionHandle("test", "Test", "Normal"),
                None,
                pause_event,
                threading.Event(),
                lambda _session, recipient, *_args: sent.append(recipient),
                recipient_queue_path=queue_path,
                task_factory=lambda recipient: {
                    "recipient": recipient,
                    "subject": "Subject",
                    "body_text": "Body",
                    "attachment_html": "",
                    "attachment_format": "PDF document",
                    "file_name_value": "",
                },
                task_total=len(recipients),
                window_label="Window 1",
                delay_mode="Fixed",
                delay_from=0,
                delay_to=0,
                retry_count=0,
                retry_enabled=False,
                convert_enabled=False,
                attachment_formats=[],
                file_name_mode="auto",
                window_send_mode="Parallel",
                cleanup_callback=lambda session: cleaned_sessions.append(session.session_id),
            )
            worker.run()

        self.assertEqual(sent, recipients)
        self.assertEqual(cleaned_sessions, ["test"])

    def test_automatic_worker_ignores_delays_between_retries_and_recipients(self) -> None:
        attempts: list[str] = []
        pause_event = threading.Event()
        pause_event.set()

        def send(_session, recipient, *_args) -> None:
            attempts.append(recipient)
            if len(attempts) == 1:
                raise RuntimeError("temporary failure")

        tasks = [
            {
                "recipient": recipient,
                "subject": "Subject",
                "body_text": "Body",
                "attachment_html": "",
                "attachment_format": "PDF document",
                "file_name_value": "",
            }
            for recipient in ("first@example.com", "second@example.com")
        ]
        worker = CampaignSendWorker(
            BrowserSessionHandle("test", "Test", "Normal"),
            tasks,
            pause_event,
            threading.Event(),
            send,
            window_label="Window 1",
            delay_mode="Fixed",
            delay_from=60,
            delay_to=60,
            retry_count=1,
            retry_enabled=True,
            convert_enabled=False,
            attachment_formats=[],
            file_name_mode="auto",
            window_send_mode="Parallel",
            automatic_no_delay=True,
        )
        worker._sleep_with_controls = mock.Mock(
            side_effect=AssertionError("automatic sending must not enter delay handling")
        )

        worker.run()

        self.assertEqual(
            attempts,
            ["first@example.com", "first@example.com", "second@example.com"],
        )
        worker._sleep_with_controls.assert_not_called()



if __name__ == "__main__":
    unittest.main()
