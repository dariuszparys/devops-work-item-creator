# Azure Work Items

A command-line tool for creating and managing Azure DevOps work items from YAML definitions.

## Overview

This tool allows you to define a hierarchy of work items (Epics, Features, and Product Backlog Items) in a YAML file and then create or delete them in Azure DevOps with proper parent-child relationships.

## Features

- Create hierarchical work items in Azure DevOps from YAML definitions
- Automatically establish parent-child relationships between work items
- Delete work items created from YAML definitions
- Track created work items for easy deletion
- Detailed logging for troubleshooting

## Prerequisites

- Python 3.6+
- Azure CLI installed and configured
- Azure DevOps extension for Azure CLI
- Python Fire library

## Installation

1. Install dependencies:
   ```bash
   pip install pyyaml fire
   ```

   as this was created using `uv` you can also `uv sync`

2. Ensure Azure CLI is installed and authenticated:
   ```bash
   az login
   az extension add --name azure-devops
   az devops configure --defaults organization=https://dev.azure.com/your-organization project=your-project
   ```

## Usage

### Creating Work Items

To create work items defined in a YAML file:

```bash
python azure_work_items.py create [yaml_file]
```

If no YAML file is specified, it defaults to `input.yaml`.

### Deleting Work Items

To delete work items that were previously created:

```bash
python azure_work_items.py delete [yaml_file]
```

This will first try to delete items based on the saved `created_items.yaml` file. If that file doesn't exist, it will search for items by title in Azure DevOps.

### Debug Mode

To enable debug logging:

```bash
python azure_work_items.py --debug create [yaml_file]
```

## YAML File Format

The YAML file should define a hierarchy of Epics, Features, and Product Backlog Items:

```yaml
epics:
  - title: "Epic 1: Improve Product Performance"
    features:
      - title: "Feature 1: Optimize Database Queries"
        items:
          - title: "Item 1: Add Indexing to User Table"
          - title: "Item 2: Optimize Query Caching"
      - title: "Feature 2: Refactor UI Components"
        items:
          - title: "Item 1: Implement Component Library"
          - title: "Item 2: Audit Legacy Code"
```

## Files Created by the Application

- **created_items.yaml**: Stores information about created work items for later deletion
- **azure_devops.log**: Log file containing execution details

## Troubleshooting

- If you encounter authentication issues, ensure you're logged in with `az login`
- If work item creation fails, check that your Azure DevOps project uses the expected work item types (Epic, Feature, Product Backlog Item)
- For detailed logs, check the `azure_devops.log` file or run with the `--debug` flag

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
