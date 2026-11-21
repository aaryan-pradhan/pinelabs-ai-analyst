import subprocess

PHRASE = "claude" + " code"  # split so this file does not match itself


def test_no_tracked_file_names_the_coding_tool():
    """The repo is public: no file credits the coding assistant used to build it."""
    hits = subprocess.run(["git", "grep", "-n", "-i", PHRASE], capture_output=True, text=True).stdout
    assert hits == "", hits
