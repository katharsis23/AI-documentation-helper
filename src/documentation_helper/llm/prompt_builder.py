from src.documentation_helper.protocols.chunker import Chunk


class PromptBuilder:
    system_prompt = """You are a professional technical documentation assistant.
Your task is to provide accurate, concise, and clear answers to the user's questions based EXCLUSIVELY on the provided Context.

Adhere strictly to the following rules:
1. Use ONLY the information provided in the "CONTEXT" section. Do not invent facts or extrapolate beyond what is explicitly stated.
2. If the provided Context does not contain enough information to answer the question, state clearly: "I cannot find information about this in the uploaded documentation."
3. If code snippets are available in the context, format them using standard Markdown code blocks (e.g., ```python ... ```).
4. Do not assume or guess anything that is not directly supported by the context.
5. Provide your answer in a helpful, structured format."""

    def __init__(self, question: str, chunks: list[Chunk]):
        self.question = question
        self.chunks = chunks

    def _format_context(self) -> str:
        """Formats the list of retrieved chunks into a single string block."""
        formatted_blocks = []
        for i, chunk in enumerate(self.chunks, start=1):
            header_info = (
                f" (Section: {chunk.section_header})" if chunk.section_header else ""
            )
            block = (
                f"--- SOURCE {i}{header_info} [File: {chunk.source_file}] ---\n"
                f"{chunk.text.strip()}"
            )
            formatted_blocks.append(block)

        return "\n\n".join(formatted_blocks)

    def build(self) -> str:
        """Assembles the final prompt to be passed to the LLM."""
        context_text = self._format_context()

        user_content = f"""CONTEXT:
{context_text}

----------------
USER QUESTION:
{self.question}

ANSWER:"""

        return f"{self.system_prompt}\n\n{user_content}"
