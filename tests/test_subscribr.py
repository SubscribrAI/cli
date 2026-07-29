import importlib.util
import io
import json
import os
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("subscribr", ROOT / "subscribr.py")
subscribr = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subscribr)


class CliContractTest(unittest.TestCase):
    def test_generated_metadata_covers_all_current_operations(self):
        operation_ids = {route["operation_id"] for route in subscribr.ROUTES.values()}
        self.assertEqual(set(subscribr.METADATA["required_operation_ids"]), operation_ids)
        self.assertIn("operations.get-operation", subscribr.ROUTES)
        self.assertEqual("getOperation", subscribr.ROUTES["operations.get-operation"]["operation_id"])
        self.assertIn("team.create-api-token", subscribr.ROUTES)
        self.assertIn("scripts.cancel-script-agent-run", subscribr.ROUTES)
        self.assertIn("projects.list-projects", subscribr.ROUTES)
        self.assertIn("templates.create-template", subscribr.ROUTES)
        self.assertIn("voices.commit-voice-profile", subscribr.ROUTES)

    def test_aliases_resolve_to_generated_routes(self):
        key, route = subscribr.resolve_route("scripts", "agent-cancel")
        self.assertEqual("scripts.cancel-script-agent-run", key)
        self.assertEqual("cancelScriptAgentRun", route["operation_id"])

    def test_build_request_encodes_paths_query_body_and_safety_headers(self):
        get_route = {"method": "GET", "path": "/api/v1/projects/{project}"}
        method, path, body, headers = subscribr.build_request(get_route, {"project": "project:v1:idea:7", "include": ["tasks", "comments"]})
        self.assertEqual("GET", method)
        self.assertEqual("/api/v1/projects/project%3Av1%3Aidea%3A7?include=tasks&include=comments", path)
        self.assertIsNone(body)
        self.assertEqual({}, headers)

        patch_route = {"method": "PATCH", "path": "/api/v1/projects/{project}"}
        _, path, body, headers = subscribr.build_request(patch_route, {
            "project": "project:v1:script:8",
            "title": "Updated",
            "idempotency_key": "once-1",
            "if_match": '"project-r1"',
        })
        self.assertEqual("/api/v1/projects/project%3Av1%3Ascript%3A8", path)
        self.assertEqual({"title": "Updated"}, body)
        self.assertEqual({"Idempotency-Key": "once-1", "If-Match": '"project-r1"'}, headers)

    def test_generated_write_safety_requires_and_rejects_transport_headers(self):
        update_route = subscribr.ROUTES["projects.update-project"]
        with self.assertRaises(subscribr.CliError) as raised:
            subscribr.build_request(update_route, {"project": "project:v1:idea:7", "title": "Updated"})
        self.assertEqual(subscribr.EXIT_USAGE, raised.exception.exit_code)
        self.assertIn("idempotency", str(raised.exception).lower())

        with self.assertRaises(subscribr.CliError) as raised:
            subscribr.build_request(update_route, {
                "project": "project:v1:idea:7",
                "title": "Updated",
                "idempotency_key": "once-7",
            })
        self.assertIn("if-match", str(raised.exception).lower())

        create_idea_route = subscribr.ROUTES["ideas.create-channel-idea"]
        with self.assertRaises(subscribr.CliError) as raised:
            subscribr.build_request(create_idea_route, {
                "channel": 7,
                "title": "No transport header",
                "idempotency_key": "unsupported",
            })
        self.assertIn("does not support", str(raised.exception))

    def test_wait_is_not_sent_as_a_write_field_and_points_to_operation_polling(self):
        with self.assertRaises(subscribr.CliError) as raised:
            subscribr.run(["projects", "create-project", "--wait"])
        self.assertEqual(subscribr.EXIT_USAGE, raised.exception.exit_code)
        self.assertIn("operations get-operation", str(raised.exception).lower())

    def test_team_bound_auth_and_versioned_user_agent(self):
        with patch.dict(os.environ, {"SUBSCRIBR_API_TOKEN": "secret"}, clear=True):
            headers = subscribr.get_headers()
        self.assertEqual("Bearer secret", headers["Authorization"])
        self.assertEqual("subscribr-cli/2.0.0", headers["User-Agent"])

    def test_body_can_be_loaded_from_json_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as handle:
            json.dump({"profile_schema_version": 2}, handle)
            handle.flush()
            route = {"method": "POST", "path": "/api/v1/channels/{channel}/voices/validate"}
            _, _, body, _ = subscribr.build_request(route, {"channel": 4, "body": "@" + handle.name})
        self.assertEqual({"profile_schema_version": 2}, body)

    def test_raw_body_calls_fail_closed_when_the_method_or_extra_fields_are_ambiguous(self):
        with self.assertRaises(subscribr.CliError) as raised:
            subscribr.build_request({"method": "GET", "path": "/api/v1/operations/{operation}"}, {
                "operation": "6b33d5a6-72c8-4e1e-9bc4-8024f38be3fb",
                "body": {"ignored": True},
            })
        self.assertEqual(subscribr.EXIT_USAGE, raised.exception.exit_code)
        self.assertIn("only supported", str(raised.exception))

        with self.assertRaises(subscribr.CliError) as raised:
            subscribr.build_request({"method": "POST", "path": "/api/v1/channels/{channel}/voices/validate"}, {
                "channel": 4,
                "body": {"profile_schema_version": 2},
                "extra_field": "would previously disappear",
            })
        self.assertEqual(subscribr.EXIT_USAGE, raised.exception.exit_code)
        self.assertIn("cannot be combined", str(raised.exception))

    def test_missing_auth_has_stable_exit_class(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(subscribr.CliError) as raised:
                subscribr.get_headers()
        self.assertEqual(subscribr.EXIT_AUTH, raised.exception.exit_code)

    def test_help_and_version_are_transport_only(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(0, subscribr.run(["version"]))
        self.assertEqual("2.0.0\n", stdout.getvalue())


class RequestTest(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {
            "SUBSCRIBR_API_TOKEN": "secret",
            "SUBSCRIBR_API_BASE_URL": "https://example.test",
        }, clear=True)
        self.environment.start()

    def tearDown(self):
        self.environment.stop()

    def test_get_retries_transient_transport_failure(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"ok":true}'
        with patch("urllib.request.urlopen", side_effect=[urllib.error.URLError("down"), response]) as opener, patch("time.sleep"):
            self.assertEqual({"ok": True}, subscribr.request("GET", "/api/v1/team"))
        self.assertEqual(2, opener.call_count)

    def test_unkeyed_write_is_never_retried(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")) as opener:
            with self.assertRaises(subscribr.CliError) as raised:
                subscribr.request("POST", "/api/v1/projects", {"title": "A"})
        self.assertEqual(1, opener.call_count)
        self.assertEqual(subscribr.EXIT_TRANSIENT, raised.exception.exit_code)

    def test_keyed_write_can_retry_identical_request(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"data":{"id":"project:v1:idea:1"}}'
        with patch("urllib.request.urlopen", side_effect=[urllib.error.URLError("down"), response]) as opener, patch("time.sleep"):
            result = subscribr.request("POST", "/api/v1/projects", {"title": "A"}, {"Idempotency-Key": "same"})
        self.assertEqual("project:v1:idea:1", result["data"]["id"])
        self.assertEqual(2, opener.call_count)

    def test_http_errors_map_to_stable_exit_classes(self):
        error = urllib.error.HTTPError("https://example.test", 409, "Conflict", {}, io.BytesIO(b'{"error":{"code":"revision_conflict"}}'))
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(subscribr.CliError) as raised:
                subscribr.request("PATCH", "/api/v1/projects/project%3Av1%3Aidea%3A1", {}, max_attempts=1)
        self.assertEqual(subscribr.EXIT_CONFLICT, raised.exception.exit_code)
        self.assertEqual("revision_conflict", raised.exception.detail["error"]["code"])


if __name__ == "__main__":
    unittest.main()
