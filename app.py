#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Flask,request,jsonify,render_template

from services.rag_service import search_knowledge
from services.llm_service import ask_llm
from services.tts_service import text_to_speech
from services.filter_service import is_related_question

app = Flask(__name__)


@app.route("/")
def index():

    return render_template("index.html")


@app.route("/chat",methods=["POST"])
def chat():

    data = request.json

    question = data.get("question")

    need_audio = data.get("need_audio",True)

    if not question:

        return jsonify({"error":"question required"}),400

    if not is_related_question(question):

        return jsonify({
            "answer":"这个问题超出了我的专业范围，我是专门讲高考志愿和就业规划的。"
        })

    try:

        # RAG
        context = search_knowledge(question)

        # LLM
        answer = ask_llm(question,context)

        result = {
            "answer":answer
        }

        # TTS
        if need_audio:

            audio = text_to_speech(answer)

            if audio:
                result["audio"] = audio

        return jsonify(result)

    except Exception as e:

        return jsonify({"error":str(e)}),500


if __name__ == "__main__":

    app.run(host="0.0.0.0",port=5000)