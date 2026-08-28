import importlib.util
import io
import json
import os
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("subscribr", ROOT / "subscribr.py")
subscribr = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subscribr)


class CliContractTest(unittest.TestCase):
    VIDEO_ROUTES = {
        "video.list-capabilities": ("videoListCapabilities", "/api/v1/video/capabilities"),
        "video.list-channels": ("videoListChannels", "/api/v1/video/channels"),
        "video.get-channel": ("videoGetChannel", "/api/v1/video/channels/{videoChannel}"),
        "video.list-voices": ("videoListVoices", "/api/v1/video/voices"),
        "video.get-voice": ("videoGetVoice", "/api/v1/video/voices/{voice}"),
        "video.list-avatars": ("videoListAvatars", "/api/v1/video/avatars"),
        "video.get-avatar": ("videoGetAvatar", "/api/v1/video/avatars/{avatar}"),
        "video.list-media-assets": ("videoListMediaAssets", "/api/v1/video/media-assets"),
        "video.get-media-asset": ("videoGetMediaAsset", "/api/v1/video/media-assets/{mediaAsset}"),
    }

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

    def test_video_surface_contains_exactly_the_nine_canonical_reads(self):
        routes = {
            key: (route["operation_id"], route["path"])
            for key, route in subscribr.ROUTES.items()
            if key.startswith("video.")
        }

        self.assertEqual(self.VIDEO_ROUTES, routes)
        for key in self.VIDEO_ROUTES:
            self.assertEqual("GET", subscribr.ROUTES[key]["method"])
            self.assertEqual(["video:read"], subscribr.ROUTES[key]["abilities"])
            self.assertIsNone(subscribr.ROUTES[key]["write_safety"])

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

    def test_camel_case_contract_parameters_use_kebab_case_cli_options(self):
        route = subscribr.ROUTES["video.get-media-asset"]
        method, path, body, headers = subscribr.build_request(
            route,
            {"media_asset": "820e8400-e29b-41d4-a716-446655440006"},
        )

        self.assertEqual("GET", method)
        self.assertEqual(
            "/api/v1/video/media-assets/820e8400-e29b-41d4-a716-446655440006",
            path,
        )
        self.assertIsNone(body)
        self.assertEqual({}, headers)
        self.assertEqual("video-channel", subscribr.parameter_option("videoChannel"))

    def test_video_asset_lists_encode_page_and_per_page_query_options(self):
        for key in ("video.list-voices", "video.list-avatars", "video.list-media-assets"):
            route = subscribr.ROUTES[key]
            method, path, body, headers = subscribr.build_request(route, {"page": 2, "per_page": 5})

            self.assertEqual("GET", method)
            self.assertEqual(f"{route['path']}?page=2&per_page=5", path)
            self.assertIsNone(body)
            self.assertEqual({}, headers)
            self.assertEqual(["page", "per_page"], route["query_parameters"])

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
        self.assertEqual(f"subscribr-cli/{subscribr.VERSION}", headers["User-Agent"])

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
        self.assertEqual(f"{subscribr.VERSION}\n", stdout.getvalue())

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(0, subscribr.run(["video", "help"]))
        self.assertIn("optional: --page <value> --per-page <value>", stdout.getvalue())

    def test_run_prints_the_server_json_without_rewriting_it(self):
        payload = {
            "data": [{"id": "820e8400-e29b-41d4-a716-446655440003", "future": {"nested": True}}],
            "pagination": {"current_page": 1, "per_page": 20, "total": 1, "last_page": 1},
        }
        stdout = io.StringIO()
        with patch.object(subscribr, "request", return_value=payload), redirect_stdout(stdout):
            self.assertEqual(0, subscribr.run(["video", "list-voices", "--page", "1", "--per-page", "20"]))

        self.assertEqual(payload, json.loads(stdout.getvalue()))

    def test_authored_docs_define_the_video_slice_and_its_boundaries(self):
        readme = (ROOT / "README.md").read_text()
        skill = (ROOT / "skills/subscribr-api/SKILL.md").read_text()

        for command in self.VIDEO_ROUTES:
            action = command.split(".", 1)[1]
            self.assertIn(f"video {action}", readme)
            self.assertIn(f"video {action}", skill)
        for document in (readme, skill):
            self.assertIn("video_capability_unavailable", document)
            self.assertIn("video_provisioning_required", document)
            self.assertIn("Team-bound", document)
            self.assertIn("owner/admin-only", document)
            self.assertIn("quote", document)
            self.assertIn("revision", document)
        self.assertIn("Subscribr Video capability, Channel, and custom-asset reads", skill)



