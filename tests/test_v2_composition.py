# SPDX-License-Identifier: MIT
"""
Tests for AEGIS v2 composition root extraction.

DoD criteria from fase1-composition-root.md:
- [ ] Dado main.cpp de Actia, extraer: m1, m2, m3
- [ ] Detectar wiring: m1->m2, m2->m3
- [ ] Cada instancia tiene location exacta
- [ ] Cada wiring tiene call-site exacto
"""

from pathlib import Path

import pytest

# Test project path
ACTIA_PROJECT = Path("/home/jesusramos/Workspace/Actia Prueba Tecnica")


class TestCppCompositionExtractor:
    """Test suite for C++ composition root extraction."""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance."""
        from code_map.v2.composition import CppCompositionExtractor

        ext = CppCompositionExtractor()
        if not ext.is_available():
            pytest.skip("tree-sitter not available")
        return ext

    def test_extractor_available(self, extractor):
        """Verify tree-sitter is available."""
        assert extractor.is_available()

    def test_find_composition_roots(self, extractor):
        """Test finding main() as composition root."""
        main_cpp = ACTIA_PROJECT / "main.cpp"
        if not main_cpp.exists():
            pytest.skip("Actia project not found")

        roots = extractor.find_composition_roots(main_cpp)
        assert "main" in roots

    def test_extract_instances_dod(self, extractor):
        """
        DoD: Dado main.cpp de Actia, extraer: m1, m2, m3
        """
        main_cpp = ACTIA_PROJECT / "main.cpp"
        if not main_cpp.exists():
            pytest.skip("Actia project not found")

        root = extractor.extract(main_cpp)
        assert root is not None
        assert root.function_name == "main"

        # Check we extracted all three instances
        instance_names = {i.name for i in root.instances}
        assert "m1" in instance_names, f"m1 not found in {instance_names}"
        assert "m2" in instance_names, f"m2 not found in {instance_names}"
        assert "m3" in instance_names, f"m3 not found in {instance_names}"

    def test_instances_have_location(self, extractor):
        """
        DoD: Cada instancia tiene location exacta
        """
        main_cpp = ACTIA_PROJECT / "main.cpp"
        if not main_cpp.exists():
            pytest.skip("Actia project not found")

        root = extractor.extract(main_cpp)
        assert root is not None

        for instance in root.instances:
            assert instance.location is not None
            assert instance.location.line > 0
            assert instance.location.file_path == main_cpp.resolve()

        # Check specific line numbers from main.cpp:
        # Line 22: const auto m1 = createGeneratorModule();
        # Line 23: const auto m2 = createFilterModule({0x00, 0x01, 0x02});
        # Line 24: const auto m3 = createPrinterModule();
        m1 = root.get_instance("m1")
        m2 = root.get_instance("m2")
        m3 = root.get_instance("m3")

        assert m1 is not None
        assert m1.location.line == 22, f"m1 at line {m1.location.line}, expected 22"

        assert m2 is not None
        assert m2.location.line == 23, f"m2 at line {m2.location.line}, expected 23"

        assert m3 is not None
        assert m3.location.line == 24, f"m3 at line {m3.location.line}, expected 24"

    def test_instances_factory_detection(self, extractor):
        """Test factory function detection."""
        main_cpp = ACTIA_PROJECT / "main.cpp"
        if not main_cpp.exists():
            pytest.skip("Actia project not found")

        root = extractor.extract(main_cpp)
        assert root is not None

        m1 = root.get_instance("m1")
        assert m1 is not None
        assert m1.factory_name == "createGeneratorModule"
        assert m1.creation_pattern.value == "factory"

        m2 = root.get_instance("m2")
        assert m2 is not None
        assert m2.factory_name == "createFilterModule"

        m3 = root.get_instance("m3")
        assert m3 is not None
        assert m3.factory_name == "createPrinterModule"

    def test_extract_wiring_dod(self, extractor):
        """
        DoD: Detectar wiring: m1->m2, m2->m3
        """
        main_cpp = ACTIA_PROJECT / "main.cpp"
        if not main_cpp.exists():
            pytest.skip("Actia project not found")

        root = extractor.extract(main_cpp)
        assert root is not None

        # Should have exactly 2 wiring connections
        assert len(root.wiring) == 2, f"Expected 2 wiring, got {len(root.wiring)}"

        # Check m1 -> m2 wiring
        m1_to_m2 = None
        m2_to_m3 = None

        for w in root.wiring:
            if w.source == "m1" and w.target == "m2":
                m1_to_m2 = w
            elif w.source == "m2" and w.target == "m3":
                m2_to_m3 = w

        assert m1_to_m2 is not None, "Wiring m1->m2 not found"
        assert m1_to_m2.method == "setNext"

        assert m2_to_m3 is not None, "Wiring m2->m3 not found"
        assert m2_to_m3.method == "setNext"

    def test_wiring_has_location(self, extractor):
        """
        DoD: Cada wiring tiene call-site exacto
        """
        main_cpp = ACTIA_PROJECT / "main.cpp"
        if not main_cpp.exists():
            pytest.skip("Actia project not found")

        root = extractor.extract(main_cpp)
        assert root is not None

        for wiring in root.wiring:
            assert wiring.location is not None
            assert wiring.location.line > 0
            assert wiring.location.file_path == main_cpp.resolve()

        # Check specific line numbers from main.cpp:
        # Line 27: m1->setNext(m2.get());
        # Line 29: m2->setNext(m3.get());
        m1_to_m2 = None
        m2_to_m3 = None

        for w in root.wiring:
            if w.source == "m1" and w.target == "m2":
                m1_to_m2 = w
            elif w.source == "m2" and w.target == "m3":
                m2_to_m3 = w

        assert m1_to_m2 is not None
        assert m1_to_m2.location.line == 27, f"m1->m2 at line {m1_to_m2.location.line}, expected 27"

        assert m2_to_m3 is not None
        assert m2_to_m3.location.line == 29, f"m2->m3 at line {m2_to_m3.location.line}, expected 29"

    def test_extract_lifecycle(self, extractor):
        """Test lifecycle method extraction (start/stop)."""
        main_cpp = ACTIA_PROJECT / "main.cpp"
        if not main_cpp.exists():
            pytest.skip("Actia project not found")

        root = extractor.extract(main_cpp)
        assert root is not None

        # Check we extracted lifecycle calls
        # From main.cpp:
        # m3->start(); m2->start(); m1->start();
        # m1->stop(); m2->stop(); m3->stop();
        start_calls = [lc for lc in root.lifecycle if lc.method.value == "start"]
        stop_calls = [lc for lc in root.lifecycle if lc.method.value == "stop"]

        assert len(start_calls) == 3, f"Expected 3 start calls, got {len(start_calls)}"
        assert len(stop_calls) == 3, f"Expected 3 stop calls, got {len(stop_calls)}"

        # Check order of start calls (m3, m2, m1)
        start_instances = [lc.instance for lc in start_calls]
        assert start_instances == ["m3", "m2", "m1"], f"Start order: {start_instances}"

    def test_to_dict_serialization(self, extractor):
        """Test JSON serialization of composition root."""
        main_cpp = ACTIA_PROJECT / "main.cpp"
        if not main_cpp.exists():
            pytest.skip("Actia project not found")

        root = extractor.extract(main_cpp)
        assert root is not None

        data = root.to_dict()
        assert "instances" in data
        assert "wiring" in data
        assert "lifecycle" in data
        assert len(data["instances"]) >= 3
        assert len(data["wiring"]) >= 2


class TestModels:
    """Test the v2 data models."""

    def test_instance_info_str(self):
        """Test InstanceInfo string representation."""
        from code_map.v2.models import InstanceInfo, Location, CreationPattern

        loc = Location(file_path=Path("/test.cpp"), line=10)
        inst = InstanceInfo(
            name="m1",
            type_name="auto",
            actual_type="GeneratorModule",
            location=loc,
            creation_pattern=CreationPattern.FACTORY,
        )
        assert str(inst) == "m1: GeneratorModule"

    def test_wiring_info_str(self):
        """Test WiringInfo string representation."""
        from code_map.v2.models import WiringInfo, Location

        loc = Location(file_path=Path("/test.cpp"), line=20)
        wiring = WiringInfo(
            source="m1",
            target="m2",
            method="setNext",
            location=loc,
        )
        assert str(wiring) == "m1 --[setNext]--> m2"

    def test_location_str(self):
        """Test Location string representation."""
        from code_map.v2.models import Location

        loc = Location(file_path=Path("/test.cpp"), line=42)
        assert str(loc) == "/test.cpp:42"


# =============================================================================
# Python Composition Extractor Tests
# =============================================================================

# Python test project path
PYTHON_PIPELINE = Path(__file__).parent.parent / "test_projects" / "python_pipeline"


class TestPythonCompositionExtractor:
    """Test suite for Python composition root extraction."""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance."""
        from code_map.v2.composition import PythonCompositionExtractor

        ext = PythonCompositionExtractor()
        if not ext.is_available():
            pytest.skip("tree-sitter not available for Python")
        return ext

    def test_extractor_available(self, extractor):
        """Verify tree-sitter is available."""
        assert extractor.is_available()

    def test_language_id(self, extractor):
        """Test language identifier."""
        assert extractor.language_id == "python"

    def test_file_extensions(self, extractor):
        """Test supported file extensions."""
        assert ".py" in extractor.file_extensions

    def test_find_composition_roots(self, extractor):
        """Test finding main() as composition root."""
        main_py = PYTHON_PIPELINE / "main.py"
        if not main_py.exists():
            pytest.skip("Python test project not found")

        roots = extractor.find_composition_roots(main_py)
        assert "main" in roots, f"main not in {roots}"

    def test_extract_instances(self, extractor):
        """Test extracting instances from Python pipeline."""
        main_py = PYTHON_PIPELINE / "main.py"
        if not main_py.exists():
            pytest.skip("Python test project not found")

        root = extractor.extract(main_py)
        assert root is not None
        assert root.function_name == "main"

        # Check we extracted all three instances
        instance_names = {i.name for i in root.instances}
        assert "gen" in instance_names, f"gen not found in {instance_names}"
        assert "proc" in instance_names, f"proc not found in {instance_names}"
        assert "out" in instance_names, f"out not found in {instance_names}"

    def test_instances_have_location(self, extractor):
        """Test that instances have exact locations."""
        main_py = PYTHON_PIPELINE / "main.py"
        if not main_py.exists():
            pytest.skip("Python test project not found")

        root = extractor.extract(main_py)
        assert root is not None

        for instance in root.instances:
            assert instance.location is not None
            assert instance.location.line > 0
            assert instance.location.file_path == main_py.resolve()

    def test_instances_type_detection(self, extractor):
        """Test type detection for direct instantiation."""
        main_py = PYTHON_PIPELINE / "main.py"
        if not main_py.exists():
            pytest.skip("Python test project not found")

        root = extractor.extract(main_py)
        assert root is not None

        gen = root.get_instance("gen")
        assert gen is not None
        assert gen.actual_type == "Generator"

        proc = root.get_instance("proc")
        assert proc is not None
        assert proc.actual_type == "Processor"

        out = root.get_instance("out")
        assert out is not None
        assert out.actual_type == "Output"

    def test_extract_wiring(self, extractor):
        """Test wiring detection: gen->proc, proc->out."""
        main_py = PYTHON_PIPELINE / "main.py"
        if not main_py.exists():
            pytest.skip("Python test project not found")

        root = extractor.extract(main_py)
        assert root is not None

        # Should have exactly 2 wiring connections
        assert len(root.wiring) >= 2, f"Expected >= 2 wiring, got {len(root.wiring)}"

        # Check gen -> proc wiring
        gen_to_proc = None
        proc_to_out = None

        for w in root.wiring:
            if w.source == "gen" and w.target == "proc":
                gen_to_proc = w
            elif w.source == "proc" and w.target == "out":
                proc_to_out = w

        assert gen_to_proc is not None, "Wiring gen->proc not found"
        assert gen_to_proc.method == "set_next"

        assert proc_to_out is not None, "Wiring proc->out not found"
        assert proc_to_out.method == "set_next"

    def test_wiring_has_location(self, extractor):
        """Test that wiring has exact call-site locations."""
        main_py = PYTHON_PIPELINE / "main.py"
        if not main_py.exists():
            pytest.skip("Python test project not found")

        root = extractor.extract(main_py)
        assert root is not None

        for wiring in root.wiring:
            assert wiring.location is not None
            assert wiring.location.line > 0
            assert wiring.location.file_path == main_py.resolve()

    def test_extract_lifecycle(self, extractor):
        """Test lifecycle method extraction (start/stop)."""
        main_py = PYTHON_PIPELINE / "main.py"
        if not main_py.exists():
            pytest.skip("Python test project not found")

        root = extractor.extract(main_py)
        assert root is not None

        # Check we extracted lifecycle calls
        start_calls = [lc for lc in root.lifecycle if lc.method.value == "start"]
        stop_calls = [lc for lc in root.lifecycle if lc.method.value == "stop"]

        assert len(start_calls) >= 1, f"Expected >= 1 start calls, got {len(start_calls)}"
        assert len(stop_calls) >= 1, f"Expected >= 1 stop calls, got {len(stop_calls)}"

    def test_to_dict_serialization(self, extractor):
        """Test JSON serialization of composition root."""
        main_py = PYTHON_PIPELINE / "main.py"
        if not main_py.exists():
            pytest.skip("Python test project not found")

        root = extractor.extract(main_py)
        assert root is not None

        data = root.to_dict()
        assert "instances" in data
        assert "wiring" in data
        assert "lifecycle" in data
        assert len(data["instances"]) >= 3


