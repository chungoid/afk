#!/usr/bin/env python3
import json
import os

# Load pipeline data
data = json.load(open('/tmp/pipeline_data.json'))
code_msg = next(m for m in data['recent_messages'] if m['stage']=='coding')

print(f"Extracting project: {code_msg['data']['metadata']['original_request']['metadata']['project_name']}")

# Extract and save each source file
for artifact in code_msg['data']['artifacts']:
    filepath = 'generated_project/' + artifact['file_path']
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(artifact['content'])
    print(f'Created: {filepath}')

# Save test files
for test_file in code_msg['data']['test_files']:
    filepath = 'generated_project/' + test_file['file_path'] 
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(test_file['content'])
    print(f'Created: {filepath}')

# Save deployment files
for deploy_file in code_msg['data']['deployment_files']:
    filepath = 'generated_project/' + deploy_file['file_path']
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(deploy_file['content'])
    print(f'Created: {filepath}')

print(f"\nProject extracted to: ./generated_project/")
print(f"Total files: {len(code_msg['data']['artifacts']) + len(code_msg['data']['test_files']) + len(code_msg['data']['deployment_files'])}") 