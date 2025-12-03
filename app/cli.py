import sys
import time
import logging
from pathlib import Path

print("\n[System] Booting Onyx AI v2 (Optimized)...")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("OnyxCLI")

try:
    from app.features.audio_extraction.service.api import extract_audio
    from app.features.transcription.service.api import transcribe_audio
    from app.features.intelligence_router.service.api import route_transcript
    from app.features.vision_analysis.service.api import analyze_video_segments_batch
    from app.features.knowledge_base.service.api import ingest_processed_video
    from app.features.chat.service.rag_service import chat_session
except ImportError as e:
    print(f"Error: {e}")
    sys.exit(1)

def main():
    print("\n==========================================")
    print("      ONYX: Secure On-Premise AI          ")
    print("==========================================\n")

    if len(sys.argv) < 2:
        print("Usage: python -m app.cli \"Video.mp4\"")
        sys.exit(1)

    # Handle filenames with spaces
    video_path = Path(" ".join(sys.argv[1:]))
    if not video_path.exists():
        print(f"❌ Error: File not found: '{video_path}'")
        sys.exit(1)

    try:
        # --- PHASE 1: INGESTION ---
        print("\n[1/5] Extracting Audio...")
        audio_path = extract_audio(video_path)
        
        print("\n[2/5] Transcribing Audio...")
        transcript = transcribe_audio(audio_path)
        
        print("\n[3/5] Intelligence Routing...")
        routing_result = route_transcript(transcript)

        # 4. BATCH Vision Analysis
        visual_contexts = []
        if routing_result.total_triggers_found > 0:
            print(f"\n[4/5] Analyzing Visuals (Batch Mode - Fast)...")
            print(f"      -> Processing {routing_result.total_triggers_found} events in ONE pass.")
            
            # Using the new Batch API
            visual_contexts = analyze_video_segments_batch(
                video_path, 
                routing_result.visual_queries
            )
        else:
            print("\n[4/5] No visuals found.")

        print("\n[5/5] Indexing...")
        ingest_processed_video(video_path.name, transcript, visual_contexts)
        print("✅ Ingestion Complete.")

        # --- PHASE 2: PERSISTENT CHAT ---
        print("\n==========================================")
        print("      🤖 ONYX READY (Session Mode)        ")
        print("      (The AI will stay loaded!)          ")
        print("==========================================\n")

        # Start the Session: This loads Qwen 14B ONCE
        with chat_session() as chat:
            history = []
            while True:
                try:
                    user_input = input("\nYou: ")
                except EOFError:
                    break
                    
                if user_input.lower() in ["exit", "quit"]:
                    break
                if not user_input.strip():
                    continue
                    
                print("Onyx: (Thinking... 🧠)")
                
                # Fast Response (Model is already loaded)
                response = chat.ask(user_input, history)
                
                print(f"\nOnyx: {response.answer}")
                if response.citations:
                    print("\n   Sources:")
                    for cit in response.citations:
                        print(f"   - [{cit.timestamp_start:.1f}s] {cit.text_snippet}...")
                        
                history.append({"role": "user", "content": user_input})
                history.append({"role": "assistant", "content": response.answer})

    except KeyboardInterrupt:
        print("\nUser Interrupted.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failure: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()