# =============================================================================
# TypeScript Composition Extractor Tests
# =============================================================================

# TypeScript test project path
TS_PIPELINE = Path(__file__).parent.parent / "test_projects" / "ts_pipeline"


class TestTypeScriptCompositionExtractor:
    """Test suite for TypeScript composition root extraction."""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance."""
        from code_map.v2.composition import TypeScriptCompositionExtractor

        ext = TypeScriptCompositionExtractor()
        if not ext.is_available():
            pytest.skip("tree-sitter not available for TypeScript")
        return ext

    def test_extractor_available(self, extractor):
        """Verify tree-sitter is available."""
        assert extractor.is_available()

    def test_language_id(self, extractor):
        """Test language identifier."""
        assert extractor.language_id == "typescript"

    def test_file_extensions(self, extractor):
        """Test supported file extensions."""
        exts = extractor.file_extensions
        assert ".ts" in exts
        assert ".tsx" in exts
        assert ".js" in exts
        assert ".jsx" in exts

    def test_find_composition_roots(self, extractor):
        """Test finding main() as composition root."""
        index_ts = TS_PIPELINE / "src" / "index.ts"
        if not index_ts.exists():
            pytest.skip("TypeScript test project not found")

        roots = extractor.find_composition_roots(index_ts)
        assert "main" in roots, f"main not in {roots}"

    def test_extract_instances(self, extractor):
        """Test extracting instances from TypeScript pipeline."""
        index_ts = TS_PIPELINE / "src" / "index.ts"
        if not index_ts.exists():
            pytest.skip("TypeScript test project not found")

        root = extractor.extract(index_ts)
        assert root is not None
        assert root.function_name == "main"

        # Check we extracted all three instances
        instance_names = {i.name for i in root.instances}
        assert "gen" in instance_names, f"gen not found in {instance_names}"
        assert "proc" in instance_names, f"proc not found in {instance_names}"
        assert "out" in instance_names, f"out not found in {instance_names}"

    def test_instances_have_location(self, extractor):
        """Test that instances have exact locations."""
        index_ts = TS_PIPELINE / "src" / "index.ts"
        if not index_ts.exists():
            pytest.skip("TypeScript test project not found")

        root = extractor.extract(index_ts)
        assert root is not None

        for instance in root.instances:
            assert instance.location is not None
            assert instance.location.line > 0
            assert instance.location.file_path == index_ts.resolve()

    def test_instances_type_detection(self, extractor):
        """Test type detection for new keyword instantiation."""
        index_ts = TS_PIPELINE / "src" / "index.ts"
        if not index_ts.exists():
            pytest.skip("TypeScript test project not found")

        root = extractor.extract(index_ts)
        assert root is not None

        gen = root.get_instance("gen")
        assert gen is not None
        assert gen.actual_type == "Generator"

        proc = root.get_instance("proc")
        assert proc is not None
        assert proc.actual_type == "Processor"

        out = root.get_instance("out")
        assert out is not None
        assert out.actual_type == "Output"

    def test_extract_wiring(self, extractor):
        """Test wiring detection: gen->proc, proc->out."""
        index_ts = TS_PIPELINE / "src" / "index.ts"
        if not index_ts.exists():
            pytest.skip("TypeScript test project not found")

        root = extractor.extract(index_ts)
        assert root is not None

        # Should have exactly 2 wiring connections
        assert len(root.wiring) >= 2, f"Expected >= 2 wiring, got {len(root.wiring)}"

        # Check gen -> proc wiring
        gen_to_proc = None
        proc_to_out = None

        for w in root.wiring:
            if w.source == "gen" and w.target == "proc":
                gen_to_proc = w
            elif w.source == "proc" and w.target == "out":
                proc_to_out = w

        assert gen_to_proc is not None, "Wiring gen->proc not found"
        assert gen_to_proc.method == "setNext"

        assert proc_to_out is not None, "Wiring proc->out not found"
        assert proc_to_out.method == "setNext"

    def test_wiring_has_location(self, extractor):
        """Test that wiring has exact call-site locations."""
        index_ts = TS_PIPELINE / "src" / "index.ts"
        if not index_ts.exists():
            pytest.skip("TypeScript test project not found")

        root = extractor.extract(index_ts)
        assert root is not None

        for wiring in root.wiring:
            assert wiring.location is not None
            assert wiring.location.line > 0
            assert wiring.location.file_path == index_ts.resolve()

    def test_extract_lifecycle(self, extractor):
        """Test lifecycle method extraction (start/stop)."""
        index_ts = TS_PIPELINE / "src" / "index.ts"
        if not index_ts.exists():
            pytest.skip("TypeScript test project not found")

        root = extractor.extract(index_ts)
        assert root is not None

        # Check we extracted lifecycle calls
        start_calls = [lc for lc in root.lifecycle if lc.method.value == "start"]
        stop_calls = [lc for lc in root.lifecycle if lc.method.value == "stop"]

        assert len(start_calls) >= 1, f"Expected >= 1 start calls, got {len(start_calls)}"
        assert len(stop_calls) >= 1, f"Expected >= 1 stop calls, got {len(stop_calls)}"

    def test_to_dict_serialization(self, extractor):
        """Test JSON serialization of composition root."""
        index_ts = TS_PIPELINE / "src" / "index.ts"
        if not index_ts.exists():
            pytest.skip("TypeScript test project not found")

        root = extractor.extract(index_ts)
        assert root is not None

        data = root.to_dict()
        assert "instances" in data
        assert "wiring" in data
        assert "lifecycle" in data
        assert len(data["instances"]) >= 3


# =============================================================================
# Service Language Router Tests
# =============================================================================


class TestInstanceGraphServiceRouter:
    """Test the language router in InstanceGraphService."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        from code_map.v2.service import InstanceGraphService

        return InstanceGraphService(Path("/tmp"))

    def test_get_extractor_python(self, service):
        """Test Python extractor selection."""
        extractor = service._get_extractor(Path("test.py"))
        assert extractor is not None
        assert extractor.language_id == "python"

    def test_get_extractor_typescript(self, service):
        """Test TypeScript extractor selection."""
        for ext in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".mts"):
            extractor = service._get_extractor(Path(f"test{ext}"))
            assert extractor is not None, f"No extractor for {ext}"
            assert extractor.language_id == "typescript", f"Wrong extractor for {ext}"

    def test_get_extractor_cpp(self, service):
        """Test C++ extractor selection."""
        for ext in (".cpp", ".hpp", ".cc", ".h", ".cxx", ".hxx"):
            extractor = service._get_extractor(Path(f"test{ext}"))
            assert extractor is not None, f"No extractor for {ext}"
            assert extractor.language_id == "cpp", f"Wrong extractor for {ext}"

    def test_get_extractor_unsupported(self, service):
        """Test unsupported extension returns None."""
        extractor = service._get_extractor(Path("test.rs"))
        assert extractor is None

    def test_supported_extensions(self, service):
        """Test all supported extensions are returned."""
        exts = service.get_supported_extensions()
        # Python
        assert ".py" in exts
        # TypeScript/JavaScript
        assert ".ts" in exts
        assert ".tsx" in exts
        assert ".js" in exts
        assert ".jsx" in exts
        # C++
        assert ".cpp" in exts
        assert ".hpp" in exts
        assert ".h" in exts


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
