"""
Configuration management for ReqSmith
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, asdict, field
from cryptography.fernet import Fernet
from enum import Enum


logger = logging.getLogger(__name__)


class ConfigVersion(Enum):
    """Configuration version for migration support."""
    V1_0 = "1.0"
    V1_1 = "1.1"
    CURRENT = V1_1


@dataclass
class StorageConfig:
    """Configuration for hybrid storage system"""
    memory_cache_size_mb: int = 25
    disk_cache_size_mb: int = 100
    history_limit: int = 1000
    cache_ttl_seconds: int = 3600
    user_storage_path: Optional[str] = None


@dataclass
class AIConfig:
    """Configuration for AI features"""
    gemini_api_key: Optional[str] = None
    enable_suggestions: bool = True
    enable_validation: bool = True
    enable_explanations: bool = True


@dataclass
class OutputConfig:
    """Configuration for output formatting"""
    default_format: str = "json"
    color_output: bool = True
    table_max_rows: int = 50
    save_responses: bool = False
    response_save_path: Optional[str] = None


@dataclass
class NetworkConfig:
    """Configuration for network requests"""
    timeout_seconds: int = 30
    max_retries: int = 3
    verify_ssl: bool = True
    follow_redirects: bool = True
    default_headers: Dict[str, str] = None

    def __post_init__(self):
        if self.default_headers is None:
            self.default_headers = {
                "User-Agent": "ReqSmith/0.1.0"
            }


@dataclass
class ReqSmithConfig:
    """Main configuration class for ReqSmith"""
    storage: StorageConfig
    ai: AIConfig
    output: OutputConfig
    network: NetworkConfig
    debug: bool = False
    config_file_path: Optional[str] = None
    version: str = ConfigVersion.CURRENT.value
    
    # Environment variable mappings
    ENV_MAPPINGS = {
        "REQSMITH_DEBUG": ("debug", bool),
        "REQSMITH_STORAGE_PATH": ("storage.user_storage_path", str),
        "REQSMITH_CACHE_SIZE": ("storage.memory_cache_size_mb", int),
        "REQSMITH_HISTORY_LIMIT": ("storage.history_limit", int),
        "REQSMITH_TIMEOUT": ("network.timeout_seconds", int),
        "REQSMITH_MAX_RETRIES": ("network.max_retries", int),
        "REQSMITH_VERIFY_SSL": ("network.verify_ssl", bool),
        "REQSMITH_COLOR_OUTPUT": ("output.color_output", bool),
        "REQSMITH_DEFAULT_FORMAT": ("output.default_format", str),
        "REQSMITH_GEMINI_API_KEY": ("ai.gemini_api_key", str),
        "REQSMITH_AI_SUGGESTIONS": ("ai.enable_suggestions", bool),
        "REQSMITH_AI_VALIDATION": ("ai.enable_validation", bool),
    }

    @classmethod
    def get_default_config_path(cls) -> Path:
        """Get the default configuration file path"""
        home = Path.home()
        config_dir = home / ".reqsmith"
        config_dir.mkdir(exist_ok=True)
        return config_dir / "config.json"

    @classmethod
    def get_default_storage_path(cls) -> Path:
        """Get the default storage directory path"""
        home = Path.home()
        storage_dir = home / ".reqsmith" / "storage"
        storage_dir.mkdir(parents=True, exist_ok=True)
        return storage_dir

    @classmethod
    def load_from_file(cls, config_path: Optional[Path] = None, apply_env_overrides: bool = True) -> "ReqSmithConfig":
        """Load configuration from file or create default"""
        if config_path is None:
            config_path = cls.get_default_config_path()

        config = None
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                
                # Check if migration is needed
                file_version = config_data.get("version", "1.0")
                if file_version != ConfigVersion.CURRENT.value:
                    logger.info(f"Migrating configuration from version {file_version} to {ConfigVersion.CURRENT.value}")
                    config_data = cls._migrate_config(config_data, file_version)
                
                config = cls.from_dict(config_data)
                
                # Validate configuration
                validation_errors = config.validate()
                if validation_errors:
                    logger.warning(f"Configuration validation errors: {validation_errors}")
                    logger.warning("Some settings may be reset to defaults")
                    
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.error(f"Invalid config file {config_path}: {e}")
                logger.info("Using default configuration")

        # Use default if loading failed
        if config is None:
            config = cls.get_default()
        
        # Apply environment variable overrides
        if apply_env_overrides:
            config = config.apply_env_overrides()
            
        return config

    @classmethod
    def get_default(cls) -> "ReqSmithConfig":
        """Get default configuration"""
        storage_path = str(cls.get_default_storage_path())
        
        return cls(
            storage=StorageConfig(user_storage_path=storage_path),
            ai=AIConfig(),
            output=OutputConfig(),
            network=NetworkConfig(),
            config_file_path=str(cls.get_default_config_path())
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReqSmithConfig":
        """Create configuration from dictionary"""
        storage_data = data.get("storage", {})
        ai_data = data.get("ai", {})
        output_data = data.get("output", {})
        network_data = data.get("network", {})

        return cls(
            storage=StorageConfig(**storage_data),
            ai=AIConfig(**ai_data),
            output=OutputConfig(**output_data),
            network=NetworkConfig(**network_data),
            debug=data.get("debug", False),
            config_file_path=data.get("config_file_path")
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "storage": asdict(self.storage),
            "ai": asdict(self.ai),
            "output": asdict(self.output),
            "network": asdict(self.network),
            "debug": self.debug,
            "config_file_path": self.config_file_path
        }

    def save_to_file(self, config_path: Optional[Path] = None) -> bool:
        """Save configuration to file"""
        if config_path is None:
            config_path = Path(self.config_file_path) if self.config_file_path else self.get_default_config_path()

        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config to {config_path}: {e}")
            return False

    def set_gemini_api_key(self, api_key: str) -> bool:
        """Set and encrypt Gemini API key"""
        try:
            # Generate encryption key if it doesn't exist
            key_file = Path(self.storage.user_storage_path) / "encryption.key"
            if not key_file.exists():
                key = Fernet.generate_key()
                with open(key_file, 'wb') as f:
                    f.write(key)
                os.chmod(key_file, 0o600)  # Restrict permissions
            else:
                with open(key_file, 'rb') as f:
                    key = f.read()

            # Encrypt and store API key
            fernet = Fernet(key)
            encrypted_key = fernet.encrypt(api_key.encode())
            
            key_storage_file = Path(self.storage.user_storage_path) / "gemini_key.enc"
            with open(key_storage_file, 'wb') as f:
                f.write(encrypted_key)
            os.chmod(key_storage_file, 0o600)  # Restrict permissions

            self.ai.gemini_api_key = "[ENCRYPTED]"
            return True
        except Exception as e:
            print(f"Error storing API key: {e}")
            return False

    def get_gemini_api_key(self) -> Optional[str]:
        """Decrypt and return Gemini API key"""
        try:
            key_file = Path(self.storage.user_storage_path) / "encryption.key"
            key_storage_file = Path(self.storage.user_storage_path) / "gemini_key.enc"
            
            if not key_file.exists() or not key_storage_file.exists():
                return None

            with open(key_file, 'rb') as f:
                key = f.read()
            
            with open(key_storage_file, 'rb') as f:
                encrypted_key = f.read()

            fernet = Fernet(key)
            decrypted_key = fernet.decrypt(encrypted_key).decode()
            return decrypted_key
        except Exception as e:
            logger.error(f"Error retrieving API key: {e}")
            return None
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        # Validate storage config
        if self.storage.memory_cache_size_mb <= 0:
            errors.append("Memory cache size must be positive")
        if self.storage.disk_cache_size_mb <= 0:
            errors.append("Disk cache size must be positive")
        if self.storage.history_limit <= 0:
            errors.append("History limit must be positive")
        if self.storage.cache_ttl_seconds <= 0:
            errors.append("Cache TTL must be positive")
        
        # Validate network config
        if self.network.timeout_seconds <= 0:
            errors.append("Network timeout must be positive")
        if self.network.max_retries < 0:
            errors.append("Max retries cannot be negative")
        
        # Validate output config
        valid_formats = ["json", "table", "raw", "yaml", "xml"]
        if self.output.default_format not in valid_formats:
            errors.append(f"Default format must be one of: {', '.join(valid_formats)}")
        if self.output.table_max_rows <= 0:
            errors.append("Table max rows must be positive")
        
        return errors
    
    def apply_env_overrides(self) -> "ReqSmithConfig":
        """Apply environment variable overrides"""
        config_dict = self.to_dict()
        
        for env_var, (config_path, value_type) in self.ENV_MAPPINGS.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    # Convert value to appropriate type
                    if value_type == bool:
                        converted_value = env_value.lower() in ('true', '1', 'yes', 'on')
                    elif value_type == int:
                        converted_value = int(env_value)
                    else:
                        converted_value = env_value
                    
                    # Set nested value
                    self._set_nested_value(config_dict, config_path, converted_value)
                    logger.debug(f"Applied environment override: {env_var}={env_value}")
                    
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid environment variable {env_var}={env_value}: {e}")
        
        return self.from_dict(config_dict)
    
    def _set_nested_value(self, config_dict: Dict[str, Any], path: str, value: Any) -> None:
        """Set a nested value in configuration dictionary"""
        keys = path.split('.')
        current = config_dict
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    @classmethod
    def _migrate_config(cls, config_data: Dict[str, Any], from_version: str) -> Dict[str, Any]:
        """Migrate configuration from older version"""
        if from_version == "1.0":
            # Migrate from 1.0 to 1.1
            config_data = cls._migrate_v1_0_to_v1_1(config_data)
        
        config_data["version"] = ConfigVersion.CURRENT.value
        return config_data
    
    @classmethod
    def _migrate_v1_0_to_v1_1(cls, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate configuration from version 1.0 to 1.1"""
        # Add new fields with defaults
        if "ai" not in config_data:
            config_data["ai"] = {}
        
        ai_config = config_data["ai"]
        if "enable_explanations" not in ai_config:
            ai_config["enable_explanations"] = True
        
        # Rename old fields if they exist
        if "output" in config_data:
            output_config = config_data["output"]
            if "max_table_rows" in output_config:
                output_config["table_max_rows"] = output_config.pop("max_table_rows")
        
        return config_data
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration for display"""
        return {
            "version": self.version,
            "storage": {
                "memory_cache_mb": self.storage.memory_cache_size_mb,
                "disk_cache_mb": self.storage.disk_cache_size_mb,
                "history_limit": self.storage.history_limit,
                "storage_path": self.storage.user_storage_path
            },
            "network": {
                "timeout": self.network.timeout_seconds,
                "max_retries": self.network.max_retries,
                "verify_ssl": self.network.verify_ssl
            },
            "output": {
                "format": self.output.default_format,
                "colors": self.output.color_output,
                "table_rows": self.output.table_max_rows
            },
            "ai": {
                "api_key_set": self.ai.gemini_api_key is not None,
                "suggestions": self.ai.enable_suggestions,
                "validation": self.ai.enable_validation,
                "explanations": self.ai.enable_explanations
            },
            "debug": self.debug
        }
    
    def update_setting(self, key_path: str, value: str) -> bool:
        """Update a configuration setting by key path"""
        try:
            config_dict = self.to_dict()
            
            # Determine the expected type from the current value
            current_value = self._get_nested_value(config_dict, key_path)
            if current_value is not None:
                value_type = type(current_value)
                
                # Convert value to appropriate type
                if value_type == bool:
                    converted_value = value.lower() in ('true', '1', 'yes', 'on')
                elif value_type == int:
                    converted_value = int(value)
                elif value_type == float:
                    converted_value = float(value)
                else:
                    converted_value = value
                
                # Set the value
                self._set_nested_value(config_dict, key_path, converted_value)
                
                # Update self from the modified dictionary
                updated_config = self.from_dict(config_dict)
                self.__dict__.update(updated_config.__dict__)
                
                return True
            else:
                logger.error(f"Configuration key not found: {key_path}")
                return False
                
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error updating configuration {key_path}={value}: {e}")
            return False
    
    def _get_nested_value(self, config_dict: Dict[str, Any], path: str) -> Any:
        """Get a nested value from configuration dictionary"""
        keys = path.split('.')
        current = config_dict
        
        try:
            for key in keys:
                current = current[key]
            return current
        except KeyError:
            return None


# Global configuration instance
_config: Optional[ReqSmithConfig] = None


def get_config() -> ReqSmithConfig:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        _config = ReqSmithConfig.load_from_file()
    return _config


def reload_config(config_path: Optional[Path] = None) -> ReqSmithConfig:
    """Reload configuration from file"""
    global _config
    _config = ReqSmithConfig.load_from_file(config_path)
    return _config


def save_config() -> bool:
    """Save the current configuration to file"""
    config = get_config()
    return config.save_to_file()