import asyncio
import os
import uuid
from agentswarm.datamodels import Context, LocalStore, LocalFeedbackSystem, Feedback
from agentswarm.llms import GeminiLLM
from agentswarm.utils.tracing import LocalTracing
from dotenv import load_dotenv

load_dotenv()


async def main():
    print("🚀 Verification of Feedback System")

    # 1. Initialize Feedback System and subscribe
    feedback_system = LocalFeedbackSystem()

    def on_feedback(fb: Feedback):
        if fb.source == "llm":
            print(f"LLM Chunk: {fb.payload}", end="", flush=True)
        else:
            print(f"\n[FEEDBACK] from {fb.source}: {fb.payload}")

    feedback_system.subscribe(on_feedback)

    # 2. Setup Context
    tracing = LocalTracing()
    trace_id = str(uuid.uuid4())

    # We'll use Gemini if API key is available, otherwise this is just a structure test
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print(
            "⚠️ GEMINI_API_KEY not found. This test will only verify the emission mechanism."
        )
        llm = None
    else:
        llm = GeminiLLM(api_key=api_key)

    context = Context(
        trace_id=trace_id,
        messages=[],
        store=LocalStore(),
        tracing=tracing,
        feedback=feedback_system,
        default_llm=llm,
    )

    # 3. Manually emit feedback
    context.emit_feedback("Agent is starting some heavy work...", source="my_agent")

    # 4. Test LLM streaming (if LLM is available)
    if llm:
        from agentswarm.datamodels import Message

        print("\n--- Testing LLM Streaming ---")
        messages = [Message(type="user", content="Tell me a very short joke.")]
        await llm.generate(messages=messages, feedback=context.feedback)
        print("\n--- LLM Streaming Done ---")
    else:
        # Mocking an LLM chunk emission
        context.emit_feedback("This is a mock chunk", source="llm")

    print("\n✅ Verification finished.")


if __name__ == "__main__":
    asyncio.run(main())
