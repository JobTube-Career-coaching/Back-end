from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path
from grobid_client.api.pdf import process_fulltext_document
from grobid_client.models import Article, ProcessForm
from grobid_client.types import TEI, File
from grobid_client import Client
import openai

app = Flask(__name__)
CORS(app)  # CORS 허용

openai.api_key = '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'
client = Client(base_url="https://kermitt2-grobid.hf.space/api")

@app.route('/process-pdf', methods=['POST'])
def process_pdf():
    try:
        file = request.files.get('file')
        if not file:
            return jsonify({"error": "No file provided"}), 400

        pdf_file = Path(file.filename)
        with pdf_file.open("wb") as f:
            f.write(file.read())

        with pdf_file.open("rb") as fin:
            form = ProcessForm(
                input_=File(file_name=pdf_file.name, payload=fin, mime_type="application/pdf")
            )

            r = process_fulltext_document.sync_detailed(client=client, multipart_data=form)

            if not r.is_success:
                return jsonify({"error": "Failed to process PDF"}), 500

            article: Article = TEI.parse(r.content, figures=False)
            paragraph = " ".join(p.text for p in article.sections[2].paragraphs).strip()

            messages = [
                {'role': 'system', 'content': 'You are a helpful assistant for summarizing research papers.'},
                {'role': 'user', 'content': f'Summarize it briefly in Korean: {paragraph}'}
            ]

            res = openai.ChatCompletion.create(model='gpt-4o-mini', messages=messages)
            summary = res['choices'][0]['message']['content']

            return jsonify({"summary": summary})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
