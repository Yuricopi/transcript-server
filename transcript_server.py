#!/usr/bin/env python3
"""
YouTube Transcript Webhook Server
POST /transcript  →  {"video_id": "...", "lang": "ja"}
                  ←  {"transcript": "字幕テキスト全文"}
"""

import os
from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

app = Flask(__name__)


def fetch_transcript(video_id: str, preferred_lang: str = "ja") -> str:
    """
    指定した言語の字幕を取得する。
    見つからなければ英語にフォールバック。
    それも無ければ利用可能な最初の字幕を返す。
    """
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

    # 1. 要求言語を試みる
    # 2. 英語にフォールバック
    # 3. 自動生成字幕も含めて利用可能なものを探す
    fallback_order = [preferred_lang, "en", "en-US", "en-GB"]

    for lang in fallback_order:
        try:
            transcript = transcript_list.find_transcript([lang])
            entries = transcript.fetch()
            return " ".join(entry["text"] for entry in entries)
        except NoTranscriptFound:
            continue

    # それでも見つからなければ最初に利用可能な字幕を使う
    for transcript in transcript_list:
        entries = transcript.fetch()
        return " ".join(entry["text"] for entry in entries)

    raise NoTranscriptFound(video_id, [], [])


@app.route("/transcript", methods=["POST"])
def transcript():
    data = request.get_json(silent=True)

    if not data or "video_id" not in data:
        return jsonify({"error": "video_id is required"}), 400

    video_id = data["video_id"].strip()
    lang = data.get("lang", "ja")

    if not video_id:
        return jsonify({"error": "video_id must not be empty"}), 400

    try:
        text = fetch_transcript(video_id, lang)
        return jsonify({"transcript": text})

    except TranscriptsDisabled:
        return jsonify({"error": "Transcripts are disabled for this video"}), 404

    except NoTranscriptFound:
        return jsonify({"error": "No transcript found for the requested languages"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
