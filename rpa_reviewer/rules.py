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

        # CP2: Deep Nesting (UiPath-aware)

        if_count = 0
        sequence_count = 0

        for act in workflow_data["activities"]:
            act_type = act["type"]
            display = act["display_name"]

            if act_type == "If":
                if_count += 1

            # Count only meaningful sequences (ignore default containers)
            elif act_type == "Sequence" and not display.lower().startswith("sequence"):
                sequence_count += 1

        if if_count > 3 or sequence_count > 30:
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

    # ---------- Naming helpers ----------

    def _is_valid_variable_name(self, name):
        if "_" not in name or len(name) >= 25:
            return False

        prefix, var = name.split("_", 1)
        return prefix in self.ALLOWED_TYPES and var and var[0].isupper()

    def _is_valid_argument_name(self, name, direction):
        if len(name) >= 25:
            return False

        return {
            "InArgument": name.startswith("in_"),
            "OutArgument": name.startswith("out_"),
            "InOutArgument": name.startswith("io_")
        }.get(direction, False)

    # ---------- Processing ----------

    def process_workflow(self, workflow_data):
        wf_name = workflow_data["name"]
        used_names = workflow_data.get("used_names", set())

        # Variables
        for var in workflow_data["variables"]:
            var_name = var["name"]

            if not self._is_valid_variable_name(var_name):
                self.naming_fails.append(f"{wf_name}:{var_name}")

            if var_name not in used_names:
                self.unused_fails.append(f"{wf_name}:{var_name}")

        # Arguments
        for arg in workflow_data["arguments"]:
            arg_name = arg["name"]

            if not self._is_valid_argument_name(arg_name, arg["direction"]):
                self.naming_fails.append(f"{wf_name}:{arg_name}")

            if arg_name not in used_names:
                self.unused_fails.append(f"{wf_name}:{arg_name}")

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
                "No unused variables or arguments detected."
                if not self.unused_fails
                else f"Unused items found:\n" + "\n".join(self.unused_fails[:5])
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
        self.nested_trycatch = []
        self.empty_catch_blocks = []
        self.missing_throw_in_catch = []
        self.retry_mechanisms = []
        self.incorrect_business_exception_handling = []
        self.incorrect_system_exception_handling = []
        self.catch_without_logging = []
        self.has_trycatch_blocks = False
        self.business_exceptions = set()
        self.system_exceptions = set()

    def process_workflow(self, workflow_data):
        name = workflow_data["name"]
        txt = workflow_data["text_content"]

        # Rule 1: Invoke without Try-Catch
        if "InvokeWorkflowFile" in txt and "TryCatch" not in txt:
            self.missing_trycatch.append(name)

        # Rule 2: Nested TryCatch (TryCatch inside TryCatch)
        # Look for TryCatch blocks that contain another TryCatch
        trycatch_pattern = r'<TryCatch[^>]*>.*?</TryCatch>'
        trycatch_blocks = re.findall(trycatch_pattern, txt, re.DOTALL)
        
        # Track if TryCatch exists
        if "TryCatch" in txt:
            self.has_trycatch_blocks = True
        
        for block in trycatch_blocks:
            # Check if this TryCatch block contains another TryCatch
            if block.count("<TryCatch") > 1:
                self.nested_trycatch.append(name)
                break

        # Rule 3: Empty Catch Blocks
        # Pattern: <Catch> ... </Catch> where there's no activity inside
        catch_pattern = r'<Catch[^>]*>(.*?)</Catch>'
        catch_blocks = re.findall(catch_pattern, txt, re.DOTALL)
        for catch_content in catch_blocks:
            # Check if catch block is empty or only contains whitespace/metadata
            # Remove common metadata tags and whitespace
            cleaned = re.sub(r'<sap:WorkflowViewStateService\.ViewState>.*?</sap:WorkflowViewStateService\.ViewState>', '', catch_content, flags=re.DOTALL)
            cleaned = re.sub(r'<sap2010:WorkflowViewState\.IdRef>.*?</sap2010:WorkflowViewState\.IdRef>', '', cleaned)
            cleaned = cleaned.strip()
            
            # If no meaningful content remains, it's empty
            if not cleaned or cleaned.count('<') == 0:
                self.empty_catch_blocks.append(name)
                break

        # Rule 4: Catch Blocks without Throw Activity
        # Check if TryCatch exists and has Catch blocks without Throw
        if "TryCatch" in txt:
            for catch_content in catch_blocks:
                # Check if this catch block has a Throw activity
                if "Throw" not in catch_content and catch_content.strip():
                    # Make sure it's not an empty block (already caught by Rule 3)
                    cleaned = re.sub(r'<sap:WorkflowViewStateService\.ViewState>.*?</sap:WorkflowViewStateService\.ViewState>', '', catch_content, flags=re.DOTALL)
                    cleaned = re.sub(r'<sap2010:WorkflowViewState\.IdRef>.*?</sap2010:WorkflowViewState\.IdRef>', '', cleaned)
                    cleaned = cleaned.strip()
                    
                    if cleaned and cleaned.count('<') > 0:
                        self.missing_throw_in_catch.append(name)
                        break

        # Rule 5: Retry Mechanisms Detection
        # Check for Retry, DoWhile, and While activities
        retry_activities = []
        if "RetryScope" in txt or "ui:RetryScope" in txt or "<Retry" in txt:
            retry_activities.append("Retry")
        if "DoWhile" in txt or "ui:DoWhile" in txt:
            retry_activities.append("DoWhile")
        if "<While" in txt and "DoWhile" not in txt:
            retry_activities.append("While")
        
        
        if retry_activities:
            self.retry_mechanisms.append(f"{name} ({', '.join(retry_activities)})")

        # Rule 6: Business vs System Exception Handling in Catch Blocks
        # Check if catch blocks throw appropriate exceptions based on caught exception type
        # Pattern: <Catch x:TypeArguments="ExceptionType">...<Throw>...</Throw>...</Catch>
        catch_with_type_pattern = r'<Catch\s+x:TypeArguments="([^"]+)"[^>]*>(.*?)</Catch>'
        catch_with_types = re.findall(catch_with_type_pattern, txt, re.DOTALL)
        
        for exception_type, catch_content in catch_with_types:
            # Determine if this is a business or system exception based on the caught type
            is_business_catch = "BusinessRuleException" in exception_type
            is_system_catch = not is_business_catch and "Exception" in exception_type
            
            # Extract throw statements from the catch block
            # Pattern 1: Attribute-based Throw
            attr_throw_pattern = r'<Throw[^>]+Exception="\[New\s+([A-Za-z0-9_.]+)\('
            attr_throws = re.findall(attr_throw_pattern, catch_content)
            
            # Pattern 2: CSharpValue-based Throw
            csharp_throw_pattern = r'<CSharpValue[^>]*>\s*new\s+([A-Za-z0-9_.]+)\('
            csharp_throws = re.findall(csharp_throw_pattern, catch_content)
            
            all_throws = attr_throws + csharp_throws
            
            # Validate business exception handling
            if is_business_catch and all_throws:
                # Business catch should throw BusinessRuleException
                has_business_throw = any("BusinessRuleException" in throw_type for throw_type in all_throws)
                if not has_business_throw:
                    self.incorrect_business_exception_handling.append(
                        f"{name} (Catches {exception_type}, throws {', '.join(all_throws)})"
                    )
            
            # Validate system exception handling
            elif is_system_catch and all_throws:
                # System catch should throw system exception (not BusinessRuleException)
                has_business_throw = any("BusinessRuleException" in throw_type for throw_type in all_throws)
                if has_business_throw:
                    self.incorrect_system_exception_handling.append(
                        f"{name} (Catches {exception_type}, throws {', '.join(all_throws)})"
                    )

        # Rule 7: Logging in Catch Blocks
        # Check if catch blocks have logging activities (LogMessage, WriteLine, AddLogFields, etc.)
        # Pattern: <Catch ...>...</Catch>
        catch_pattern = r'<Catch[^>]*>(.*?)</Catch>'
        catch_blocks_content = re.findall(catch_pattern, txt, re.DOTALL)
        
        catch_without_log_count = 0
        for catch_content in catch_blocks_content:
            # Check for common logging activities
            has_logging = any([
                "LogMessage" in catch_content,
                "ui:LogMessage" in catch_content,
                "WriteLine" in catch_content,  # For debugging/logging
                "AddLogFields" in catch_content,
                "ui:AddLogFields" in catch_content,
                # Could also check for custom logging activities
            ])
            
            # Only count non-empty catch blocks
            # Remove metadata to check if it has actual activities
            cleaned = re.sub(r'<sap:WorkflowViewStateService\.ViewState>.*?</sap:WorkflowViewStateService\.ViewState>', '', catch_content, flags=re.DOTALL)
            cleaned = re.sub(r'<sap2010:WorkflowViewState\.IdRef>.*?</sap2010:WorkflowViewState\.IdRef>', '', cleaned)
            cleaned = cleaned.strip()
            
            # If catch block has content but no logging
            if cleaned and cleaned.count('<') > 0 and not has_logging:
                catch_without_log_count += 1
        
        if catch_without_log_count > 0:
            self.catch_without_logging.append(f"{name} ({catch_without_log_count} catch block(s) without logging)")



        # ==================================================
        # Pattern 1: Attribute-based Throw
        # <Throw Exception="[New BusinessRuleException("msg")]"/>
        # ==================================================
        attr_matches = re.findall(
            r'<Throw[^>]+Exception="\[New\s+([A-Za-z0-9_.]+)\((.*?)\)\]"',
            txt,
            re.DOTALL
        )

        # ==================================================
        # Pattern 2: CSharpValue-based Throw
        # <CSharpValue>new BusinessRuleException("msg")</CSharpValue>
        # ==================================================
        csharp_matches = re.findall(
            r'<CSharpValue[^>]*>\s*new\s+([A-Za-z0-9_.]+)\((.*?)\)\s*</CSharpValue>',
            txt,
            re.DOTALL
        )

        all_matches = attr_matches + csharp_matches

        for exc_type, raw_msg in all_matches:
            # Clean message
            msg = raw_msg.replace("&quot;", "").strip()

            # Remove concatenations / variables
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

        # CP 2: Nested TryCatch blocks
        area.add_checkpoint(
            CheckpointResult(
                2,
                "Are nested Try-Catch blocks avoided?",
                "PASS" if not self.nested_trycatch else "FAIL",
                "No nested Try-Catch blocks detected."
                if not self.nested_trycatch
                else f"Nested Try-Catch found in: {', '.join(self.nested_trycatch[:3])}..."
            )
        )

        # CP 3: Empty Catch blocks
        area.add_checkpoint(
            CheckpointResult(
                3,
                "Are all Catch blocks non-empty?",
                "PASS" if not self.empty_catch_blocks else "FAIL",
                "All Catch blocks have content."
                if not self.empty_catch_blocks
                else f"Empty Catch blocks found in: {', '.join(self.empty_catch_blocks[:3])}..."
            )
        )

        # CP 4: Throw Activity in Catch blocks
        area.add_checkpoint(
            CheckpointResult(
                4,
                "Do all Catch blocks contain Throw activities?",
                "PASS" if not self.missing_throw_in_catch else "FAIL",
                "All Catch blocks contain Throw activities."
                if not self.missing_throw_in_catch
                else f"Catch blocks without Throw found in: {', '.join(self.missing_throw_in_catch[:3])}..."
            )
        )

        # CP 5: Specific Exceptions (Business / System)
        if not self.business_exceptions and not self.system_exceptions:
            status2 = "N/A"
            comment2 = "No explicit Business or System exceptions detected."
        else:
            status2 = "PASS"
            lines = []

            if self.business_exceptions:
                lines.append("Business Exceptions:")
                for exc in sorted(self.business_exceptions):
                    lines.append(f"- {exc}")

            if self.system_exceptions:
                if lines:
                    lines.append("")  # blank line between sections
                lines.append("System Exceptions:")
                for exc in sorted(self.system_exceptions):
                    lines.append(f"- {exc}")

            comment2 = "\n".join(lines)

        area.add_checkpoint(
            CheckpointResult(
                5,
                "Are specific exceptions (Business / System) handled?",
                status2,
                comment2
            )
        )
        
        # CP 6: Retry Mechanisms
        area.add_checkpoint(
            CheckpointResult(
                6,
                "Are retry mechanisms used?",
                "PASS" if self.retry_mechanisms else "N/A",
                "\n".join(self.retry_mechanisms) if self.retry_mechanisms else "No retry mechanisms detected (Retry, DoWhile, While)."
            )
        )
        
        # CP 7: Business vs System Exception Handling
        has_errors = self.incorrect_business_exception_handling or self.incorrect_system_exception_handling
        
        if has_errors:
            error_lines = []
            if self.incorrect_business_exception_handling:
                error_lines.append("❌ Business exceptions not throwing BusinessRuleException:")
                for item in self.incorrect_business_exception_handling[:5]:
                    error_lines.append(f"  - {item}")
            
            if self.incorrect_system_exception_handling:
                if error_lines:
                    error_lines.append("")
                error_lines.append("❌ System exceptions throwing BusinessRuleException:")
                for item in self.incorrect_system_exception_handling[:5]:
                    error_lines.append(f"  - {item}")
            
            comment7 = "\n".join(error_lines)
            status7 = "FAIL"
        else:
            # Check if there are any catch blocks at all
            if self.has_trycatch_blocks:
                comment7 = "Exception handling appears correct (Business catches throw BusinessRuleException, System catches throw System exceptions)."
                status7 = "PASS"
            else:
                comment7 = "No TryCatch blocks found to validate."
                status7 = "N/A"
        
        area.add_checkpoint(CheckpointResult(7, "Are business vs system exceptions handled correctly?", status7, comment7))
        
        # CP 8: Logging in Catch Blocks
        area.add_checkpoint(
            CheckpointResult(
                8,
                "Are proper logging and error messages implemented in catch blocks?",
                "PASS" if not self.catch_without_logging else "FAIL",
                "All catch blocks have logging activities."
                if not self.catch_without_logging
                else "Catch blocks without logging:\n" + "\n".join(self.catch_without_logging)
            )
        )

        return area


