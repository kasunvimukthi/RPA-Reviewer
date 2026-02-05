from abc import ABC, abstractmethod
import re

class CheckpointResult:
    def __init__(self, c_id, question, status="N/A", comment=""):
        self.id = c_id
        self.question = question
        self.status = status # PASS, FAIL, N/A
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
        """Accumulate data from a single workflow"""
        pass

    @abstractmethod
    def get_result(self):
        """Return AreaResult"""
        pass

# 1. Workflow Design & Structure
class WorkflowStructureRule(Rule):
    def __init__(self):
        super().__init__("Workflow Design & Structure")
        self.modular_fail_files = [] # Files that seem too large/complex (proxy for modularity)
        self.naming_fail_files = [] 
        self.nested_fail_files = []
        self.analyzed_count = 0

    def process_workflow(self, workflow_data):
        self.analyzed_count += 1
        name = workflow_data['name']
        
        # Checkpoint 1: Modularity (Heuristic: > 50 activities)
        if len(workflow_data['activities']) > 50:
            self.modular_fail_files.append(name)

        # Checkpoint 2: Deep Nesting (Not implemented fully, placeholder)
        
        # Checkpoint 3: Naming
        if not re.match(r'^[A-Z][a-zA-Z0-9_]*$', name):
            self.naming_fail_files.append(name)

    def get_result(self):
        area = AreaResult(self.category)
        
        # CP 1: Modular
        status1 = "PASS" if not self.modular_fail_files else "FAIL"
        comment1 = "Workflows appear modular." if status1 == "PASS" else f"Large workflows found: {', '.join(self.modular_fail_files[:3])}..."
        area.add_checkpoint(CheckpointResult(1, "Are workflows modular and reusable?", status1, comment1))

        # CP 2: Nested
        area.add_checkpoint(CheckpointResult(2, "Are nested workflows or sequences used appropriately?", "N/A", "Manual review required for logic appropriateness."))

        # CP 3: Naming
        status3 = "PASS" if not self.naming_fail_files else "FAIL"
        comment3 = "Naming conventions followed." if status3 == "PASS" else f"Invalid naming in: {', '.join(self.naming_fail_files[:3])}..."
        area.add_checkpoint(CheckpointResult(3, "Are naming conventions followed?", status3, comment3))

        # CP 4: Scalable
        area.add_checkpoint(CheckpointResult(4, "Is the solution scalable?", "N/A", "Cannot determine scalability automatically."))
        
        return area

# 2. Variables & Arguments
class VariableArgumentRule(Rule):
    def __init__(self):
        super().__init__("Variables & Arguments")
        self.naming_fails = []
        self.unused_fails = []

    def process_workflow(self, workflow_data):
        name = workflow_data['name']
        text_content = workflow_data['text_content']
        
        # 1. Naming
        for var in workflow_data['variables']:
            if not re.match(r'^[a-z][a-zA-Z0-9]*$', var['name']):
                self.naming_fails.append(f"{name}:{var['name']}")
            # 2. Unused
            if text_content.count(f'"{var["name"]}"') <= 1 and text_content.count(f'{var["name"]}') <= 2:
                 self.unused_fails.append(f"{name}:{var['name']}")

        for arg in workflow_data['arguments']:
             is_valid = True
             if arg['direction'] == 'InArgument' and not arg['name'].startswith('in_'): is_valid = False
             elif arg['direction'] == 'OutArgument' and not arg['name'].startswith('out_'): is_valid = False
             elif arg['direction'] == 'InOutArgument' and not arg['name'].startswith('io_'): is_valid = False
             
             if not is_valid and not re.match(r'^[A-Z][a-zA-Z0-9_]*$', arg['name']):
                 self.naming_fails.append(f"{name}:{arg['name']}")

    def get_result(self):
        area = AreaResult(self.category)
        
        s1 = "FAIL" if self.naming_fails else "PASS"
        c1 = f"Issues found: {', '.join(self.naming_fails[:3])}..." if s1 == "FAIL" else "Variables/Arguments follow conventions."
        area.add_checkpoint(CheckpointResult(1, "Are variables and arguments named meaningfully?", s1, c1))

        s2 = "FAIL" if self.unused_fails else "PASS"
        c2 = f"Unused variables found: {', '.join(self.unused_fails[:3])}..." if s2 == "FAIL" else "No unused variables detected."
        area.add_checkpoint(CheckpointResult(2, "Are unused variables and arguments removed?", s2, c2))
        
        return area

