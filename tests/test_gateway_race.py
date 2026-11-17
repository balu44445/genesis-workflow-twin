import json
import subprocess


def test_gateway_claim_failure_and_interleaving_boundaries():
    result = subprocess.run(["node", "scripts/js_gateway_race.cjs"],
                            text=True, capture_output=True, check=True)
    report = json.loads(result.stdout)
    assert len(report["passed"]) == 6
    assert report["live_pdi_tested"] is False