class AgentDiscoveryTest(unittest.TestCase):
    """
    An agent must be able to learn an operation's shape locally. Everything
    here has to work without touching the network.
    """

    WRITE = "scripts.create-channel-script"

    def domain_and_action(self):
        return self.WRITE.split(".", 1)

    def test_the_canonical_base_url_is_the_domain_we_control(self):
        """
        `subscribr.com` is a parked third-party domain. Shipping it as the
        default sent every customer bearer token off-platform.
        """
        self.assertEqual("https://subscribr.ai", subscribr.METADATA["base_url"])
        self.assertNotIn("subscribr.com", json.dumps(subscribr.METADATA))

    def test_token_guidance_points_at_a_host_we_control(self):
        self.assertTrue(subscribr.TOKEN_PAGE_URL.startswith("https://subscribr.ai/"))
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(subscribr.CliError) as raised:
                subscribr.get_headers()
        self.assertIn(subscribr.TOKEN_PAGE_URL, str(raised.exception))

    def test_domain_help_lists_required_body_fields_for_writes(self):
        domain, action = self.domain_and_action()
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(0, subscribr.run([domain, "help"]))
        output = stdout.getvalue()

        # Path param and the three body fields the server actually requires.
        for flag in ("--channel", "--title", "--topic", "--length"):
            self.assertIn(flag, output)

    def test_action_help_describes_fields_without_making_a_request(self):
        domain, action = self.domain_and_action()
        stdout = io.StringIO()
        with patch.object(subscribr, "request", side_effect=AssertionError("help must not call the API")):
            with redirect_stdout(stdout):
                self.assertEqual(0, subscribr.run([domain, action, "--help"]))
        output = stdout.getvalue()

        self.assertIn("Body fields (required)", output)
        self.assertIn("Body fields (optional)", output)
        self.assertIn("Token abilities: scripts:write", output)
        self.assertIn("Example --body:", output)

    def test_action_help_is_not_sent_as_a_request_field(self):
        """`--help` used to become a body field and reach the server."""
        domain, action = self.domain_and_action()
        with patch.object(subscribr, "request", side_effect=AssertionError("help must not call the API")):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(0, subscribr.run([domain, action, "-h"]))

    def test_unknown_action_fails_as_usage_before_reaching_the_network(self):
        with patch.object(subscribr, "request", side_effect=AssertionError("must not call the API")):
            with self.assertRaises(subscribr.CliError) as raised:
                subscribr.run(["scripts", "invent-a-route", "--help"])
        self.assertEqual(subscribr.EXIT_USAGE, raised.exception.exit_code)

    def test_required_options_cover_path_params_then_required_body_fields(self):
        route = subscribr.ROUTES[self.WRITE]

        self.assertEqual(
            ["--channel <value>", "--title <string>", "--topic <string>", "--length <integer>"],
            subscribr.required_options(route),
        )

    def test_optional_options_exclude_required_body_fields(self):
        route = subscribr.ROUTES[self.WRITE]
        optional = subscribr.optional_options(route)

        self.assertIn("--voice-id <integer>", optional)
        self.assertNotIn("--title <string>", optional)

    def test_range_labels_never_invent_a_bound(self):
        self.assertEqual("max 255", subscribr.range_label("", None, 255))
        self.assertEqual("min 1", subscribr.range_label("", 1, None))
        self.assertEqual("50..20000", subscribr.range_label("", 50, 20000))
        self.assertEqual("", subscribr.range_label("", None, None))

    def test_doctor_reports_the_bound_team_from_the_real_envelope(self):
        payload = {"team": {
            "id": 7,
            "name": "Acme",
            "user_role": "owner",
            "subscription": {"plan": "Automation"},
        }}
        stdout = io.StringIO()
        with patch.dict(os.environ, {"SUBSCRIBR_API_TOKEN": "t"}, clear=True), \
                patch.object(subscribr, "request", return_value=payload), \
                redirect_stdout(stdout):
            self.assertEqual(0, subscribr.run(["doctor"]))
        output = stdout.getvalue()

        self.assertIn("Team 7 (Acme)", output)
        self.assertIn("owner", output)
        self.assertIn("Automation", output)

    def test_doctor_without_a_token_explains_the_fix_and_never_calls_the_api(self):
        stdout = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), \
                patch.object(subscribr, "request", side_effect=AssertionError("must not call the API")), \
                redirect_stdout(stdout):
            self.assertEqual(subscribr.EXIT_AUTH, subscribr.run(["doctor"]))
        output = stdout.getvalue()

        self.assertIn("Token          MISSING", output)
        self.assertIn(subscribr.TOKEN_PAGE_URL, output)

    def test_doctor_surfaces_the_underlying_failure_reason(self):
        error = subscribr.CliError("Cannot reach x: bad cert", subscribr.EXIT_TRANSIENT, "bad cert")
        stdout = io.StringIO()
        with patch.dict(os.environ, {"SUBSCRIBR_API_TOKEN": "t"}, clear=True), \
                patch.object(subscribr, "request", side_effect=error), \
                redirect_stdout(stdout):
            self.assertEqual(subscribr.EXIT_TRANSIENT, subscribr.run(["doctor"]))

        self.assertIn("bad cert", stdout.getvalue())


