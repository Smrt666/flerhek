import structlog

from flare_ai_rag.ai import GeminiProvider
from flare_ai_rag.attestation import Vtpm, VtpmAttestationError
from flare_ai_rag.prompts import PromptService, SemanticRouterResponse
from flare_ai_rag.responder import GeminiResponder
from flare_ai_rag.retriever import QdrantRetriever
from flare_ai_rag.router import GeminiRouter


class BaseRouter:
    """
    A simple router that processes incoming messages using the RAG pipeline.

    It wraps the existing query classification, document retrieval, and response
    generation components to handle a conversation in a single endpoint.
    """

    def __init__(  # noqa: PLR0913
        self,
        router_name: str,
        ai: GeminiProvider,
        query_router: GeminiRouter,
        retriever: QdrantRetriever,
        responder: GeminiResponder,
        attestation: Vtpm,
        prompts: PromptService,
    ) -> None:
        """
        Initialize the BaseRouter.

        Args:
            router (APIRouter): FastAPI router to attach endpoints.
            ai (GeminiProvider): AI client used by a simple semantic router
                to determine if an attestation was requested or if RAG
                pipeline should be used.
            query_router: RAG Component that classifies the query.
            retriever: RAG Component that retrieves relevant documents.
            responder: RAG Component that generates a response.
            attestation (Vtpm): Provider for attestation services
            prompts (PromptService): Service for managing prompts
        """
        self.ai = ai
        self.query_router = query_router
        self.retriever = retriever
        self.responder = responder
        self.attestation = attestation
        self.prompts = prompts
        self.histories = {}
        self.logger = structlog.get_logger(__name__).bind(router=router_name)

    async def generate_response(
        self, message: str, user_id: str
    ) -> dict[str, str]:
        """
        Generate a response by feeding the given message through the RAG pipeline.

        Args:
            message: Message to pass to RAG pipeline
            user_id: The user ID

        Returns:
            dict[str, str]: Response from the RAG pipeline

        Raises:
            Exception: When generating the response failed
        """
        try:
            history = self.histories.get(user_id, [])

            # If attestation has previously been requested:
            if self.attestation.attestation_requested:
                try:
                    resp = self.attestation.get_token([message])
                except VtpmAttestationError as e:
                    resp = f"The attestation failed with error:\n{e.args[0]}"
                self.attestation.attestation_requested = False
                return {"response": resp}

            route = await self.get_semantic_route(message, user_id, history)
            self.logger.info("Query routed", route=route)
            routed_message = await self.route_message(
                route, message, user_id, history
            )

            self.histories[user_id] = history[-20:] + [message]

            return routed_message

        except Exception as e:
            self.logger.exception("Generating response failed", error=str(e))
            raise e

    async def get_semantic_route(
        self, message: str, user_id: str, history: list[str]
    ) -> SemanticRouterResponse:
        """
        Determine the semantic route for a message using AI provider.

        Args:
            message: Message to route
            user_id: The user ID
            history: Chat history

        Returns:
            SemanticRouterResponse: Determined route for the message
        """
        try:
            formatted_history = "\n".join(f"- {question}" for question in history)
            prompt, mime_type, schema = self.prompts.get_formatted_prompt(
                "semantic_router", user_input=message, user_history=formatted_history
            )
            route_response = self.ai.generate(
                prompt=prompt, response_mime_type=mime_type, response_schema=schema
            )
            return SemanticRouterResponse(route_response.text)
        except Exception as e:
            self.logger.exception("routing_failed", error=str(e))
            return SemanticRouterResponse.CONVERSATIONAL

    async def route_message(
        self,
        route: SemanticRouterResponse,
        message: str,
        user_id: str,
        history: list[str],
    ) -> dict[str, str]:
        """
        Route a message to the appropriate handler based on semantic route.

        Args:
            route: Determined semantic route
            message: Original message to handle
            user_id: The user ID
            history: Chat history

        Returns:
            dict[str, str]: Response from the appropriate handler
        """
        handlers = {
            SemanticRouterResponse.RAG_ROUTER: self.handle_rag_pipeline,
            SemanticRouterResponse.REQUEST_ATTESTATION: self.handle_attestation,
            SemanticRouterResponse.CONVERSATIONAL: self.handle_conversation,
        }

        handler = handlers.get(route)
        if not handler:
            return {"response": "Unsupported route"}

        return await handler(message, user_id, history)

    async def handle_rag_pipeline(
        self, message: str, user_id: str, history: list[str]
    ) -> dict[str, str]:
        """
        Handle attestation requests.

        Args:
            message: Message parameter
            user_id: The user ID
            history: Chat history

        Returns:
            dict[str, str]: Response containing attestation request
        """
        # Step 1. Classify the user query.
        formatted_history = "\n".join(f"- {question}" for question in history)
        prompt, mime_type, schema = self.prompts.get_formatted_prompt(
            "rag_router", user_input=message, user_history=formatted_history
        )
        classification = self.query_router.route_query(
            prompt=prompt, response_mime_type=mime_type, response_schema=schema
        )
        self.logger.info("Query classified", classification=classification)

        if classification not in ["CODE", "ANSWER", "REJECT"]:
            self.logger.exception("RAG Routing failed")
            raise ValueError(classification)

        if classification == "REJECT":
            return {
                "classification": "REJECT",
                "response": "The query is out of scope.",
            }

        classification_type = classification.lower()
        other_type = "code" if classification_type == "answer" else "answer"

        # Step 2. Construct query for RAG
        query = "\n\n".join(history) + "\n\n" + message

        # Step 3. Retrieve relevant documents.
        retrieved_docs = self.retriever.semantic_search(
            classification_type, query, top_k=5
        )
        retrieved_docs_other = self.retriever.semantic_search(
            other_type, query, top_k=2
        )
        documents = retrieved_docs + retrieved_docs_other
        self.logger.info("Documents retrieved", documents=documents)

        # Step 4. Generate the final answer.
        answer = self.responder.generate_response(message, history, documents)
        self.logger.info("Response generated", answer=answer)
        return {"classification": classification, "response": answer}

    async def handle_attestation(self, _: str, __: str, ___: list[str]) -> dict[str, str]:
        """
        Handle attestation requests.

        Args:
            _: Unused message parameter
            __: Unused user ID parameter
            ___: Unused chat history parameter

        Returns:
            dict[str, str]: Response containing attestation request
        """
        prompt = self.prompts.get_formatted_prompt("request_attestation")[0]
        request_attestation_response = self.ai.generate(prompt=prompt)
        self.attestation.attestation_requested = True
        return {"response": request_attestation_response.text}

    async def handle_conversation(
        self, message: str, user_id: str, _: list[str]
    ) -> dict[str, str]:
        """
        Handle general conversation messages.

        Args:
            message: Message to process
            user_id: The user ID
            _: Unused chat history parameter

        Returns:
            dict[str, str]: Response from AI provider
        """
        response = self.ai.send_message(message, user_id)
        return {"response": response.text}
