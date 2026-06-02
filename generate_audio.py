"""
PV Tool Training — ElevenLabs Audio Generator
=============================================
Generates all MP3 voice clips needed for the wrong/correct answer
sound feedback system.

Usage:
    python generate_audio.py

Set your ElevenLabs API key either:
  1. As an environment variable:  set ELEVENLABS_API_KEY=your_key_here
  2. Or just paste it when prompted.

Get a free API key at: https://elevenlabs.io  (no credit card required)
Free tier = 10,000 chars/month. All clips here ≈ 900 chars total.

Output: static/audio/*.mp3
"""

import os
import sys
import time
import requests

# ──────────────────────────────────────────────
#  CONFIGURATION
# ──────────────────────────────────────────────

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "audio")

# ElevenLabs API
BASE_URL = "https://api.elevenlabs.io/v1"

# Recommended free-tier voices (soft female):
#   Rachel  → 21m00Tcm4TlvDq8ikWAM  (warm, calm)
#   Bella   → EXAVITQu4vr4xnSDxMaL  (gentle)
#   Elli    → MF3mGyEYCl7XYWbV9V6O  (friendly)
# For Hindi the multilingual_v2 model handles Devanagari natively.

VOICE_ID = "21m00Tcm4TlvDq8ikWAM"   # Rachel — change if you prefer another
MODEL_ID = "eleven_multilingual_v2"  # supports English + Hindi

VOICE_SETTINGS = {
    "stability": 0.60,          # 0–1  (higher = more consistent, less expressive)
    "similarity_boost": 0.80,   # 0–1  (how closely to match the original voice)
    "style": 0.20,              # 0–1  (a little expressiveness)
    "use_speaker_boost": True
}

# Delay between API calls (seconds) to respect rate limits
REQUEST_DELAY = 0.8

# ──────────────────────────────────────────────
#  ALL AUDIO CLIPS TO GENERATE
#  key → file name (without .mp3 extension)
# ──────────────────────────────────────────────

CLIPS = {

    # ── Fixed feedback messages ──────────────────────────────
    "wrong_1_en": "You have selected the wrong option. Please check again.",
    "wrong_1_hi": "आपने गलत विकल्प चुना है। कृपया दोबारा जाँचें।",

    "correct_en": "Correct answer! Well done.",
    "correct_hi": "सही जवाब! बहुत अच्छे।",

    # ── 2nd-attempt prefix (before carton + issue) ───────────
    "wrong_2_prefix_en": "Wrong again. The correct answer is,",
    "wrong_2_prefix_hi": "फिर गलत। सही जवाब है,",

    # ── Connector words ──────────────────────────────────────
    "connector_carton_en": "Carton,",
    "connector_carton_hi": "कार्टन,",
    "connector_issue_en":  "Issue,",
    "connector_issue_hi":  "समस्या,",

    # ── Carton names ─────────────────────────────────────────
    "carton_pass_en":     "QC Pass Carton",
    "carton_pass_hi":     "क्यूसी पास कार्टन",

    "carton_fail_en":     "QC Fail Carton STN",
    "carton_fail_hi":     "क्यूसी फेल कार्टन",

    "carton_failnon_en":  "QC Fail Carton Non-STN",
    "carton_failnon_hi":  "क्यूसी फेल कार्टन नॉन-एसटीएन",

    "carton_refinish_en": "Refinish Carton",
    "carton_refinish_hi": "रिफिनिश कार्टन",

    "carton_onhold_en":   "On Hold Carton",
    "carton_onhold_hi":   "ऑन होल्ड कार्टन",

    # ── Issue names — English ────────────────────────────────
    "issue_no-issues_en":           "No Issues",
    "issue_missing-part_en":        "Missing Part",
    "issue_defective_en":           "Defective",
    "issue_pattern-shade_en":       "Pattern or Shade Mismatch",
    "issue_stain-dirty_en":         "Stain, Dirty, or Odor",
    "issue_stitching_en":           "Stitching Defect",
    "issue_wrinkled_en":            "Wrinkled Product",
    "issue_sod-product_en":         "SMM Product",
    "issue_sod-size_en":            "SMM Size",
    "issue_product-size_en":        "Product Size Mismatch",
    "issue_tag-mismatch_en":        "Tag Mismatch",
    "issue_bt-shaded_en":           "Brand Tag Shaded or Damaged",
    "issue_wrong-product_en":       "Wrong Product Received",
    "issue_damaged_en":             "Damaged, Cut, or Torn",
    "issue_fake_en":                "Fake or Garbage Product",
    "issue_return-not-received_en": "Return Not Received",

    # ── Issue names — Hindi ──────────────────────────────────
    "issue_no-issues_hi":           "कोई समस्या नहीं",
    "issue_missing-part_hi":        "हिस्सा गायब है",
    "issue_defective_hi":           "खराब उत्पाद",
    "issue_pattern-shade_hi":       "पैटर्न या रंग मेल नहीं",
    "issue_stain-dirty_hi":         "दाग, गंदगी या बदबू",
    "issue_stitching_hi":           "सिलाई में खराबी",
    "issue_wrinkled_hi":            "सिकुड़ा हुआ उत्पाद",
    "issue_sod-product_hi":         "SMM उत्पाद",
    "issue_sod-size_hi":            "SMM साइज",
    "issue_product-size_hi":        "साइज मेल नहीं",
    "issue_tag-mismatch_hi":        "टैग मेल नहीं",
    "issue_bt-shaded_hi":           "ब्रांड टैग खराब",
    "issue_wrong-product_hi":       "गलत उत्पाद मिला",
    "issue_damaged_hi":             "क्षतिग्रस्त उत्पाद",
    "issue_fake_hi":                "नकली या बेकार उत्पाद",
    "issue_return-not-received_hi": "रिटर्न नहीं मिला",
}


