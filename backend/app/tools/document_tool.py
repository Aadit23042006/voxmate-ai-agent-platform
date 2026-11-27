from app.tools.base import BaseTool, ToolError
from app.agents.llm_client import answer_from_context
from app.rag.document_service import retrieve_relevant_chunks


class DocumentQATool(BaseTool):
    name = "ask_document"

    def validate(self, arguments):
        question = (arguments or {}).get("question")
        if not question or not isinstance(question, str):
            raise ToolError("ask_document requires a non-empty 'question' string")
        return {"question": question.strip()}

    def run(self, db, user, arguments):
        args = self.validate(arguments)
        chunks = retrieve_relevant_chunks(db, user, args["question"])
        if not chunks:
            return {
                "question": args["question"],
                "answer": "I couldn't find any relevant uploaded document content.",
                "sources": [],
            }

        context = "\n\n".join(c.content for c in chunks)
        answer = answer_from_context(context, args["question"])
        return {
            "question": args["question"],
            "answer": answer,
            "sources": [
                {"document_id": c.document_id, "chunk_index": c.chunk_index}
                for c in chunks
            ],
        }
