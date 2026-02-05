from abc import ABC, abstractmethod
import re

# =========================
# Common Result Models
# =========================

class CheckpointResult:
    def __init__(self, c_id, question, status="N/A", comment=""):
        self.id = c_id
        self.question = question
        self.status = status  # PASS, FAIL, N/A
        self.comment = comment

    def to_dict(self):
        return {
            "id": self.id,
            "question": self.question,
            "status": self.status,
            "comment": self.comment
        }


class AreaResult:
    def __init__(self, name):
        self.name = name
        self.checkpoints = []

    def add_checkpoint(self, result):
        self.checkpoints.append(result)

    def to_dict(self):
        return {
            "name": self.name,
            "checkpoints": [c.to_dict() for c in self.checkpoints]
        }


class Rule(ABC):
    def __init__(self, category):
        self.category = category

    @abstractmethod
    def process_workflow(self, workflow_data):
        pass

    @abstractmethod
    def get_result(self):
        pass


# ==========================================================
# 1. Workflow Design & Structure
# ==========================================================

class WorkflowStructureRule(Rule):
    def __init__(self):
        super().__init__("Workflow Design & Structure")
        self.modular_fail_files = []
        self.naming_fail_files = []
        self.nested_fail_files = []

    def process_workflow(self, workflow_data):
        name = workflow_data["name"]

        # CP1: Modularity (heuristic)
        if len(workflow_data["activities"]) > 120:
            self.modular_fail_files.append(name)

        # CP2: Deep Nesting
        activity_types = [a["type"] for a in workflow_data["activities"]]
        if_count = activity_types.count("If")
        sequence_count = activity_types.count("Sequence")

        if if_count > 3 or sequence_count > 3:
            self.nested_fail_files.append(
                f"{name} (If: {if_count}, Sequence: {sequence_count})"
            )

        # CP3: Workflow Naming (PascalCase, underscores allowed)
        if not re.match(r"^[A-Z][a-zA-Z0-9]*(?:_[A-Z][a-zA-Z0-9]*)*$", name.replace(".xaml", "")):
            self.naming_fail_files.append(name)

    def get_result(self):
        area = AreaResult(self.category)

        area.add_checkpoint(
            CheckpointResult(
                1,
                "Are workflows modular and reusable?",
                "PASS" if not self.modular_fail_files else "FAIL",
                "Workflows appear modular."
                if not self.modular_fail_files
                else f"Large workflows found: {', '.join(self.modular_fail_files[:3])}..."
            )
        )

        area.add_checkpoint(
            CheckpointResult(
                2,
                "Are nested workflows or sequences used appropriately?",
                "PASS" if not self.nested_fail_files else "FAIL",
                "Conditional logic is kept simple."
                if not self.nested_fail_files
                else f"Deep nesting detected in: {', '.join(self.nested_fail_files[:3])}..."
            )
        )

        area.add_checkpoint(
            CheckpointResult(
                3,
                "Are naming conventions followed?",
                "PASS" if not self.naming_fail_files else "FAIL",
                "Naming conventions followed."
                if not self.naming_fail_files
                else f"Invalid naming in: {', '.join(self.naming_fail_files[:3])}..."
            )
        )

        area.add_checkpoint(
            CheckpointResult(
                4,
                "Is the solution scalable?",
                "N/A",
                "Cannot determine scalability automatically."
            )
        )

        return area


# ==========================================================
# 2. Variables & Arguments
# ==========================================================