# ──────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────

def get_api_key():
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if key:
        print(f"  ✔  Using API key from environment variable.")
        return key
    print("\n  Paste your ElevenLabs API key (free at elevenlabs.io, no credit card needed):")
    key = input("  API Key → ").strip()
    if not key:
        print("  ✗  No API key provided. Exiting.")
        sys.exit(1)
    return key


def list_voices(api_key):
    """Print available voices so the user can pick one."""
    resp = requests.get(f"{BASE_URL}/voices", headers={"xi-api-key": api_key})
    if resp.status_code != 200:
        print(f"  ⚠  Could not fetch voices: {resp.status_code}")
        return
    voices = resp.json().get("voices", [])
    print("\n  Available voices on your account:")
    for v in voices:
        labels = v.get("labels", {})
        gender = labels.get("gender", "?")
        accent = labels.get("accent", "?")
        print(f"    [{v['voice_id']}]  {v['name']}  ({gender}, {accent})")
    print()


def generate_clip(api_key, text, out_path):
    """Call ElevenLabs TTS API and save the MP3."""
    url = f"{BASE_URL}/text-to-speech/{VOICE_ID}"
    headers = {
        "xi-api-key":   api_key,
        "Content-Type": "application/json",
        "Accept":       "audio/mpeg",
    }
    payload = {
        "text":           text,
        "model_id":       MODEL_ID,
        "voice_settings": VOICE_SETTINGS,
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=30)

    if resp.status_code == 200:
        with open(out_path, "wb") as f:
            f.write(resp.content)
        return True
    else:
        # Try to extract error message
        try:
            err = resp.json().get("detail", {})
            if isinstance(err, dict):
                msg = err.get("message", str(err))
            else:
                msg = str(err)
        except Exception:
            msg = resp.text[:200]
        print(f"\n    ✗  API error {resp.status_code}: {msg}")
        return False


def check_quota(api_key):
    """Show remaining character quota."""
    resp = requests.get(f"{BASE_URL}/user/subscription", headers={"xi-api-key": api_key})
    if resp.status_code == 200:
        data = resp.json()
        used  = data.get("character_count", 0)
        limit = data.get("character_limit", 10000)
        remaining = limit - used
        print(f"  ℹ  ElevenLabs quota: {used:,} used / {limit:,} total  ({remaining:,} remaining)")
        total_needed = sum(len(t) for t in CLIPS.values())
        print(f"  ℹ  This job needs ≈ {total_needed:,} characters.")
        if remaining < total_needed:
            print("  ⚠  WARNING: Not enough quota remaining for all clips!")
            print("     Already-downloaded files will be skipped automatically.")
    else:
        print("  ⚠  Could not check quota (non-critical, continuing anyway)")


# ──────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────

def main():
    global VOICE_ID   # allow reassignment if user picks a different voice
    print("\n" + "=" * 56)
    print("  PV Tool — ElevenLabs Audio Generator")
    print("=" * 56)

    # 1. API key
    api_key = get_api_key()

    # 2. Show quota
    check_quota(api_key)

    # 3. Optional: list voices
    show = input("\n  Show available voices? (y/N): ").strip().lower()
    if show == "y":
        list_voices(api_key)
        new_id = input(
            f"  Enter voice ID to use (press Enter to keep '{VOICE_ID}'): "
        ).strip()
        if new_id:
            VOICE_ID = new_id
            print(f"  \u2192 Using voice: {VOICE_ID}")

    # 4. Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"\n  Output directory: {OUTPUT_DIR}")

    # 5. Generate
    total    = len(CLIPS)
    done     = 0
    skipped  = 0
    failed   = 0

    print(f"\n  Generating {total} audio clips...\n")

    for key, text in CLIPS.items():
        out_path = os.path.join(OUTPUT_DIR, f"{key}.mp3")
        label    = f"  [{done + skipped + failed + 1:02d}/{total}]  {key}.mp3"

        # Skip if already downloaded
        if os.path.exists(out_path) and os.path.getsize(out_path) > 500:
            print(f"{label}  ⏭  skipped (already exists)")
            skipped += 1
            continue

        print(f"{label}  ⏳ generating…", end="", flush=True)
        ok = generate_clip(api_key, text, out_path)

        if ok:
            size_kb = os.path.getsize(out_path) / 1024
            print(f"\r{label}  ✔  saved ({size_kb:.1f} KB)  — \"{text[:50]}\"")
            done += 1
        else:
            print(f"\r{label}  ✗  FAILED — \"{text[:50]}\"")
            failed += 1

        time.sleep(REQUEST_DELAY)   # be polite to the API

    # 6. Summary
    print("\n" + "─" * 56)
    print(f"  Done!  ✔ {done} generated  |  ⏭ {skipped} skipped  |  ✗ {failed} failed")
    print(f"  Files saved to: {OUTPUT_DIR}")
    if failed:
        print(f"\n  ⚠  Re-run the script to retry failed clips (already-good files are skipped).")
    print("=" * 56 + "\n")


if __name__ == "__main__":
    main()
