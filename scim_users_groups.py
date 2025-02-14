#!/usr/bin/env python3
import requests
import argparse
import json
from typing import Dict, List, Optional
import sys
import time

def get_page(base_url: str, token: str, resource_type: str, start_index: int = 1, count: int = 1000) -> Dict:
    """Retrieve a single page of resources (users or groups) from SCIM API"""
    headers = {
        'accept': 'application/scim+json;charset=utf-8',
        'Authorization': f'Bearer {token}'
    }
    
    params = {
        'startIndex': start_index,
        'count': count
    }
    
    try:
        response = requests.get(
            f"{base_url.rstrip('/')}/api/v2/scim/{resource_type}",
            headers=headers,
            params=params
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving {resource_type}: {e}", file=sys.stderr)
        sys.exit(1)

def get_all_resources(base_url: str, token: str, resource_type: str) -> Dict:
    """Retrieve all resources from SCIM API using pagination"""
    first_page = get_page(base_url, token, resource_type)
    total_results = first_page.get('totalResults', 0)
    items_per_page = first_page.get('itemsPerPage', 1000)
    
    print(f"Found {total_results} total {resource_type}, fetching all pages...", file=sys.stderr)
    
    all_resources = first_page.get('Resources', [])
    
    current_index = items_per_page + 1
    while current_index <= total_results:
        print(f"Fetching page starting at index {current_index}...", file=sys.stderr)
        page = get_page(base_url, token, resource_type, start_index=current_index)
        all_resources.extend(page.get('Resources', []))
        current_index += items_per_page
    
    return {
        "schemas": first_page.get('schemas', []),
        "totalResults": total_results,
        "Resources": all_resources,
        "itemsPerPage": len(all_resources),
        "startIndex": 1
    }

def delete_resource(base_url: str, token: str, resource_type: str, resource_id: str) -> bool:
    """Delete a single resource by ID"""
    headers = {
        'accept': '*/*',
        'Authorization': f'Bearer {token}'
    }
    
    try:
        response = requests.delete(
            f"{base_url.rstrip('/')}/api/v2/scim/{resource_type}/{resource_id}",
            headers=headers
        )
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error deleting {resource_type} {resource_id}: {e}", file=sys.stderr)
        return False

def delete_resources(base_url: str, token: str, resource_type: str, resource_ids: List[str], delay: float = 0.5) -> Dict[str, bool]:
    """Delete multiple resources with delay between requests"""
    results = {}
    total = len(resource_ids)
    
    for i, resource_id in enumerate(resource_ids, 1):
        print(f"Deleting {resource_type} {i}/{total} (ID: {resource_id})...", file=sys.stderr)
        success = delete_resource(base_url, token, resource_type, resource_id)
        results[resource_id] = success
        if i < total:  # Don't sleep after the last request
            time.sleep(delay)
    
    return results

def create_user(base_url: str, token: str, username: str, email: str, 
                first_name: str, last_name: str, external_id: Optional[str] = None) -> Dict:
    """Create a new user via SCIM API"""
    headers = {
        'accept': 'application/scim+json;charset=utf-8',
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/scim+json;charset=utf-8'
    }
    
    payload = {
        "active": True,
        "emails": [
            {
                "primary": True,
                "value": email
            }
        ],
        "externalId": external_id,
        "meta": {
            "resourceType": "User"
        },
        "name": {
            "familyName": last_name,
            "givenName": first_name
        },
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
            "urn:ietf:params:scim:schemas:extension:tenant:2.0:User"
        ],
        "userName": username
    }
    
    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/api/v2/scim/Users",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error creating user: {e}", file=sys.stderr)
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)

def create_group(base_url: str, token: str, display_name: str, 
                external_id: Optional[str] = None, member_ids: Optional[List[str]] = None) -> Dict:
    """Create a new group via SCIM API"""
    headers = {
        'accept': 'application/scim+json;charset=utf-8',
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/scim+json;charset=utf-8'
    }
    
    payload = {
        "displayName": display_name,
        "externalId": external_id,
        "meta": {
            "resourceType": "Group"
        },
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:Group"
        ]
    }
    
    if member_ids:
        payload["members"] = [{"value": member_id} for member_id in member_ids]
    
    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/api/v2/scim/Groups",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error creating group: {e}", file=sys.stderr)
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)

def add_user_to_group(base_url: str, token: str, group_id: str, user_id: str) -> bool:
    """Add a user to a group via SCIM PATCH operation"""
    headers = {
        'accept': '*/*',
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/scim+json;charset=utf-8'
    }
    
    payload = {
        "schemas": [
            "urn:ietf:params:scim:api:messages:2.0:PatchOp"
        ],
        "Operations": [
            {
                "op": "add",
                "path": "members",
                "value": {
                    "value": {
                        "value": user_id
                    }
                }
            }
        ]
    }
    
    try:
        response = requests.patch(
            f"{base_url.rstrip('/')}/api/v2/scim/Groups/{group_id}",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error adding user to group: {e}", file=sys.stderr)
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}", file=sys.stderr)
        return False