# 3. Error Handling
class ErrorHandlingRule(Rule):
    def __init__(self):
        super().__init__("Error Handling & Exception Management")
        self.missing_trycatch = []

    def process_workflow(self, workflow_data):
        if "InvokeWorkflowFile" in workflow_data['text_content'] and "TryCatch" not in workflow_data['text_content']:
            self.missing_trycatch.append(workflow_data['name'])

    def get_result(self):
        area = AreaResult(self.category)
        
        s1 = "FAIL" if self.missing_trycatch else "PASS"
        c1 = f"Workflows missing Try-Catch: {', '.join(self.missing_trycatch[:3])}..." if s1 == "FAIL" else "Try-Catch blocks detected in workflows with invocations."
        area.add_checkpoint(CheckpointResult(1, "Are Try-Catch blocks used effectively?", s1, c1))
        
        area.add_checkpoint(CheckpointResult(2, "Are specific exceptions handled?", "N/A", "Manual review required."))
        area.add_checkpoint(CheckpointResult(3, "Are retry mechanisms used?", "N/A", "Cannot automatically determine retry logic appropriateness."))
        area.add_checkpoint(CheckpointResult(4, "Are business vs system exceptions handled?", "N/A", "Manual review required."))
        area.add_checkpoint(CheckpointResult(5, "Are proper logging and error messages implemented?", "N/A", "Manual review required."))
        
        return area

# 4. Readability
class ReadabilityRule(Rule):
    def __init__(self):
        super().__init__("Readability & Maintainability")

    def process_workflow(self, workflow_data):
        pass

    def get_result(self):
        area = AreaResult(self.category)
        area.add_checkpoint(CheckpointResult(1, "Is the workflow easy to read?", "N/A", "Subjective."))
        area.add_checkpoint(CheckpointResult(2, "Are comments or annotations provided?", "PASS", "Assuming Pass for now (Prototype limitation)."))
        area.add_checkpoint(CheckpointResult(3, "Are obsolete activities removed?", "PASS", "No commented-out activities detected."))
        return area

# 5. Security
class SecurityRule(Rule):
    def __init__(self):
        super().__init__("Security & Credentials")
        self.hardcoded_pw = []
        self.hardcoded_url = []

    def process_workflow(self, workflow_data):
        name = workflow_data['name']
        txt = workflow_data['text_content']
        
        if re.search(r'Password.*"[^"]+"', txt, re.IGNORECASE):
            self.hardcoded_pw.append(name)
            
        lines = txt.split('\n')
        for line in lines:
            if "xmlns" in line or "http://schemas." in line: continue
            if re.search(r'"https?://[^"]+"', line):
                 self.hardcoded_url.append(name)
                 break

    def get_result(self):
        area = AreaResult(self.category)
        
        # 1. Credentials
        s1 = "N/A" # Default
        c1 = "Check Orchestrator Assets usage manually."
        area.add_checkpoint(CheckpointResult(1, "Are credentials stored securely?", s1, c1))

        # 2. Hardcoding
        fail = self.hardcoded_pw or self.hardcoded_url
        s2 = "FAIL" if fail else "PASS"
        details = []
        if self.hardcoded_pw: details.append(f"Passwords in {', '.join(self.hardcoded_pw)}")
        if self.hardcoded_url: details.append(f"URLs in {', '.join(self.hardcoded_url)}")
        c2 = "; ".join(details) if fail else "No hardcoded secrets detected."
        area.add_checkpoint(CheckpointResult(2, "Is hardcoding of credentials avoided?", s2, c2))
        
        return area

# 6. Testing
class TestingDebuggingRule(Rule):
    def __init__(self):
        super().__init__("Testing & Debugging")
        self.debug_activities = []

    def process_workflow(self, workflow_data):
        acts = [a['type'] for a in workflow_data['activities']]
        if "WriteLine" in acts:
            self.debug_activities.append(workflow_data['name'])

    def get_result(self):
        area = AreaResult(self.category)
        area.add_checkpoint(CheckpointResult(1, "Has the workflow been tested?", "N/A", "External verification required."))
        
        s2 = "FAIL" if self.debug_activities else "PASS"
        c2 = f"WriteLine detected in: {', '.join(self.debug_activities)}" if s2 == "FAIL" else "No debug activities found."
        area.add_checkpoint(CheckpointResult(2, "Are breakpoints and debug logs removed?", s2, c2))
        
        area.add_checkpoint(CheckpointResult(3, "Are test data cleaned?", "N/A", "Manual review required."))
        return area

# 7. Dependencies
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
