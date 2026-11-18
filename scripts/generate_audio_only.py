import asyncio
from pathlib import Path
import edge_tts

PROJECT_ROOT = Path(r"E:\W c One Drive\Wisper")
TEMP_DIR = PROJECT_ROOT / "videos" / "temp_full_overview_build"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

from generate_full_app_overview_video import SCENES

async def main():
    print("Generating 15 TTS voice clips with edge-tts (ChristopherNeural)...")
    for idx, scene in enumerate(SCENES):
        audio_p = TEMP_DIR / f"{scene['id']}.mp3"
        print(f"[{idx+1}/{len(SCENES)}] Synthesizing {scene['id']}...")
        communicator = edge_tts.Communicate(scene["script"], "en-US-ChristopherNeural", rate="+3%")
        await communicator.save(str(audio_p))
        print(f"  Saved -> {audio_p.name} ({audio_p.stat().st_size} bytes)")
    print("All 15 voice clips generated successfully!")

if __name__ == "__main__":
    import sys
    sys.path.append(str(PROJECT_ROOT / "scripts"))
    asyncio.run(main())
