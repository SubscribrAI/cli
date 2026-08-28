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
            "servers": [{"url": "https://subscribr.ai"}],
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

    def test_cli_metadata_carries_the_canonical_base_url(self):
        metadata = sync_contract.operation_metadata(self.contract, "a" * 64)

        self.assertEqual("https://subscribr.ai", metadata["base_url"])

    def write_operation_contract(self):
        """A POST whose body schema lives behind a $ref, as the real contract does."""
        contract = deepcopy(self.contract)
        contract["components"] = {
            "schemas": {
                "CreateThingRequest": {
                    "type": "object",
                    "required": ["title", "length"],
                    "properties": {
                        "title": {"type": "string", "maxLength": 255},
                        "length": {
                            "type": "integer",
                            "minimum": 50,
                            "maximum": 20000,
                            "description": "Target length in words.",
                        },
                        "angle": {"type": ["string", "null"]},
                        "tags": {"type": ["array", "null"], "items": {"type": "string"}},
                        "mode": {"enum": ["fast", "thorough"]},
                    },
                },
            },
        }
        contract["paths"]["/api/v1/things"] = {
            "post": {
                "operationId": "createThing",
                "summary": "Create Thing",
                "x-cli-command": "create-thing",
                "x-skill-group": "things",
                "x-required-abilities": ["things:write"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/CreateThingRequest"},
                            "example": {"title": "A thing", "length": 1200},
                        },
                    },
                },
            },
        }
        return contract

    def test_write_operations_expose_their_required_body_fields(self):
        """
        Without this, `<domain> help` showed only path params, so every write was
        a guess. Guessed bodies were the largest single source of 422s.
        """
        metadata = sync_contract.operation_metadata(self.write_operation_contract(), "a" * 64)
        body = metadata["operations"]["things.create-thing"]["body"]

        self.assertEqual(["title", "length"], body["required"])
        self.assertTrue(body["body_required"])
        self.assertEqual({"title": "A thing", "length": 1200}, body["example"])

    def test_body_fields_describe_types_constraints_and_descriptions(self):
        metadata = sync_contract.operation_metadata(self.write_operation_contract(), "a" * 64)
        fields = metadata["operations"]["things.create-thing"]["body"]["fields"]

        self.assertEqual("integer", fields["length"]["type"])
        self.assertEqual(50, fields["length"]["minimum"])
        self.assertEqual(20000, fields["length"]["maximum"])
        self.assertEqual("Target length in words.", fields["length"]["description"])
        # OpenAPI 3.1 nullable unions collapse to the concrete type.
        self.assertEqual("string", fields["angle"]["type"])
        self.assertEqual("string[]", fields["tags"]["type"])
        self.assertEqual(["fast", "thorough"], fields["mode"]["enum"])

    def test_reads_have_no_body_metadata(self):
        metadata = sync_contract.operation_metadata(self.contract, "a" * 64)

        self.assertIsNone(metadata["operations"]["video.list-capabilities"]["body"])

    def test_skill_is_composed_from_the_canonical_body_plus_the_cli_addendum(self):
        """One authored source for the shared rules; the CLI only appends."""
        composed = sync_contract.compose_skill(
            "# Subscribr API\n\nShared rules.\n",
            "## Using the CLI\n\nCLI specifics.\n",
        )

        self.assertEqual(
            "# Subscribr API\n\nShared rules.\n\n## Using the CLI\n\nCLI specifics.\n",
            composed,
        )

    def test_skill_composition_tolerates_a_missing_addendum(self):
        self.assertEqual(
            "# Subscribr API\n",
            sync_contract.compose_skill("# Subscribr API\n\n\n", ""),
        )


if __name__ == "__main__":
    unittest.main()