class TransportTrustTest(unittest.TestCase):
    def test_production_uses_the_system_trust_store(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(subscribr.ssl_context())

    def test_a_missing_ca_bundle_is_a_usage_error(self):
        with patch.dict(os.environ, {"SUBSCRIBR_CA_BUNDLE": "/nope/missing.pem"}, clear=True):
            with self.assertRaises(subscribr.CliError) as raised:
                subscribr.ssl_context()
        self.assertEqual(subscribr.EXIT_USAGE, raised.exception.exit_code)

    def test_certificate_and_dns_failures_are_not_treated_as_transient(self):
        import socket as socket_module
        import ssl as ssl_module

        self.assertTrue(subscribr.permanent_network_failure(ssl_module.SSLError("boom")))
        self.assertTrue(subscribr.permanent_network_failure(socket_module.gaierror("boom")))
        self.assertTrue(subscribr.permanent_network_failure("CERTIFICATE_VERIFY_FAILED"))
        self.assertFalse(subscribr.permanent_network_failure("connection reset by peer"))

    def test_a_certificate_failure_reports_the_reason_and_does_not_retry(self):
        attempts = []

        def urlopen(request, timeout=None, context=None):
            attempts.append(request)
            raise urllib.error.URLError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed")

        with patch.dict(os.environ, {"SUBSCRIBR_API_TOKEN": "t"}, clear=True), \
                patch("urllib.request.urlopen", urlopen):
            with self.assertRaises(subscribr.CliError) as raised:
                subscribr.request("GET", "/api/v1/team")

        self.assertEqual(1, len(attempts), "a certificate failure must not be retried")
        self.assertIn("CERTIFICATE_VERIFY_FAILED", str(raised.exception))


class PackagingTest(unittest.TestCase):
    def test_declared_versions_stay_in_lockstep(self):
        """package.json, plugin.json, the Claude Code plugin manifests, and the CLI
        must agree, or `doctor` and the User-Agent report a version the registry
        never published, and `/plugin install` ships a version nobody can match."""
        package = json.loads((ROOT / "package.json").read_text())
        plugin = json.loads((ROOT / "plugin.json").read_text())
        claude_plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
        marketplace = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())

        self.assertEqual(subscribr.VERSION, package["version"])
        self.assertEqual(subscribr.VERSION, plugin["version"])
        self.assertEqual(subscribr.VERSION, claude_plugin["version"])
        for entry in marketplace["plugins"]:
            self.assertEqual(subscribr.VERSION, entry["version"])

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

    def test_keyed_write_can_retry_the_identical_request(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"data":{"id":"project:v1:idea:1"}}'
        with patch("urllib.request.urlopen", side_effect=[urllib.error.URLError("down"), response]) as opener, patch("time.sleep"):
            result = subscribr.request("POST", "/api/v1/projects", {"title": "A"}, {"Idempotency-Key": "same"})
        self.assertEqual("project:v1:idea:1", result["data"]["id"])
        self.assertEqual(2, opener.call_count)

    def test_numeric_retry_after_is_honored_without_retrying_early(self):
        error = urllib.error.HTTPError(
            "https://example.test",
            429,
            "Rate limited",
            {"Retry-After": "3"},
            io.BytesIO(b'{"error":{"code":"rate_limited"}}'),
        )
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"ok":true}'

        with patch("urllib.request.urlopen", side_effect=[error, response]) as opener, patch("time.sleep") as sleeper:
            self.assertEqual({"ok": True}, subscribr.request("GET", "/api/v1/team"))

        self.assertEqual(2, opener.call_count)
        sleeper.assert_called_once_with(3.0)

    def test_http_date_retry_after_is_parsed_relative_to_the_current_time(self):
        current = datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)

        self.assertEqual(
            4.0,
            subscribr.retry_after_seconds("Wed, 29 Jul 2026 12:00:04 GMT", current),
        )

    def test_retry_after_above_the_wait_threshold_returns_429_without_retrying(self):
        error = urllib.error.HTTPError(
            "https://example.test",
            429,
            "Rate limited",
            {"Retry-After": "6"},
            io.BytesIO(b'{"error":{"code":"rate_limited"}}'),
        )

        with patch("urllib.request.urlopen", side_effect=error) as opener, patch("time.sleep") as sleeper:
            with self.assertRaises(subscribr.CliError) as raised:
                subscribr.request("GET", "/api/v1/team")

        self.assertEqual(subscribr.EXIT_RATE_LIMIT, raised.exception.exit_code)
        self.assertEqual(1, opener.call_count)
        sleeper.assert_not_called()

    def test_http_errors_map_to_stable_exit_classes(self):
        error = urllib.error.HTTPError("https://example.test", 409, "Conflict", {}, io.BytesIO(b'{"error":{"code":"revision_conflict"}}'))
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(subscribr.CliError) as raised:
                subscribr.request("PATCH", "/api/v1/projects/project%3Av1%3Aidea%3A1", {}, max_attempts=1)
        self.assertEqual(subscribr.EXIT_CONFLICT, raised.exception.exit_code)
        self.assertEqual("revision_conflict", raised.exception.detail["error"]["code"])


if __name__ == "__main__":
    unittest.main()
