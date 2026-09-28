class ServiceError(Exception):
    code = "service_error"
    status_code = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ConfigurationError(ServiceError):
    code = "configuration_error"
    status_code = 503


class DocumentValidationError(ServiceError):
    code = "document_validation_error"
    status_code = 400


class DocumentNotFoundError(ServiceError):
    code = "document_not_found"
    status_code = 404


class UnsupportedDocumentError(ServiceError):
    code = "unsupported_document"
    status_code = 415


class UnsupportedScannedDocumentError(UnsupportedDocumentError):
    code = "unsupported_scanned_document"


class EmbeddingError(ServiceError):
    code = "embedding_error"
    status_code = 502


class SearchError(ServiceError):
    code = "search_error"
    status_code = 502


class LLMError(ServiceError):
    code = "llm_error"
    status_code = 502


class StorageError(ServiceError):
    code = "storage_error"
    status_code = 502


class DependencyUnavailableError(ServiceError):
    code = "dependency_unavailable"
    status_code = 503
