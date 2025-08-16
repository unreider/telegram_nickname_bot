"""
Storage service for managing nickname data with JSON persistence.
Handles CRUD operations for nickname management by group.
"""

import json
import os
import time
import logging
from datetime import datetime
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class NicknameEntry:
    """Data model for a nickname entry."""
    user_id: int
    username: str
    nickname: str
    added_at: str


class StorageService:
    """
    Storage service that manages nickname data with in-memory storage
    and JSON file persistence.
    """
    
    def __init__(self, storage_file: str = "data/nicknames.json"):
        """
        Initialize the storage service.
        
        Args:
            storage_file: Path to the JSON file for persistence
        """
        self.storage_file = storage_file
        self._data: Dict[int, Dict[int, NicknameEntry]] = {}
        self._ensure_data_directory()
        self._load_data()
    
    def _ensure_data_directory(self) -> None:
        """Ensure the data directory exists."""
        directory = os.path.dirname(self.storage_file)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
    
    def _load_data(self) -> None:
        """Load data from JSON file into memory with comprehensive error handling."""
        max_retries = 3
        retry_delay = 0.1  # 100ms
        
        for attempt in range(max_retries):
            try:
                if os.path.exists(self.storage_file):
                    with open(self.storage_file, 'r', encoding='utf-8') as f:
                        raw_data = json.load(f)
                        
                    # Validate data structure
                    if not isinstance(raw_data, dict):
                        raise ValueError("Invalid data format: expected dictionary")
                        
                    # Convert raw data to proper structure with NicknameEntry objects
                    for group_id_str, group_data in raw_data.items():
                        try:
                            group_id = int(group_id_str)
                            if not isinstance(group_data, dict):
                                logger.warning(f"Invalid group data for group {group_id}, skipping")
                                continue
                                
                            self._data[group_id] = {}
                            
                            for user_id_str, entry_data in group_data.items():
                                try:
                                    user_id = int(user_id_str)
                                    if not isinstance(entry_data, dict):
                                        logger.warning(f"Invalid entry data for user {user_id} in group {group_id}, skipping")
                                        continue
                                        
                                    # Validate required fields
                                    required_fields = ['user_id', 'username', 'nickname', 'added_at']
                                    if not all(field in entry_data for field in required_fields):
                                        logger.warning(f"Missing required fields for user {user_id} in group {group_id}, skipping")
                                        continue
                                        
                                    self._data[group_id][user_id] = NicknameEntry(**entry_data)
                                except (ValueError, TypeError, KeyError) as e:
                                    logger.warning(f"Failed to load entry for user {user_id_str} in group {group_id}: {e}")
                                    continue
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Failed to load group {group_id_str}: {e}")
                            continue
                            
                logger.info(f"Successfully loaded data from {self.storage_file}")
                return
                
            except (json.JSONDecodeError, FileNotFoundError) as e:
                if attempt == 0:
                    logger.info(f"Storage file not found or corrupted, starting with empty data: {e}")
                    self._data = {}
                    return
                else:
                    logger.warning(f"Attempt {attempt + 1} failed to load data: {e}")
                    
            except (IOError, OSError, PermissionError) as e:
                logger.error(f"Attempt {attempt + 1} failed to load data due to file system error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                    continue
                else:
                    logger.error(f"Failed to load data after {max_retries} attempts, starting with empty data")
                    self._data = {}
                    return
                    
            except Exception as e:
                logger.error(f"Unexpected error loading data: {e}")
                self._data = {}
                return
    
    def _save_data(self) -> bool:
        """Save current data to JSON file with retry logic and error handling."""
        max_retries = 3
        retry_delay = 0.1  # 100ms
        
        for attempt in range(max_retries):
            try:
                # Convert NicknameEntry objects to dictionaries for JSON serialization
                serializable_data = {}
                for group_id, group_data in self._data.items():
                    serializable_data[str(group_id)] = {}
                    for user_id, entry in group_data.items():
                        try:
                            serializable_data[str(group_id)][str(user_id)] = asdict(entry)
                        except Exception as e:
                            logger.error(f"Failed to serialize entry for user {user_id} in group {group_id}: {e}")
                            continue
                
                # Write to temporary file first, then rename for atomic operation
                temp_file = f"{self.storage_file}.tmp"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(serializable_data, f, indent=2, ensure_ascii=False)
                
                # Atomic rename
                os.replace(temp_file, self.storage_file)
                logger.debug(f"Successfully saved data to {self.storage_file}")
                return True
                
            except (IOError, OSError, PermissionError) as e:
                logger.warning(f"Attempt {attempt + 1} failed to save data: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                    continue
                else:
                    logger.error(f"Failed to save data after {max_retries} attempts: {e}")
                    return False
                    
            except (TypeError, ValueError) as e:
                logger.error(f"Data serialization error: {e}")
                return False
                
            except Exception as e:
                logger.error(f"Unexpected error saving data: {e}")
                return False
                
        return False
    
    def add_nickname(self, group_id: int, user_id: int, username: str, nickname: str) -> bool:
        """
        Add a nickname for a user in a specific group.
        
        Args:
            group_id: Telegram group chat ID
            user_id: Telegram user ID
            username: Telegram username
            nickname: User-specified nickname
            
        Returns:
            True if nickname was added, False if user already has a nickname or operation failed
        """
        try:
            # Validate input parameters
            if not isinstance(group_id, int) or not isinstance(user_id, int):
                logger.error(f"Invalid ID types: group_id={type(group_id)}, user_id={type(user_id)}")
                return False
                
            if not username or not isinstance(username, str):
                logger.error(f"Invalid username: {username}")
                return False
                
            if not nickname or not isinstance(nickname, str):
                logger.error(f"Invalid nickname: {nickname}")
                return False
            
            if group_id not in self._data:
                self._data[group_id] = {}
            
            # Check if user already has a nickname in this group
            if user_id in self._data[group_id]:
                logger.debug(f"User {user_id} already has nickname in group {group_id}")
                return False
            
            # Add new nickname entry
            entry = NicknameEntry(
                user_id=user_id,
                username=username,
                nickname=nickname,
                added_at=datetime.now().isoformat()
            )
            
            self._data[group_id][user_id] = entry
            
            # Save data with error handling
            try:
                if not self._save_data():
                    logger.warning(f"Failed to persist nickname addition for user {user_id} in group {group_id}")
                    # Continue with in-memory storage
            except Exception as e:
                logger.warning(f"Exception during save for nickname addition: {e}")
                # Continue with in-memory storage
            
            logger.info(f"Added nickname '{nickname}' for user {user_id} in group {group_id}")
            return True
            
        except Exception as e:
            logger.error(f"Unexpected error adding nickname: {e}")
            return False
    
    def get_nickname(self, group_id: int, user_id: int) -> Optional[NicknameEntry]:
        """
        Get a user's nickname entry for a specific group.
        
        Args:
            group_id: Telegram group chat ID
            user_id: Telegram user ID
            
        Returns:
            NicknameEntry if found, None otherwise
        """
        if group_id not in self._data:
            return None
        
        return self._data[group_id].get(user_id)
    
    def get_all_nicknames(self, group_id: int) -> List[NicknameEntry]:
        """
        Get all nickname entries for a specific group.
        
        Args:
            group_id: Telegram group chat ID
            
        Returns:
            List of NicknameEntry objects, ordered by addition time
        """
        if group_id not in self._data:
            return []
        
        entries = list(self._data[group_id].values())
        # Sort by addition time for consistent ordering
        entries.sort(key=lambda x: x.added_at)
        return entries
    
    def update_nickname(self, group_id: int, user_id: int, new_nickname: str) -> bool:
        """
        Update a user's nickname in a specific group.
        
        Args:
            group_id: Telegram group chat ID
            user_id: Telegram user ID
            new_nickname: New nickname to set
            
        Returns:
            True if nickname was updated, False if user has no existing nickname or operation failed
        """
        try:
            # Validate input parameters
            if not isinstance(group_id, int) or not isinstance(user_id, int):
                logger.error(f"Invalid ID types: group_id={type(group_id)}, user_id={type(user_id)}")
                return False
                
            if not new_nickname or not isinstance(new_nickname, str):
                logger.error(f"Invalid new_nickname: {new_nickname}")
                return False
            
            if group_id not in self._data or user_id not in self._data[group_id]:
                logger.debug(f"No existing nickname for user {user_id} in group {group_id}")
                return False
            
            # Update the nickname while preserving other data
            entry = self._data[group_id][user_id]
            old_nickname = entry.nickname
            entry.nickname = new_nickname
            
            # Save data with error handling
            try:
                if not self._save_data():
                    logger.warning(f"Failed to persist nickname update for user {user_id} in group {group_id}")
                    # Continue with in-memory storage
            except Exception as e:
                logger.warning(f"Exception during save for nickname update: {e}")
                # Continue with in-memory storage
            
            logger.info(f"Updated nickname for user {user_id} in group {group_id}: '{old_nickname}' -> '{new_nickname}'")
            return True
            
        except Exception as e:
            logger.error(f"Unexpected error updating nickname: {e}")
            return False
    
    def remove_nickname(self, group_id: int, user_id: int) -> bool:
        """
        Remove a user's nickname from a specific group.
        
        Args:
            group_id: Telegram group chat ID
            user_id: Telegram user ID
            
        Returns:
            True if nickname was removed, False if user had no nickname or operation failed
        """
        try:
            # Validate input parameters
            if not isinstance(group_id, int) or not isinstance(user_id, int):
                logger.error(f"Invalid ID types: group_id={type(group_id)}, user_id={type(user_id)}")
                return False
            
            if group_id not in self._data or user_id not in self._data[group_id]:
                logger.debug(f"No nickname to remove for user {user_id} in group {group_id}")
                return False
            
            # Get nickname for logging
            removed_nickname = self._data[group_id][user_id].nickname
            
            del self._data[group_id][user_id]
            
            # Clean up empty group data
            if not self._data[group_id]:
                del self._data[group_id]
            
            # Save data with error handling
            try:
                if not self._save_data():
                    logger.warning(f"Failed to persist nickname removal for user {user_id} in group {group_id}")
                    # Continue with in-memory storage
            except Exception as e:
                logger.warning(f"Exception during save for nickname removal: {e}")
                # Continue with in-memory storage
            
            logger.info(f"Removed nickname '{removed_nickname}' for user {user_id} in group {group_id}")
            return True
            
        except Exception as e:
            logger.error(f"Unexpected error removing nickname: {e}")
            return False
    
    def has_nickname(self, group_id: int, user_id: int) -> bool:
        """
        Check if a user has a nickname in a specific group.
        
        Args:
            group_id: Telegram group chat ID
            user_id: Telegram user ID
            
        Returns:
            True if user has a nickname, False otherwise
        """
        return (group_id in self._data and 
                user_id in self._data[group_id])
    
    def get_group_count(self, group_id: int) -> int:
        """
        Get the number of nicknames in a specific group.
        
        Args:
            group_id: Telegram group chat ID
            
        Returns:
            Number of nicknames in the group
        """
        if group_id not in self._data:
            return 0
        
        return len(self._data[group_id])
    
    def is_healthy(self) -> bool:
        """
        Check if the storage service is healthy.
        
        Returns:
            True if storage is accessible and functional, False otherwise
        """
        try:
            # Check if data structure is accessible
            if not isinstance(self._data, dict):
                return False
            
            # Check if storage file directory is accessible
            directory = os.path.dirname(self.storage_file)
            if directory and not os.access(directory, os.W_OK):
                logger.warning(f"Storage directory {directory} is not writable")
                return False
            
            # Try a simple read/write test if file exists
            if os.path.exists(self.storage_file):
                if not os.access(self.storage_file, os.R_OK):
                    logger.warning(f"Storage file {self.storage_file} is not readable")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Storage health check failed: {e}")
            return False