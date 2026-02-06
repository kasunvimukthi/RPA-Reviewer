import os
import json
import xml.etree.ElementTree as ET
import re
from .rules import (
    WorkflowStructureRule, VariableArgumentRule, ErrorHandlingRule,
    ReadabilityRule, SecurityRule, TestingDebuggingRule, DependencyRule
)
from .utils import stripped_tag


class ProjectAnalyzer:
    def __init__(self, project_path, active_rules=None, include_framework=True):
        self.project_path = project_path
        self.include_framework = include_framework
        
        # REFramework default workflows list
        self.framework_files = {
            "Main.xaml",
            "Process.xaml",
            "InitAllSettings.xaml",
            "InitAllApplications.xaml",
            "CloseAllApplications.xaml",
            "KillAllProcesses.xaml",
            "GetTransactionData.xaml",
            "SetTransactionStatus.xaml",
            "RetryCurrentTransaction.xaml",
            "TakeScreenshot.xaml"
        }

        all_rules = [
            WorkflowStructureRule(),
            VariableArgumentRule(),
            ErrorHandlingRule(),
            ReadabilityRule(),
            SecurityRule(),
            TestingDebuggingRule(),
            DependencyRule()
        ]

        if active_rules:
            self.rules = [r for r in all_rules if r.category in active_rules]
        else:
            self.rules = all_rules

    def analyze(self):
        # -------------------------------------------------
        # Check for Breakpoints in .local/ProjectSettings.json
        # -------------------------------------------------
        settings_path = os.path.join(self.project_path, ".local", "ProjectSettings.json")
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    settings_data = json.load(f)
                
                bp_str = settings_data.get("ProjectBreakpoints")
                if bp_str:
                    bp_data = json.loads(bp_str)
                    bp_values = bp_data.get("Value", {})
                    
                    for rule in self.rules:
                        if isinstance(rule, TestingDebuggingRule):
                            for xaml_path, bp_list in bp_values.items():
                                if bp_list:
                                    # Extract activity names for enabled breakpoints
                                    active_bps = [bp.get("ActivityName", "Unknown") for bp in bp_list if bp.get("IsEnabled", True)]
                                    if active_bps:
                                        rule.breakpoints[xaml_path] = active_bps
            except Exception as e:
                print(f"Error reading ProjectSettings.json for breakpoints: {e}")

        # -------------------------------------------------
        # Get Project Dependencies from project.json
        # -------------------------------------------------
        project_json_path = os.path.join(self.project_path, "project.json")
        if os.path.exists(project_json_path):
            try:
                with open(project_json_path, "r", encoding="utf-8") as f:
                    project_data = json.load(f)
                
                dependencies = project_data.get("dependencies", {})
                if dependencies:
                    for rule in self.rules:
                        if isinstance(rule, DependencyRule):
                            rule.project_dependencies = dependencies
            except Exception as e:
                print(f"Error reading project.json: {e}")

        # Remove old .local/AllDependencies.json logic as requested by user
        # (It's gone in this version)

        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith(".xaml"):
                    # Check if we should skip framework files
                    if not self.include_framework and file in self.framework_files:
                        print(f"Skipping framework file: {file}")
                        continue
                        
                    self._analyze_file(os.path.join(root, file))

        return [rule.get_result().to_dict() for rule in self.rules]

    def _analyze_file(self, file_path):
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            with open(file_path, "r", encoding="utf-8") as f:
                text_content = f.read()

            filename = os.path.basename(file_path)

            # -------------------------------------------------
            # Extract Variables
            # -------------------------------------------------
            variables = []
            for elem in root.iter():
                if "Variables" in stripped_tag(elem.tag):
                    for var_elem in elem:
                        if "Variable" in stripped_tag(var_elem.tag):
                            name = (
                                var_elem.attrib.get("Name")
                                or var_elem.attrib.get("{http://schemas.microsoft.com/winfx/2006/xaml}Name")
                            )
                            if name:
                                variables.append({
                                    "name": name,
                                    "type": var_elem.attrib.get("TypeArguments")
                                })

            # -------------------------------------------------
            # Extract Arguments
            # -------------------------------------------------
            arguments = []
            for members in root.iter():
                if "Members" in stripped_tag(members.tag):
                    for prop in members:
                        if "Property" in stripped_tag(prop.tag):
                            name = prop.attrib.get("Name")
                            type_attr = prop.attrib.get("Type")

                            direction = "InArgument"
                            if "OutArgument" in str(type_attr):
                                direction = "OutArgument"
                            elif "InOutArgument" in str(type_attr):
                                direction = "InOutArgument"

                            if name:
                                arguments.append({
                                    "name": name,
                                    "direction": direction
                                })

            # -------------------------------------------------
            # Extract Activities (DisplayName-based – correct)
            # -------------------------------------------------
            activities = []
            for elem in root.iter():
                display_name = elem.attrib.get("DisplayName")
                if display_name:
                    activities.append({
                        "type": stripped_tag(elem.tag),
                        "display_name": display_name
                    })

            # -------------------------------------------------
            # Extract USED variable / argument names
            # -------------------------------------------------
            used_names = set()

            for elem in root.iter():
                tag = stripped_tag(elem.tag)

                # C# expressions
                if tag in {"CSharpReference", "CSharpValue"} and elem.text:
                    used_names.update(
                        re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', elem.text)
                    )

                # VB expressions (future-proof)
                if tag in {"VisualBasicReference", "VisualBasicValue"} and elem.text:
                    used_names.update(
                        re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', elem.text)
                    )

            workflow_data = {
                "name": filename,
                "path": file_path,
                "variables": variables,
                "arguments": arguments,
                "activities": activities,
                "used_names": used_names,
                "text_content": text_content,
                "tree": tree
            }

            for rule in self.rules:
                rule.process_workflow(workflow_data)

        except ET.ParseError:
            print(f"Skipping {file_path}: Invalid XAML")
        except Exception as e:
            print(f"Error checking {file_path}: {e}")