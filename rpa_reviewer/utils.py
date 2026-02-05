import xml.etree.ElementTree as ET
import re

def get_namespaces(file_path):
    """
    Extracts namespaces from a XAML file to help finding elements.
    """
    namespaces = {}
    try:
        events = "start", "start-ns"
        for event, elem in ET.iterparse(file_path, events):
            if event == "start-ns":
                prefix, uri = elem
                namespaces[prefix] = uri
    except Exception as e:
        pass
    return namespaces

def stripped_tag(tag):
    """
    Removes the namespace URL from a tag name.
    Example: {http://schemas.uipath.com/workflow/activities}Assign -> Assign
    """
    return tag.split('}', 1)[1] if '}' in tag else tag

def camel_case_split(str):
    return re.findall(r'[A-Z](?:[a-z]+|[A-Z]*(?=[A-Z]|$))', str)
