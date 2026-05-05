#!/usr/bin/env python3
"""
Upload sample data files to Azure Blob Storage

This script uploads conference attendance data files to Azure Blob Storage
for processing by the Fabric pipeline using Entra identity authentication.
"""

import sys
import os
import argparse
from pathlib import Path

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    class Fore:
        CYAN = GREEN = YELLOW = WHITE = RED = ""
    class Style:
        RESET_ALL = ""

try:
    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient
except ImportError:
    print("Error: Azure SDK packages not found. Install dependencies with: pip install -r requirements.txt")
    sys.exit(1)


def upload_to_blob(storage_account_name, container_name, file_path):
    """Upload a file to Azure Blob Storage using Entra identity."""
    
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}Azure Blob Storage Upload")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")
    
    print(f"{Fore.WHITE}Storage Account: {storage_account_name}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Container: {container_name}{Style.RESET_ALL}")
    
    # Check if file exists
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"{Fore.RED}Error: File not found: {file_path}{Style.RESET_ALL}")
        sys.exit(1)
    
    file_name = file_path.name
    print(f"{Fore.WHITE}File: {file_name}{Style.RESET_ALL}")
    
    try:
        # Create credential using Entra identity (DefaultAzureCredential)
        print(f"\n{Fore.YELLOW}Authenticating with Entra identity...{Style.RESET_ALL}")
        credential = DefaultAzureCredential()
        
        # Create BlobServiceClient
        account_url = f"https://{storage_account_name}.blob.core.windows.net"
        blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
        
        print(f"{Fore.GREEN}✓ Authenticated successfully{Style.RESET_ALL}")
        
        # Get or create container
        print(f"\n{Fore.YELLOW}Accessing container: {container_name}{Style.RESET_ALL}")
        container_client = blob_service_client.get_container_client(container_name)
        
        try:
            container_client.get_container_properties()
            print(f"{Fore.GREEN}✓ Container exists{Style.RESET_ALL}")
        except:
            print(f"{Fore.YELLOW}Creating container...{Style.RESET_ALL}")
            container_client.create_container()
            print(f"{Fore.GREEN}✓ Container created{Style.RESET_ALL}")
        
        # Upload the file
        print(f"\n{Fore.YELLOW}Uploading file to blob storage...{Style.RESET_ALL}")
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=file_name)
        
        with open(file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
        
        print(f"{Fore.GREEN}✓ Upload completed successfully!{Style.RESET_ALL}")
        
        # Display blob URL
        blob_url = f"https://{storage_account_name}.blob.core.windows.net/{container_name}/{file_name}"
        print(f"\n{Fore.CYAN}Blob Details:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  URL: {blob_url}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}  Size: {file_path.stat().st_size:,} bytes{Style.RESET_ALL}")
        
        # List files in container
        print(f"\n{Fore.YELLOW}Files in container:{Style.RESET_ALL}")
        blobs = container_client.list_blobs()
        for blob in blobs:
            print(f"{Fore.WHITE}  - {blob.name} ({blob.size:,} bytes){Style.RESET_ALL}")
        
    except Exception as e:
        print(f"\n{Fore.RED}Upload failed: {str(e)}{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}Troubleshooting:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}1. Ensure you're logged in: az login{Style.RESET_ALL}")
        print(f"{Fore.WHITE}2. Verify you have 'Storage Blob Data Contributor' role{Style.RESET_ALL}")
        print(f"{Fore.WHITE}3. Check storage account name is correct{Style.RESET_ALL}")
        sys.exit(1)
    
    print(f"\n{Fore.CYAN}Next steps:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}1. Update the pipeline configuration if needed{Style.RESET_ALL}")
    print(f"{Fore.WHITE}2. Deploy the Fabric pipeline using deploy_pipeline.py{Style.RESET_ALL}")
    print()


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Upload sample data files to Azure Blob Storage using Entra identity"
    )
    parser.add_argument(
        "--storage-account",
        required=True,
        help="Name of the Azure Storage Account"
    )
    parser.add_argument(
        "--container",
        default="conference-data",
        help="Name of the blob container (default: conference-data)"
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Path to the file to upload"
    )
    
    args = parser.parse_args()
    
    upload_to_blob(
        storage_account_name=args.storage_account,
        container_name=args.container,
        file_path=args.file
    )


if __name__ == "__main__":
    main()
