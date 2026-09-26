from src.documentation_helper.config import Config


class RAGPipeline:
    def __init__(
        self,
        config: Config,
        parser_factory,
        chunker,
        embedding_provider,
        vector_store,
        llm_provider,
        prompt_builder,
    ): ...
