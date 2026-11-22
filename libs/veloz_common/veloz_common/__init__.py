"""Microservice chassis da Loja Veloz.

Concentra as preocupações transversais (cross-cutting concerns) que todo serviço
precisa ter de forma idêntica: configuração por ambiente, logs estruturados,
métricas RED, tracing distribuído e endpoints de saúde.
"""

from veloz_common.app import create_base_app
from veloz_common.config import env, env_bool, env_float, env_int

__all__ = ["create_base_app", "env", "env_bool", "env_float", "env_int"]
