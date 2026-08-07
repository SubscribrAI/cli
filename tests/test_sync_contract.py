import importlib.util
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "sync_contract",
    ROOT / "scripts" / "sync_contract.py",
)
sync_contract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync_contract)


class ContractSyncTest(unittest.TestCase):
    def setUp(self):
        self.contract = {
            "info": {"version": "1.0.0"},
            "servers": [{"url": "https://subscribr.com"}],
            "x-subscribr-operation-manifest-version": "1.0.0",
            "paths": {
                "/api/v1/video/capabilities": {
                    "get": {
                        "operationId": "videoListCapabilities",
                        "x-cli-command": "list-capabilities",
                        "x-skill-group": "video",
                        "x-required-abilities": ["video:read"],
                        "parameters": [
                            {"name": "page", "in": "query"},
                            {"name": "per_page", "in": "query"},
                        ],
                    },
                },
            },
        }
        self.manifest = {
            "contract_version": "1.0.0",
            "manifest_version": "1.0.0",
            "source_sha256": "a" * 64,
            "operations": [{
                "abilities": ["video:read"],
                "method": "GET",
                "operation_id": "videoListCapabilities",
                "path": "/api/v1/video/capabilities",
            }],
        }

    def test_manifest_must_exactly_match_openapi_operations(self):
        sync_contract.validate_manifest(self.contract, self.manifest)

        drifted = deepcopy(self.manifest)
        drifted["operations"][0]["path"] = "/api/v1/video/invented"
        with self.assertRaisesRegex(ValueError, "exactly match"):
            sync_contract.validate_manifest(self.contract, drifted)

    def test_endpoint_reference_is_generated_from_openapi(self):
        reference = sync_contract.endpoint_reference(self.contract)

        self.assertIn("## Video", reference)
        self.assertIn(
            "| `GET` | `/api/v1/video/capabilities` | "
            "`videoListCapabilities` | `video:read` | read |",
            reference,
        )

    def test_cli_metadata_preserves_discoverable_query_parameters(self):
        metadata = sync_contract.operation_metadata(self.contract, "a" * 64)

        self.assertEqual(
            ["page", "per_page"],
            metadata["operations"]["video.list-capabilities"]["query_parameters"],
        )


if __name__ == "__main__":
    unittest.main()