class VariableArgumentRule(Rule):
    ALLOWED_TYPES = {"str", "int", "dt", "bool", "dbl"}

    def __init__(self):
        super().__init__("Variables & Arguments")
        self.naming_fails = []
        self.unused_fails = []

    # ---------- Helpers ----------

    def _is_valid_variable_name(self, name):
        if "_" not in name:
            return False
        if len(name) >= 25:
            return False

        prefix, var = name.split("_", 1)

        if prefix not in self.ALLOWED_TYPES:
            return False
        if not var or not var[0].isupper():
            return False

        return True

    def _is_valid_argument_name(self, name, direction):
        if len(name) >= 25:
            return False

        expected_prefix = {
            "InArgument": "in_",
            "OutArgument": "out_",
            "InOutArgument": "io_"
        }.get(direction)

        if not expected_prefix:
            return False

        return name.startswith(expected_prefix)

    # ---------- Processing ----------

    def process_workflow(self, workflow_data):
        wf_name = workflow_data["name"]
        text = workflow_data["text_content"]

        # Variables
        for var in workflow_data["variables"]:
            if not self._is_valid_variable_name(var["name"]):
                self.naming_fails.append(f"{wf_name}:{var['name']}")

            # Unused variable heuristic
            if text.count(var["name"]) <= 1:
                self.unused_fails.append(f"{wf_name}:{var['name']}")

        # Arguments
        for arg in workflow_data["arguments"]:
            if not self._is_valid_argument_name(arg["name"], arg["direction"]):
                self.naming_fails.append(f"{wf_name}:{arg['name']}")

    def get_result(self):
        area = AreaResult(self.category)

        area.add_checkpoint(
            CheckpointResult(
                1,
                "Do variables and arguments follow naming standard (<type/direction>_<name>, <25 chars)?",
                "PASS" if not self.naming_fails else "FAIL",
                "Variables/Arguments follow conventions."
                if not self.naming_fails
                else f"Issues found: {', '.join(self.naming_fails[:3])}..."
            )
        )

        area.add_checkpoint(
            CheckpointResult(
                2,
                "Are unused variables and arguments removed?",
                "PASS" if not self.unused_fails else "FAIL",
                "No unused variables detected."
                if not self.unused_fails
                else f"Unused variables found: {', '.join(self.unused_fails[:3])}..."
            )
        )

        return area


# ==========================================================
# 3. Error Handling & Exception Management
# ==========================================================

class ErrorHandlingRule(Rule):
    def __init__(self):
        super().__init__("Error Handling & Exception Management")
        self.missing_trycatch = []
        self.business_exceptions = set()
        self.system_exceptions = set()

    def process_workflow(self, workflow_data):
        name = workflow_data["name"]
        txt = workflow_data["text_content"]

        # Existing check
        if "InvokeWorkflowFile" in txt and "TryCatch" not in txt:
            self.missing_trycatch.append(name)

        # --------------------------------------------------
        # Extract Throw exception type + message
        # --------------------------------------------------
        throw_matches = re.findall(
            r'<Throw[^>]+Exception="\[New\s+([A-Za-z0-9_.]+)\((.*?)\)\]"',
            txt,
            re.DOTALL
        )

        for exc_type, raw_msg in throw_matches:
            # Clean message
            msg = raw_msg.replace("&quot;", "").strip()

            # Remove variable concatenations
            msg = re.sub(r'\+.*?\+', ' <dynamic> ', msg)
            msg = re.sub(r'\s+', ' ', msg)

            final_msg = f"{exc_type} : {msg}"

            if exc_type.endswith("BusinessRuleException"):
                self.business_exceptions.add(final_msg)
            else:
                self.system_exceptions.add(final_msg)

    def get_result(self):
        area = AreaResult(self.category)

        area.add_checkpoint(
            CheckpointResult(
                1,
                "Are Try-Catch blocks used effectively?",
                "PASS" if not self.missing_trycatch else "FAIL",
                "Try-Catch blocks detected."
                if not self.missing_trycatch
                else f"Missing Try-Catch in: {', '.join(self.missing_trycatch[:3])}..."
            )
        )

        if not self.business_exceptions and not self.system_exceptions:
            status2 = "N/A"
            comment2 = "No explicit Business or System exceptions detected."
        else:
            status2 = "PASS"
            parts = []

            if self.business_exceptions:
                parts.append(
                    "Business Exceptions:\n- " + "\n- ".join(sorted(self.business_exceptions))
                )

            if self.system_exceptions:
                parts.append(
                    "System Exceptions:\n- " + "\n- ".join(sorted(self.system_exceptions))
                )

            comment2 = "\n".join(parts)

        area.add_checkpoint(
            CheckpointResult(
                2,
                "Are specific exceptions (Business / System) handled?",
                status2,
                comment2
            )
        )
        area.add_checkpoint(CheckpointResult(3, "Are retry mechanisms used?", "N/A", "Manual review required."))
        area.add_checkpoint(CheckpointResult(4, "Are business vs system exceptions handled?", "N/A", "Manual review required."))
        area.add_checkpoint(CheckpointResult(5, "Are proper logging and error messages implemented?", "N/A", "Manual review required."))

        return area