def format_user(user: Dict) -> str:
    """Format user details for display"""
    return (
        f"Username: {user.get('userName', 'N/A')}\n"
        f"ID: {user.get('id', 'N/A')}\n"
        f"Name: {user.get('name', {}).get('givenName', 'N/A')} {user.get('name', {}).get('familyName', 'N/A')}\n"
        f"Status: {user.get('active', False)}\n"
        f"Email: {user.get('emails', [{'value': 'N/A'}])[0]['value']}"
    )

def format_group(group: Dict) -> str:
    """Format group details for display"""
    return (
        f"Display Name: {group.get('displayName', 'N/A')}\n"
        f"ID: {group.get('id', 'N/A')}\n"
        f"Last Modified: {group.get('meta', {}).get('lastModified', 'N/A')}\n"
        f"External ID: {group.get('externalId', 'N/A')}"
    )

def main():
    parser = argparse.ArgumentParser(description='SCIM User and Group Management CLI Tool')
    parser.add_argument('--url', required=True, help='Base URL of the SCIM API')
    parser.add_argument('--token', required=True, help='Bearer token for authentication')
    parser.add_argument('--format', choices=['pretty', 'json'], default='pretty',
                       help='Output format (default: pretty)')
    parser.add_argument('--type', choices=['Users', 'Groups'], 
                       help='Resource type to manage (required for list/delete operations)')
    parser.add_argument('--action', choices=['list', 'delete', 'create'], default='list',
                       help='Action to perform (default: list)')
    parser.add_argument('--id', help='Specific resource ID to delete')
    parser.add_argument('--delay', type=float, default=0.5,
                       help='Delay between delete requests in seconds (default: 0.5)')
    
    # User creation parameters
    parser.add_argument('--username', help='Username for new user')
    parser.add_argument('--email', help='Email for new user')
    parser.add_argument('--first-name', help='First name for new user')
    parser.add_argument('--last-name', help='Last name for new user')
    
    # Group creation parameters
    parser.add_argument('--display-name', help='Display name for new group')
    parser.add_argument('--external-id', help='External ID for new user or group')
    parser.add_argument('--members', help='Comma-separated list of member IDs for new group')
    
    # Group membership parameters
    parser.add_argument('--add-to-group', action='store_true',
                       help='Add user to group')
    parser.add_argument('--user-id', help='User ID for group membership operations')
    parser.add_argument('--group-id', help='Group ID for group membership operations')
    
    args = parser.parse_args()
    
    # Handle adding user to group
    if args.add_to_group:
        if not all([args.user_id, args.group_id]):
            print("Error: --user-id and --group-id are required for adding user to group")
            sys.exit(1)
        
        success = add_user_to_group(args.url, args.token, args.group_id, args.user_id)
        if success:
            print(f"Successfully added user {args.user_id} to group {args.group_id}")
        else:
            print(f"Failed to add user {args.user_id} to group {args.group_id}")
        sys.exit(0)
    
    # Create operations
    if args.action == 'create':
        # User creation
        if args.username:
            if not all([args.email, args.first_name, args.last_name]):
                print("Error: email, first-name, and last-name are required for user creation")
                sys.exit(1)
                
            user = create_user(
                args.url,
                args.token,
                args.username,
                args.email,
                args.first_name,
                args.last_name,
                args.external_id
            )
            
            if args.format == 'json':
                print(json.dumps(user, indent=2))
            else:
                print("User created successfully:")
                print(format_user(user))
            sys.exit(0)
        
        # Group creation
        elif args.display_name:
            member_ids = args.members.split(',') if args.members else None
            
            group = create_group(
                args.url,
                args.token,
                args.display_name,
                args.external_id,
                member_ids
            )
            
            if args.format == 'json':
                print(json.dumps(group, indent=2))
            else:
                print("Group created successfully:")
                print(format_group(group))
            sys.exit(0)
        else:
            print("Error: For create action, either provide --username (for user) or --display-name (for group)")
            sys.exit(1)
    
    # List and Delete operations
    else:
        if not args.type:
            print("Error: --type is required for list and delete operations")
            sys.exit(1)
        
        if args.action == 'delete' and not args.id:
            confirm = input(f"No ID specified. This will delete ALL {args.type}. Are you sure? (yes/no): ")
            if confirm.lower() != 'yes':
                print("Operation cancelled.")
                sys.exit(0)
        
        if args.action == 'list' or not args.id:
            resources = get_all_resources(args.url, args.token, args.type)
            
            if args.action == 'delete':
                resource_ids = [resource['id'] for resource in resources['Resources']]
                results = delete_resources(args.url, args.token, args.type, resource_ids, args.delay)
                
                successful = sum(1 for success in results.values() if success)
                print(f"\nDeletion Summary:")
                print(f"Successfully deleted: {successful}")
                print(f"Failed to delete: {len(results) - successful}")
                
                if args.format == 'json':
                    print(json.dumps(results, indent=2))
            else:  # list action
                if args.format == 'json':
                    print(json.dumps(resources, indent=2))
                else:
                    print(f"Total {args.type} found: {len(resources['Resources'])}\n")
                    for resource in resources['Resources']:
                        if args.type == 'Users':
                            print(format_user(resource))
                        else:
                            print(format_group(resource))
                        print("-" * 40)
        else:  # Single resource deletion
            success = delete_resource(args.url, args.token, args.type, args.id)
            print(f"{args.type[:-1]} {args.id} deletion: {'successful' if success else 'failed'}")

if __name__ == "__main__":
    main()


