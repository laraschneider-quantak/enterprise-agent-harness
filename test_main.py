from pathlib import Path

from main import list_repository_files, read_file


def test_list_repository_files_excludes_sensitive_paths():
    files = list_repository_files()

    assert ".env" not in files
    assert not any(".venv" in Path(file).parts for file in files)
    assert not any(".git" in Path(file).parts for file in files)


def test_read_file_blocks_env():
    result = read_file(".env")

    assert "DENIED" in result


def test_read_file_blocks_parent_directory():
    result = read_file("../test.txt")

    assert "outside the repository" in result