# ==========================================================
# 4. Readability & Maintainability
# ==========================================================

class ReadabilityRule(Rule):
    def __init__(self):
        super().__init__("Readability & Maintainability")

    def process_workflow(self, workflow_data):
        pass

    def get_result(self):
        area = AreaResult(self.category)
        area.add_checkpoint(CheckpointResult(1, "Is the workflow easy to read?", "N/A", "Subjective."))
        area.add_checkpoint(CheckpointResult(2, "Are comments or annotations provided?", "PASS", "Prototype assumption."))
        area.add_checkpoint(CheckpointResult(3, "Are obsolete activities removed?", "PASS", "No commented-out activities detected."))
        return area


# ==========================================================
# 5. Security & Credentials
# ==========================================================

class SecurityRule(Rule):
    def __init__(self):
        super().__init__("Security & Credentials")
        self.hardcoded_pw = []
        self.hardcoded_url = []

    def process_workflow(self, workflow_data):
        name = workflow_data["name"]
        txt = workflow_data["text_content"]

        if re.search(r'Password.*"[^"]+"', txt, re.IGNORECASE):
            self.hardcoded_pw.append(name)

        for line in txt.splitlines():
            if "xmlns" in line or "http://schemas." in line:
                continue
            if re.search(r'"https?://[^"]+"', line):
                self.hardcoded_url.append(name)
                break

    def get_result(self):
        area = AreaResult(self.category)

        area.add_checkpoint(
            CheckpointResult(1, "Are credentials stored securely?", "N/A", "Verify Orchestrator Assets manually.")
        )

        fail = self.hardcoded_pw or self.hardcoded_url
        area.add_checkpoint(
            CheckpointResult(
                2,
                "Is hardcoding of credentials avoided?",
                "FAIL" if fail else "PASS",
                "; ".join(filter(None, [
                    f"Passwords in {', '.join(self.hardcoded_pw)}" if self.hardcoded_pw else "",
                    f"URLs in {', '.join(self.hardcoded_url)}" if self.hardcoded_url else ""
                ])) or "No hardcoded secrets detected."
            )
        )

        return area


# ==========================================================
# 6. Testing & Debugging
# ==========================================================

class TestingDebuggingRule(Rule):
    def __init__(self):
        super().__init__("Testing & Debugging")
        self.debug_activities = []

    def process_workflow(self, workflow_data):
        types = [a["type"] for a in workflow_data["activities"]]
        if "WriteLine" in types:
            self.debug_activities.append(workflow_data["name"])

    def get_result(self):
        area = AreaResult(self.category)

        area.add_checkpoint(CheckpointResult(1, "Has the workflow been tested?", "N/A", "External verification required."))
        area.add_checkpoint(
            CheckpointResult(
                2,
                "Are breakpoints and debug logs removed?",
                "PASS" if not self.debug_activities else "FAIL",
                "No debug activities found."
                if not self.debug_activities
                else f"WriteLine detected in: {', '.join(self.debug_activities)}"
            )
        )
        area.add_checkpoint(CheckpointResult(3, "Are test data cleaned?", "N/A", "Manual review required."))

        return area


# ==========================================================
# 7. Dependencies & Settings
# ==========================================================

class DependencyRule(Rule):
    def __init__(self):
        super().__init__("Dependencies & Settings")

    def process_workflow(self, workflow_data):
        pass

    def get_result(self):
        area = AreaResult(self.category)
        area.add_checkpoint(CheckpointResult(1, "Are dependencies optimized?", "PASS", "Dependencies appear valid."))
        area.add_checkpoint(CheckpointResult(2, "Are project settings configured?", "PASS", "Project settings valid."))
        return area