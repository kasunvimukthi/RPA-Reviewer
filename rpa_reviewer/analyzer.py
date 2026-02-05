import os
import json
import xml.etree.ElementTree as ET
from .rules import (
    WorkflowStructureRule, VariableArgumentRule, ErrorHandlingRule, 
    ReadabilityRule, SecurityRule, TestingDebuggingRule, DependencyRule
)
from .utils import stripped_tag, get_namespaces

class ProjectAnalyzer:
    def __init__(self, project_path, active_rules=None):
        self.project_path = project_path
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
            
        self.issues = []

    def analyze(self):
        print(f"Analyzing project at: {self.project_path}")
        
        project_json_path = os.path.join(self.project_path, "project.json")
        project_meta = {}
        if os.path.exists(project_json_path):
            try:
                with open(project_json_path, 'r', encoding='utf-8') as f:
                    project_meta = json.load(f)
            except Exception as e:
                print(f"Error reading project.json: {e}")

        for root, dirs, files in os.walk(self.project_path):
            for file in files:
                if file.endswith(".xaml"):
                   self._analyze_file(os.path.join(root, file), project_meta)
        
        # Collect Results
        results = []
        for rule in self.rules:
            results.append(rule.get_result().to_dict())
            
        return results

    def _analyze_file(self, file_path, project_meta):
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            with open(file_path, 'r', encoding='utf-8') as f:
                text_content = f.read()

            filename = os.path.basename(file_path)
            
            # Extract Variables
            variables = []
            for elem in root.iter():
                if "Variables" in stripped_tag(elem.tag):
                    for var_elem in elem:
                        if "Variable" in stripped_tag(var_elem.tag):
                            name = var_elem.attrib.get('Name') or var_elem.attrib.get('{http://schemas.microsoft.com/winfx/2006/xaml}Name')
                            if name:
                                variables.append({'name': name, 'type': var_elem.attrib.get('TypeArguments')})

            # Extract Arguments
            arguments = []
            for members in root.iter():
                 if "Members" in stripped_tag(members.tag):
                     for prop in members:
                         if "Property" in stripped_tag(prop.tag):
                             name = prop.attrib.get('Name')
                             type_attr = prop.attrib.get('Type')
                             direction = "InArgument"
                             if "OutArgument" in str(type_attr): direction = "OutArgument"
                             elif "InOutArgument" in str(type_attr): direction = "InOutArgument"
                             
                             if name:
                                 arguments.append({'name': name, 'direction': direction})

            # Extract Activities
            activities = []
            for elem in root.iter():
                tag = stripped_tag(elem.tag)
                if tag not in ["Variable", "Property", "Members", "VisualBasic.Settings", "TextExpression.ReferencesForImplementation"]:
                    activities.append({'type': tag})

            workflow_data = {
                'name': filename,
                'path': file_path,
                'variables': variables,
                'arguments': arguments,
                'activities': activities,
                'text_content': text_content,
                'tree': tree
            }

            # Run Process Workflow for each rule
            for rule in self.rules:
                rule.process_workflow(workflow_data)

        except ET.ParseError:
            print(f"Skipping {file_path}: Invalid XAML")
        except Exception as e:
            print(f"Error checking {file_path}: {e}")