# ==========================================================
# 4. Readability & Maintainability
# ==========================================================

class ReadabilityRule(Rule):
    def __init__(self):
        super().__init__("Readability & Maintainability")
        self.workflows_with_annotations = []
        self.workflows_without_annotations = []
        self.annotations_map = {}
        self.activity_annotations = {}  # {wf_name: {'If': [notes], 'InvokeCode': [notes]}}
        self.missing_activity_annotations = {} # {wf_name: {'If': count, 'InvokeCode': count}}
        self.workflows_with_comments = []

    def process_workflow(self, workflow_data):
        name = workflow_data["name"]
        txt = workflow_data["text_content"]
        
        # Check for annotations in the workflow
        # UiPath annotations typically use sads:DebugSymbol.Symbol or Annotation tags
        has_annotations = any([
            "sads:DebugSymbol.Symbol" in txt,
            "<Annotation" in txt,
            "ui:Annotation" in txt,
            "AnnotationText=" in txt,
            # Check for DisplayName attributes which can serve as annotations
            'DisplayName="' in txt and not all(dn.startswith("Sequence") or dn.startswith("Flowchart") 
                                                for dn in txt.split('DisplayName="')[1:])
        ])

        # Extract actual annotation text line by line
        # Regex to find AnnotationText="some message"
        found_notes = re.findall(r'AnnotationText="([^"]*)"', txt)
        if found_notes:
            self.annotations_map[name] = [note.strip() for note in found_notes if note.strip()]
        
        if has_annotations:
            self.workflows_with_annotations.append(name)
        else:
            self.workflows_without_annotations.append(name)

        # Extraction for Checkpoint 2 (If and Invoke Code)
        self.activity_annotations[name] = {'If': [], 'InvokeCode': []}
        self.missing_activity_annotations[name] = {'If': 0, 'InvokeCode': 0}

        # Find If activities
        # Pattern to find <If ...> blocks - a bit tricky with nested ones, but we mostly care about attributes
        # Find all <If tags
        if_tags = re.findall(r'<If\b[^>]*>', txt)
        for tag in if_tags:
            note_match = re.search(r'AnnotationText="([^"]*)"', tag)
            if note_match:
                self.activity_annotations[name]['If'].append(note_match.group(1).strip())
            else:
                self.missing_activity_annotations[name]['If'] += 1

        # Find InvokeCode activities
        ic_tags = re.findall(r'<(?:ui:)?InvokeCode\b[^>]*>', txt)
        for tag in ic_tags:
            note_match = re.search(r'AnnotationText="([^"]*)"', tag)
            if note_match:
                self.activity_annotations[name]['InvokeCode'].append(note_match.group(1).strip())
            else:
                self.missing_activity_annotations[name]['InvokeCode'] += 1

        # Check for CommentOut activities
        if "<CommentOut" in txt or "<ui:CommentOut" in txt:
            self.workflows_with_comments.append(name)

    def get_result(self):
        area = AreaResult(self.category)
        
        # CP 1: Annotations for Readability
        comment_parts = []
        if self.workflows_with_annotations:
            comment_parts.append(f"✅ {len(self.workflows_with_annotations)} workflow(s) have annotations.")
            
            # Add line-by-line annotations
            for wf_name in self.workflows_with_annotations:
                notes = self.annotations_map.get(wf_name, [])
                if notes:
                    comment_parts.append(f"\n📌 Annotations in `{wf_name}`:")
                    for note in notes:
                        comment_parts.append(f"  - {note}")
        
        if self.workflows_without_annotations:
            comment_parts.append(f"\n❌ Workflows without annotations: {', '.join(self.workflows_without_annotations[:5])}{'...' if len(self.workflows_without_annotations) > 5 else ''}")

        area.add_checkpoint(
            CheckpointResult(
                1,
                "Are workflow-level annotations meaningful and present?",
                "PASS" if not self.workflows_without_annotations else "FAIL",
                "\n".join(comment_parts) if comment_parts else "No annotations detected."
            )
        )
        # CP 2: Activity-level Annotations
        activity_comment_parts = []
        total_missing_annotations = 0
        
        for wf_name, data in self.activity_annotations.items():
            wf_notes = []
            if data['If']:
                wf_notes.append(f"  - **If** Conditions:")
                for note in data['If']:
                    wf_notes.append(f"    - {note}")
            
            if data['InvokeCode']:
                wf_notes.append(f"  - **Invoke Code** Activities:")
                for note in data['InvokeCode']:
                    wf_notes.append(f"    - {note}")
            
            missing = self.missing_activity_annotations.get(wf_name, {})
            total_missing_wf = missing.get('If', 0) + missing.get('InvokeCode', 0)
            total_missing_annotations += total_missing_wf
            
            if wf_notes:
                activity_comment_parts.append(f"\n📌 Annotations in `{wf_name}`:")
                activity_comment_parts.extend(wf_notes)
            
            if total_missing_wf > 0:
                activity_comment_parts.append(f"  ⚠️ Missing annotations: {missing.get('If', 0)} If(s), {missing.get('InvokeCode', 0)} Invoke Code(s)")

        area.add_checkpoint(
            CheckpointResult(
                2,
                "Do If conditions and Invoke Code activities have annotations?",
                "PASS" if total_missing_annotations == 0 else "FAIL",
                "\n".join(activity_comment_parts) if activity_comment_parts else "No If or Invoke Code activities found."
            )
        )
        area.add_checkpoint(
            CheckpointResult(
                3,
                "Are obsolete activities removed?",
                "PASS" if not self.workflows_with_comments else "FAIL",
                "No commented-out activities detected." if not self.workflows_with_comments 
                else f"Commented-out activities found in: {', '.join(self.workflows_with_comments[:5])}{'...' if len(self.workflows_with_comments) > 5 else ''}"
            )
        )
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