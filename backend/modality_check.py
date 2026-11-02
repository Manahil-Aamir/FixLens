
import argparse
import base64
from pathlib import Path

from openai import OpenAI
from app.config import get_settings


def b64(path: str) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode()


def classify_response(response: str, modality: str) -> str:
    text = response.lower().strip()

    disclaimers = {
        "image": [
            "i cannot see images",
            "i can't see images",
            "i cannot view images",
            "i can't view images",
            "as a text-based ai",
            "unable to view the image",
            "cannot analyze images",
        ],
        "audio": [
            "i cannot listen",
            "i can't listen",
            "i cannot hear",
            "i can't hear",
            "unable to listen",
            "unable to hear",
            "as a text-based ai",
            "cannot analyze audio",
            "don't have the ability to listen",
        ],
        "video": [
            "i cannot watch videos",
            "i can't watch videos",
            "i cannot view videos",
            "i can't view videos",
            "unable to watch the video",
            "as a text-based ai",
            "cannot analyze video",
        ],
    }

    if not text:
        return "INCONCLUSIVE"

    if any(phrase in text for phrase in disclaimers[modality]):
        return "UNSUPPORTED"

    return "INCONCLUSIVE"


def ask(
    client: OpenAI,
    model: str,
    content: list[dict],
    label: str,
    modality: str,
) -> None:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content}],
            max_tokens=1500,
        )

        result = response.choices[0].message.content or ""
        result = result.strip()

        status = classify_response(result, modality)

        print(f"\n[{label}] {status}")
        print(f"Response: {result[:500]!r}")

    except Exception as e:
        error = str(e).lower()

        unsupported_indicators = [
            "unsupported",
            "not supported",
            "does not support",
            "invalid content type",
            "unknown content type",
            "unsupported modality",
            "invalid request",
        ]

        if any(term in error for term in unsupported_indicators):
            status = "UNSUPPORTED"
        else:
            status = "INCONCLUSIVE"

        print(f"\n[{label}] {status}")
        print(f"Error: {type(e).__name__}: {str(e)[:500]}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check model input modality support."
    )

    parser.add_argument("--image")
    parser.add_argument("--audio")
    parser.add_argument("--video")

    args = parser.parse_args()

    settings = get_settings()

    model = settings.baseten_model

    print(f"Testing model: {model}")

    client = OpenAI(
        api_key=settings.baseten_api_key,
        base_url=settings.baseten_base_url,
        timeout=90,
    )

    if args.image:
        path = Path(args.image)

        if not path.is_file():
            print(f"[image] FAILED: File not found: {path}")
        else:
            extension = path.suffix.lower()

            mime_types = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".webp": "image/webp",
                ".gif": "image/gif",
            }

            mime = mime_types.get(extension)

            if not mime:
                print(f"[image] FAILED: Unsupported image format: {extension}")
            else:
                img = {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime};base64,{b64(str(path))}"
                    },
                }

                ask(
                    client,
                    model,
                    [
                        {
                            "type": "text",
                            "text": (
                                "Describe the actual contents of this image. "
                                "Mention specific visible objects, colors, "
                                "and their arrangement."
                            ),
                        },
                        img,
                    ],
                    "image",
                    "image",
                )

    if args.audio:
        path = Path(args.audio)

        if not path.is_file():
            print(f"[audio] FAILED: File not found: {path}")
        else:
            fmt = path.suffix.lstrip(".").lower()

            if fmt not in ("wav", "mp3"):
                print(f"[audio] FAILED: Use WAV or MP3. Got: {fmt}")
            else:
                ask(
                    client,
                    model,
                    [
                        {
                            "type": "text",
                            "text": (
                                "Listen to the audio and describe the "
                                "actual sounds or spoken words. "
                                "Do not guess if you cannot access the audio."
                            ),
                        },
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": b64(str(path)),
                                "format": fmt,
                            },
                        },
                    ],
                    f"audio ({fmt})",
                    "audio",
                )

    if args.video:
        path = Path(args.video)

        if not path.is_file():
            print(f"[video] FAILED: File not found: {path}")
        else:
            if path.stat().st_size > 5 * 1024 * 1024:
                print("[video] FAILED: Video exceeds 5 MB.")
            else:
                ask(
                    client,
                    model,
                    [
                        {
                            "type": "text",
                            "text": (
                                "Describe the actual visual events in "
                                "this video, including objects and "
                                "their movement. Do not guess."
                            ),
                        },
                        {
                            "type": "video_url",
                            "video_url": {
                                "url": (
                                    "data:video/mp4;base64,"
                                    + b64(str(path))
                                )
                            },
                        },
                    ],
                    "video",
                    "video",
                )


if __name__ == "__main__":
    main()
