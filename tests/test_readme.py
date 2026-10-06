from pathlib import Path

from homi_gate.cli import main

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8-sig")
FAIL = ROOT / "examples" / "fail.json"


def test_readme_h1_matches_repo_name():
    assert README.lstrip().startswith("# homi-gate\n")


def test_readme_first_screen_matches_top100_craft():
    pip_at = README.find("pip install")
    later_at = README.find("## The three checks")
    assert 0 <= pip_at < later_at
    head = "\n".join(README.splitlines()[:26])
    assert "# homi-gate" in head
    assert "Homayoun Safarpour" in head
    badge = (
        "[![M8ven](https://m8ven.ai/badge/mcp/homayoun-safarpour/homi-gate"
        "?variant=verified)](https://m8ven.ai/mcp/homayoun-safarpour/homi-gate?s=readme)"
    )
    assert badge in head
    assert "variant=verified" in badge
    assert "git clone https://github.com/homayoun-safarpour/homi-gate" in head
    assert "pip install -e" in head
    assert "homi-gate check-completion examples/fail.json" in head
    assert "truncated=true" in head
    assert "completion_bit=false" in head
    assert "Interview pack" not in head
    assert "Hire-signal" not in head
    assert "\u2014" not in head


def test_readme_stranger_fail_is_untrusted():
    code = main(["check-completion", str(FAIL)])
    assert code == 1
