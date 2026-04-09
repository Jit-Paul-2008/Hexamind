import sys
import os

# Mocking TaxonomyNode
class TaxonomyNode:
    def __init__(self, id, topic):
        self.id = id
        self.topic = topic
        self.children = []

def prune_duplicate_nodes(node):
    seen_topics = set()
    unique_children = []
    for child in node.children:
        if child.topic.lower() not in seen_topics:
            seen_topics.add(child.topic.lower())
            unique_children.append(child)
            prune_duplicate_nodes(child)
    node.children = unique_children

# Test case for duplication
root = TaxonomyNode("root", "Energy")
root.children = [
    TaxonomyNode("c1", "Solar"),
    TaxonomyNode("c2", "Wind"),
    TaxonomyNode("c3", "Solar"), # Duplicate
]

print("Before pruning:")
for c in root.children:
    print(f"- {c.topic}")

prune_duplicate_nodes(root)

print("\nAfter pruning:")
for c in root.children:
    print(f"- {c.topic}")

assert len(root.children) == 2
assert root.children[0].topic == "Solar"
assert root.children[1].topic == "Wind"
import re

def clean_headers(text):
    return re.sub(r'^#+\s+', '', text, flags=re.MULTILINE).strip()

# Test header cleaning
dirty_text = "### Findings\n\nSome results.\n## Subtitle\nMore info."
expected = "Findings\n\nSome results.\nSubtitle\nMore info."
cleaned = clean_headers(dirty_text)
print(f"Original:\n{dirty_text}\n")
print(f"Cleaned:\n{cleaned}\n")
assert "###" not in cleaned
assert "##" not in cleaned
print("Success: Header cleaning logic verified!")

