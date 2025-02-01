import json

from src.connectors.connector_type import ConnectorType
from src.connectors.registry import ConnectorConfig, get_connector_config_schema


def serialize_connector_config(config: ConnectorConfig) -> str:
    return config.model_dump_json()


def deserialize_connector_config(config_str: str) -> ConnectorConfig:
    config_dict = json.loads(config_str)
    connector_type = config_dict.get("type")

    if not connector_type:
        raise ValueError("Connector type not found in config")

    schema_class = get_connector_config_schema(ConnectorType(connector_type))
    return schema_class(**config_dict)
