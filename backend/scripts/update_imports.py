import os
import re

backend_dir = r"d:\Maitri V5\backend"

def update_imports(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content

    content = content.replace("from security", "from security")
    content = content.replace("import security", "import security")
    content = content.replace("from rag.finetuning", "from rag.finetuning")
    content = content.replace("import rag.finetuning", "import rag.finetuning")
    content = content.replace("from rag.knowledge", "from rag.knowledge")
    content = content.replace("import rag.knowledge", "import rag.knowledge")
    content = content.replace("from rag.memory", "from rag.memory")
    content = content.replace("import rag.memory", "import rag.memory")
    content = content.replace("from rag.brain", "from rag.brain")
    content = content.replace("import rag.brain", "import rag.brain")
    content = content.replace("from rag.knowledge", "from rag.knowledge")
    content = content.replace("import rag.knowledge", "import rag.knowledge")
    content = content.replace("from security.authentication", "from security.authentication")
    content = content.replace("import security.authentication", "import security.authentication")
    content = content.replace("from modules.legacy_api.", "from modules.legacy_api.")
    content = content.replace("import modules.legacy_api.", "import modules.legacy_api.")
    content = content.replace("from modules.core_api", "from modules.core_api")
    content = content.replace("import modules.core_api", "import modules.core_api")
    content = content.replace("from modules.services", "from modules.services")
    content = content.replace("import modules.services", "import modules.services")
    content = content.replace("from modules.telemetry_ui", "from modules.telemetry_ui")
    content = content.replace("import modules.telemetry_ui", "import modules.telemetry_ui")
    content = content.replace("from modules.src.", "from modules.src.")
    content = content.replace("import modules.src.", "import modules.src.")

    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated: {filepath}")

for root, dirs, files in os.walk(backend_dir):
    if 'venv' in root or '__pycache__' in root or '.git' in root:
        continue
    for file in files:
        if file.endswith('.py'):
            update_imports(os.path.join(root, file))

print("Import update complete.")
