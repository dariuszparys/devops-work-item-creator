import yaml
import subprocess
import sys
import logging
import os
import fire

# Configure logging
def setup_logging(log_level=logging.INFO):
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(),  # Console handler
            logging.FileHandler(os.path.join(os.path.dirname(__file__), 'devops.log'))  # File handler
        ]
    )
    return logging.getLogger(__name__)

# Initialize logger
logger = setup_logging()

class DevOpsWorkItems:
    """Create and manage Azure DevOps work items from YAML definitions.
    
    This tool allows you to create and delete work items in Azure DevOps
    based on a YAML file definition. It supports creating Epics, Features,
    and Product Backlog Items with proper parent-child relationships.
    """
    
    def __init__(self, debug=False):
        """Initialize the DevOpsWorkItems tool.
        
        Args:
            debug (bool): Enable debug logging
        """
        global logger
        if debug:
            logger = setup_logging(logging.DEBUG)
            logger.debug("Debug logging enabled")
    
    def create(self, yaml_file="input.yaml"):
        """Create work items defined in the YAML file.
        
        Args:
            yaml_file (str): Path to the YAML file containing work item definitions
        """
        logger.info(f"Creating work items from {yaml_file}")
        try:
            with open(yaml_file, 'r') as file:
                data = yaml.safe_load(file)
            self._create_work_items(data)
        except FileNotFoundError:
            print(f"Error: YAML file not found: {yaml_file}")
            return 1
        except yaml.YAMLError as e:
            print(f"Error parsing YAML file: {e}")
            return 1
        return 0
    
    def delete(self, yaml_file="input.yaml"):
        """Delete work items defined in the YAML file.
        
        Args:
            yaml_file (str): Path to the YAML file containing work item definitions
        """
        logger.info(f"Deleting work items from {yaml_file}")
        try:
            with open(yaml_file, 'r') as file:
                data = yaml.safe_load(file)
            self._delete_work_items(data)
        except FileNotFoundError:
            print(f"Error: YAML file not found: {yaml_file}")
            return 1
        except yaml.YAMLError as e:
            print(f"Error parsing YAML file: {e}")
            return 1
        return 0
    
    def _create_work_item(self, work_item_type, title, parent_id=None):
        """Create a single work item in Azure DevOps.
        
        Args:
            work_item_type (str): Type of work item (Epic, Feature, Product Backlog Item)
            title (str): Title of the work item
            parent_id (str, optional): ID of the parent work item
            
        Returns:
            str: ID of the created work item, or None if creation failed
        """
        command = [
            "az", "boards", "work-item", "create",
            "--type", work_item_type,
            "--title", title,
            "--query", "id",
            "-o", "tsv"
        ]
        
        # Run the command and capture the work item ID
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Error creating work item: {result.stderr}")
            return None
        
        work_item_id = result.stdout.strip()
        
        # Link to parent if specified
        if parent_id:
            link_command = [
                "az", "boards", "work-item", "relation", "add",
                "--id", work_item_id,
                "--relation-type", "Parent",
                "--target-id", parent_id
            ]
            subprocess.run(link_command, check=True)
        
        return work_item_id
    
    def _delete_work_item(self, work_item_id):
        """Delete a single work item from Azure DevOps.
        
        Args:
            work_item_id (str): ID of the work item to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        if not work_item_id:
            return False
            
        command = [
            "az", "boards", "work-item", "delete",
            "--id", work_item_id,
            "--yes"  # Skip confirmation prompt
        ]
        
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Error deleting work item {work_item_id}: {result.stderr}")
            return False
        
        return True
    
    def _create_work_items(self, data):
        """Create all work items defined in the data structure.
        
        Args:
            data (dict): Data structure containing work item definitions
        """
        created_items = []
        
        for epic in data['epics']:
            # Create Epic
            epic_id = self._create_work_item("Epic", epic['title'])
            logger.info(f"Created Epic: {epic['title']} (ID: {epic_id})")
            created_items.append({"type": "Epic", "id": epic_id, "title": epic['title']})
            
            if not epic_id:
                logger.warning("Failed to create Epic. Skipping features.")
                continue
            
            for feature in epic['features']:
                # Create Feature
                feature_id = self._create_work_item("Feature", feature['title'])
                logger.info(f"  Created Feature: {feature['title']} (ID: {feature_id})")
                created_items.append({"type": "Feature", "id": feature_id, "title": feature['title']})
                
                if not feature_id:
                    logger.warning("  Failed to create Feature. Skipping items.")
                    continue
                
                # Link Feature to Epic (Epic is parent of Feature)
                link_command = [
                    "az", "boards", "work-item", "relation", "add",
                    "--id", feature_id,
                    "--relation-type", "Parent",
                    "--target-id", epic_id
                ]
                subprocess.run(link_command, check=True)
                
                for item in feature['items']:
                    # Create Product Backlog Item
                    item_id = self._create_work_item("Product Backlog Item", item['title'])
                    logger.info(f"    Created Item: {item['title']} (ID: {item_id})")
                    created_items.append({"type": "Product Backlog Item", "id": item_id, "title": item['title']})
                    
                    # Only try to link if item was created successfully
                    if item_id:
                        # Link PBI to Feature (Feature is parent of PBI)
                        link_command = [
                            "az", "boards", "work-item", "relation", "add",
                            "--id", item_id,
                            "--relation-type", "Parent",
                            "--target-id", feature_id
                        ]
                        subprocess.run(link_command, check=True)
                    else:
                        logger.warning(f"    Failed to create work item for: {item['title']}")
        
        # Save created items to a file for potential deletion later
        with open("created_items.yaml", "w") as f:
            yaml.dump({"created_items": created_items}, f)
        logger.debug(f"Saved {len(created_items)} created items to created_items.yaml")
    
    def _delete_work_items(self, data):
        """Delete all work items defined in the data structure.
        
        Args:
            data (dict): Data structure containing work item definitions
        """
        # First try to load from created_items.yaml if it exists
        try:
            with open("created_items.yaml", "r") as f:
                created_items = yaml.safe_load(f)
                if created_items and "created_items" in created_items:
                    self._delete_from_created_items(created_items["created_items"])
                    return
        except FileNotFoundError:
            logger.warning("No created_items.yaml file found. Attempting to delete based on input YAML...")
        
        # If no created_items.yaml, try to find and delete based on titles
        logger.info("Searching for work items to delete based on titles in the YAML file...")
        
        # Delete in reverse order (PBIs first, then Features, then Epics)
        for epic in data['epics']:
            for feature in epic['features']:
                for item in feature['items']:
                    # Find and delete PBI by title
                    self._find_and_delete_by_title("Product Backlog Item", item['title'])
                
                # Find and delete Feature by title
                self._find_and_delete_by_title("Feature", feature['title'])
            
            # Find and delete Epic by title
            self._find_and_delete_by_title("Epic", epic['title'])
    
    def _delete_from_created_items(self, created_items):
        """Delete work items from a saved list.
        
        Args:
            created_items (list): List of work items to delete
        """
        # Delete in reverse order (last created first)
        logger.info(f"Deleting {len(created_items)} work items from saved list...")
        for item in reversed(created_items):
            if "id" in item and item["id"]:
                logger.info(f"Deleting {item['type']}: {item['title']} (ID: {item['id']})")
                if self._delete_work_item(item["id"]):
                    logger.info(f"  Successfully deleted {item['type']} with ID {item['id']}")
                else:
                    logger.error(f"  Failed to delete {item['type']} with ID {item['id']}")
    
    def _find_and_delete_by_title(self, work_item_type, title):
        """Find and delete work items by type and title.
        
        Args:
            work_item_type (str): Type of work item to find
            title (str): Title of the work item to find
        """
        # Find work item by title and type
        find_command = [
            "az", "boards", "query",
            "--wiql", f"SELECT [System.Id] FROM WorkItems WHERE [System.WorkItemType] = '{work_item_type}' AND [System.Title] = '{title}'",
            "-o", "json"
        ]
        
        result = subprocess.run(find_command, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Error finding {work_item_type} '{title}': {result.stderr}")
            return
        
        try:
            import json
            items = json.loads(result.stdout)
            if items and len(items) > 0:
                for item in items:
                    work_item_id = str(item.get("id"))
                    logger.info(f"Found {work_item_type}: {title} (ID: {work_item_id})")
                    if self._delete_work_item(work_item_id):
                        logger.info(f"  Successfully deleted {work_item_type} with ID {work_item_id}")
                    else:
                        logger.error(f"  Failed to delete {work_item_type} with ID {work_item_id}")
            else:
                logger.warning(f"No {work_item_type} found with title: {title}")
        except json.JSONDecodeError:
            logger.error(f"Error parsing response when finding {work_item_type} '{title}'")

def main():
    """Main entry point for the script."""
    fire.Fire(DevOpsWorkItems)

if __name__ == "__main__":
    main()