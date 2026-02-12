"""
Clase base abstracta para extractores batch.

Patrón Template Method:
    run() define el flujo: extract → validate → enrich
    Cada subclase implementa extract() y opcionalmente validate().
"""
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, List, Dict

import requests
import structlog

logger = structlog.get_logger()


class BaseExtractor(ABC):
    """
    Clase base para todos los extractores de datos batch.

    Uso:
        class MiExtractor(BaseExtractor):
            def extract(self) -> list[dict]:
                return [{"dato": "valor"}]

        extractor = MiExtractor("mi_fuente")
        datos = extractor.run()  # extract → validate → enrich
    """

    def __init__(self, source_name: str):
        self.source_name = source_name
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "CryptoLake/1.0 (Educational Project)",
            "Accept": "application/json",
        })

    def run(self) -> List[Dict[str, Any]]:
        """Ejecuta el pipeline completo: extract → validate → enrich."""
        logger.info("extraction_started", source=self.source_name)
        start_time = datetime.now(timezone.utc)

        raw_data = self.extract()
        logger.info("extraction_raw", source=self.source_name,
                    raw_count=len(raw_data))

        validated_data = self.validate(raw_data)
        logger.info(
            "extraction_validated",
            source=self.source_name,
            valid_count=len(validated_data),
            dropped=len(raw_data) - len(validated_data),
        )

        enriched_data = self.enrich(validated_data)

        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(
            "extraction_completed",
            source=self.source_name,
            total_records=len(enriched_data),
            elapsed_seconds=round(elapsed, 2),
        )

        return enriched_data

    @abstractmethod
    def extract(self) -> List[Dict[str, Any]]:
        """Extrae datos de la fuente. Debe ser implementado."""
        ...

    def validate(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validación básica: filtra registros None."""
        return [record for record in data if record is not None]

    def enrich(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Añade metadata de ingesta a cada registro."""
        now = datetime.now(timezone.utc).isoformat()
        for record in data:
            record["_ingested_at"] = now
            record["_source"] = self.source_name
        return data
