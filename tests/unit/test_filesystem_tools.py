"""
Unit tests for filesystem tools

Tests read-only file operations with security controls.
"""

import gc

import pytest

from mcp_server_langgraph.tools.filesystem_tools import list_directory, read_file, search_files


@pytest.mark.unit
@pytest.mark.xdist_group(name="testreadfile")
class TestReadFile:
    """Test suite for read_file tool"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_read_existing_file(self, tmp_path):
        """Test reading an existing text file"""
        test_file = tmp_path / "test.txt"
        test_content = "Hello, World!"
        test_file.write_text(test_content)

        result = read_file.invoke({"file_path": str(test_file)})
        assert test_content in result
        assert "test.txt" in result

    def test_read_file_with_size_limit(self, tmp_path):
        """Test reading file with size limit"""
        test_file = tmp_path / "large.txt"
        test_content = "A" * 1000
        test_file.write_text(test_content)

        result = read_file.invoke({"file_path": str(test_file), "max_bytes": 100})
        assert len(result) < len(test_content)
        assert "truncated" in result

    def test_read_nonexistent_file(self, tmp_path):
        """Test error handling for nonexistent file"""
        result = read_file.invoke({"file_path": str(tmp_path / "nonexistent_file_12345.txt")})
        assert "Error" in result or "does not exist" in result

    def test_read_directory_instead_of_file(self, tmp_path):
        """Test error when trying to read a directory"""
        result = read_file.invoke({"file_path": str(tmp_path)})
        assert "Error" in result or "not a file" in result

    def test_read_unsafe_path(self):
        """Test security - block access to system directories"""
        unsafe_paths = ["/etc/passwd", "/root/.ssh/id_rsa", "/sys/kernel"]
        for path in unsafe_paths:
            result = read_file.invoke({"file_path": path})
            assert "Error" in result or "Access denied" in result

    def test_read_supported_file_types(self, tmp_path):
        """Test reading different supported file types"""
        supported_types = [".txt", ".md", ".json", ".yaml", ".py"]
        for ext in supported_types:
            test_file = tmp_path / f"test{ext}"
            test_file.write_text("test content")
            result = read_file.invoke({"file_path": str(test_file)})
            assert "test content" in result

    def test_read_unsupported_file_type(self, tmp_path):
        """Test rejection of unsupported file types"""
        test_file = tmp_path / "test.exe"
        test_file.write_bytes(b"binary content")
        result = read_file.invoke({"file_path": str(test_file)})
        assert "Error" in result or "not allowed" in result


@pytest.mark.unit
@pytest.mark.xdist_group(name="testlistdirectory")
class TestListDirectory:
    """Test suite for list_directory tool"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_list_directory_contents(self, tmp_path):
        """Test listing directory contents"""
        # Create test files
        (tmp_path / "file1.txt").write_text("test")
        (tmp_path / "file2.md").write_text("test")
        (tmp_path / "subdir").mkdir()

        result = list_directory.invoke({"directory_path": str(tmp_path)})
        assert "file1.txt" in result
        assert "file2.md" in result
        assert "subdir" in result
        assert "[FILE]" in result
        assert "[DIR]" in result

    def test_list_directory_hidden_files(self, tmp_path):
        """Test listing with hidden files"""
        (tmp_path / "visible.txt").write_text("test")
        (tmp_path / ".hidden").write_text("test")

        # Without show_hidden
        result1 = list_directory.invoke({"directory_path": str(tmp_path), "show_hidden": False})
        assert "visible.txt" in result1
        assert ".hidden" not in result1

        # With show_hidden
        result2 = list_directory.invoke({"directory_path": str(tmp_path), "show_hidden": True})
        assert "visible.txt" in result2
        assert ".hidden" in result2

    def test_list_empty_directory(self, tmp_path):
        """Test listing empty directory"""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = list_directory.invoke({"directory_path": str(empty_dir)})
        assert "(empty)" in result

    def test_list_nonexistent_directory(self, tmp_path):
        """Test error handling for nonexistent directory"""
        result = list_directory.invoke({"directory_path": str(tmp_path / "nonexistent_dir_12345")})
        assert "Error" in result or "does not exist" in result

    def test_list_file_instead_of_directory(self, tmp_path):
        """Test error when trying to list a file"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        result = list_directory.invoke({"directory_path": str(test_file)})
        assert "Error" in result or "not a directory" in result

    def test_list_unsafe_directory(self):
        """Test security - block access to system directories"""
        unsafe_paths = ["/etc", "/root", "/sys"]
        for path in unsafe_paths:
            result = list_directory.invoke({"directory_path": path})
            assert "Error" in result or "Access denied" in result


@pytest.mark.unit
@pytest.mark.xdist_group(name="testsearchfiles")
class TestSearchFiles:
    """Test suite for search_files tool"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_search_files_by_pattern(self, tmp_path):
        """Test searching files by pattern"""
        # Create test files
        (tmp_path / "test1.txt").write_text("test")
        (tmp_path / "test2.txt").write_text("test")
        (tmp_path / "other.md").write_text("test")

        result = search_files.invoke({"directory_path": str(tmp_path), "pattern": "*.txt"})
        assert "test1.txt" in result
        assert "test2.txt" in result
        assert "other.md" not in result

    def test_search_files_recursive(self, tmp_path):
        """Test recursive file search"""
        # Create nested structure
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / "root.py").write_text("test")
        (subdir / "nested.py").write_text("test")

        result = search_files.invoke({"directory_path": str(tmp_path), "pattern": "*.py"})
        assert "root.py" in result
        assert "nested.py" in result

    def test_search_files_max_results(self, tmp_path):
        """Test max results limit"""
        # Create many files
        for i in range(25):
            (tmp_path / f"file{i}.txt").write_text("test")

        result = search_files.invoke({"directory_path": str(tmp_path), "pattern": "*.txt", "max_results": 10})
        assert "Found: 10 files" in result
        assert "limited to 10 results" in result

    def test_search_files_no_matches(self, tmp_path):
        """Test search with no matches"""
        (tmp_path / "test.txt").write_text("test")

        result = search_files.invoke({"directory_path": str(tmp_path), "pattern": "*.nonexistent"})
        assert "(no matches)" in result or "Found: 0 files" in result

    def test_search_files_specific_name(self, tmp_path):
        """Test searching for specific filename"""
        (tmp_path / "config.yaml").write_text("test")
        (tmp_path / "other.yaml").write_text("test")

        result = search_files.invoke({"directory_path": str(tmp_path), "pattern": "config.yaml"})
        assert "config.yaml" in result
        assert "other.yaml" not in result


@pytest.mark.unit
@pytest.mark.xdist_group(name="testfilesystemtoolschemas")
class TestFilesystemToolSchemas:
    """Test filesystem tool schemas"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_read_file_schema(self):
        """Test read_file has proper schema"""
        assert read_file.name == "read_file"
        assert read_file.description is not None
        schema = read_file.args_schema.model_json_schema()
        assert "file_path" in str(schema)
        assert "max_bytes" in str(schema)

    def test_list_directory_schema(self):
        """Test list_directory has proper schema"""
        assert list_directory.name == "list_directory"
        assert list_directory.description is not None
        schema = list_directory.args_schema.model_json_schema()
        assert "directory_path" in str(schema)
        assert "show_hidden" in str(schema)

    def test_search_files_schema(self):
        """Test search_files has proper schema"""
        assert search_files.name == "search_files"
        assert search_files.description is not None
        schema = search_files.args_schema.model_json_schema()
        assert "directory_path" in str(schema)
        assert "pattern" in str(schema)
        assert "max_results" in str(schema)
