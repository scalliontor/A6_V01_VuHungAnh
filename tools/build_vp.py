"""Compile and run the installed Visual Paradigm Open API, then validate .vpp."""
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
APP = Path("/Applications/Visual Paradigm.app/Contents/Resources/app")
JRE = APP.parent / "jre.bundle/Contents/Home/bin"
PLUGIN = ROOT / "tools/vp_plugin"
INSTALL = Path.home() / "Library/Application Support/VisualParadigm/plugins/ptit.assignment06.multimodal"
CLASSPATH = ":".join([str(PLUGIN / "classes")] +
    [str(path) for folder in ("lib", "ormlib") for path in (APP / folder).glob("*.jar")] + [str(APP / "bin")])


def main():
    INSTALL.parent.mkdir(parents=True, exist_ok=True)
    created = False
    if INSTALL.exists() and INSTALL.resolve() != PLUGIN.resolve():
        raise RuntimeError(f"Plugin ID already installed elsewhere: {INSTALL}")
    if not INSTALL.exists():
        INSTALL.symlink_to(PLUGIN, target_is_directory=True)
        created = True
    try:
        with tempfile.TemporaryDirectory(prefix="assignment06_vp_") as folder:
            temp = Path(folder)
            with zipfile.ZipFile(APP / "lib/openapi.jar") as archive:
                archive.extractall(temp / "api")
            (PLUGIN / "classes").mkdir(exist_ok=True)
            subprocess.run([str(JRE / "javac"), "-encoding", "UTF-8", "-cp", str(temp / "api"),
                "-d", str(PLUGIN / "classes"), str(PLUGIN / "Assignment06Builder.java")], check=True)
            seed = temp / "seed.vpp"
            shutil.copy2(APP / "resources/BaggageSchemas.vpp", seed)
            cmd = [str(JRE / "java"), "-Xmx1536m", "-Dfile.encoding=UTF-8", "-Djava.awt.headless=true",
                "-Dptit.assignment.root=" + str(ROOT), "-cp", CLASSPATH, "com.vp.cmd.Plugin",
                "-project", str(seed), "-upgrade-project", "-pluginid", "ptit.assignment06.multimodal"]
            log = ROOT / "tools/vp_build.log"
            with log.open("w") as output:
                subprocess.run(cmd, cwd=APP / "bin", stdout=output, stderr=subprocess.STDOUT, check=True)
            if "ASSIGNMENT06_BUILD_SUCCESS" not in log.read_text(errors="replace"):
                raise RuntimeError("Visual Paradigm plugin did not complete; inspect tools/vp_build.log")
        project = ROOT / "Assignment06_V01_Multimodal_Search.vpp"
        with sqlite3.connect(project) as db:
            diagrams = dict(db.execute("SELECT NAME, DIAGRAM_TYPE FROM DIAGRAM"))
            expected = {
                "01 - Use Case - Multimodal Search": "UseCaseDiagram",
                "02 - Class - Three-Layer Architecture": "ClassDiagram",
                "03 - Sequence - Voice Product Search": "InteractionDiagram",
            }
            if diagrams != expected:
                raise RuntimeError(f"Unexpected editable diagrams: {diagrams}")
            classes = list(db.execute(
                "SELECT c.ID, c.NAME, c.DEFINITION FROM MODEL_ELEMENT c "
                "JOIN MODEL_ELEMENT p ON c.PARENT_ID = p.ID "
                "WHERE c.MODEL_TYPE = 'Class' AND p.MODEL_TYPE = 'Package' "
                "AND p.NAME IN ('Presentation Layer', 'Application / Intelligence Layer', 'Data Layer')"
            ))
        if len(classes) != 16:
            raise RuntimeError(f"Expected 16 architecture classes, found {len(classes)}")
        for _class_id, name, definition in classes:
            text = definition.decode("utf-8", errors="replace")
            if "Attribute {" not in text or "Operation {" not in text:
                raise RuntimeError(f"Class {name} is missing an attribute or operation compartment")
        with sqlite3.connect(project) as db:
            class_diagram_id = db.execute(
                "SELECT ID FROM DIAGRAM WHERE NAME = '02 - Class - Three-Layer Architecture'"
            ).fetchone()[0]
            dependency_rows = list(db.execute(
                "SELECT m.DEFINITION FROM DIAGRAM_ELEMENT e "
                "JOIN MODEL_ELEMENT m ON m.ID = e.MODEL_ELEMENT_ID "
                "WHERE e.DIAGRAM_ID = ? AND m.MODEL_TYPE = 'Dependency'",
                (class_diagram_id,),
            ))
        if len(dependency_rows) != 15:
            raise RuntimeError(f"Expected 15 class dependencies, found {len(dependency_rows)}")
        class_names_by_id = {class_id: name for class_id, name, _definition in classes}
        linked_class_ids = set()
        for (definition,) in dependency_rows:
            text = definition.decode("utf-8", errors="replace")
            linked_class_ids.update(re.findall(r"(?:from|to)Model=<[^:>]+:([^>]+)>", text))
        missing_links = set(class_names_by_id) - linked_class_ids
        if missing_links:
            missing_names = [class_names_by_id[class_id] for class_id in missing_links]
            raise RuntimeError(f"Architecture classes without relationships: {missing_names}")
        for stem in ("01_use_case", "02_three_layer_architecture", "03_sequence_voice"):
            for ext in ("png", "svg"):
                if not (ROOT / "diagrams" / f"{stem}.{ext}").is_file():
                    raise RuntimeError(f"Missing export: {stem}.{ext}")
        print(f"Validated {project.name}: {len(diagrams)} editable Visual Paradigm diagrams, "
              f"including {len(classes)} classes with attributes and operations, "
              f"plus {len(dependency_rows)} class-to-class dependencies.")
    finally:
        if created and INSTALL.is_symlink():
            INSTALL.unlink()


if __name__ == "__main__":
    main()
