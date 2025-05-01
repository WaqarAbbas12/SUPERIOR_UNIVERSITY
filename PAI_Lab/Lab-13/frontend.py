import gradio as gr
import requests

chatbot_name = "Lumina: Your HR Policy Assistant"


def chat_with_bot(user_input, history):
    response = requests.post("http://localhost:5000/chat", json={"query": user_input})
    bot_reply = response.json().get("response", "")
    history.append((user_input, bot_reply))
    return "", history


def upload_pdf(file_path):
    with open(file_path, "rb") as f:
        files = {"file": (file_path, f, "application/pdf")}
        response = requests.post("http://localhost:5000/upload", files=files)
    return response.json().get("message", "Upload failed.")


def end_chat():
    response = requests.post("http://localhost:5000/end_chat")
    return response.json().get("message", "Failed to end chat.")


with gr.Blocks() as demo:
    gr.Markdown(f"# {chatbot_name}")
    with gr.Row():
        with gr.Column():
            pdf_file = gr.File(label="Upload HR Policy PDF", type="filepath")
            upload_button = gr.Button("Upload")
            upload_status = gr.Textbox(label="Upload Status")
        with gr.Column():
            chatbot = gr.Chatbot()
            msg = gr.Textbox(label="Your Question")
            send = gr.Button("Send")
            end = gr.Button("End Chat")
            end_status = gr.Textbox(label="Chat Status")

    upload_button.click(upload_pdf, inputs=pdf_file, outputs=upload_status)
    send.click(chat_with_bot, inputs=[msg, chatbot], outputs=[msg, chatbot])
    end.click(end_chat, outputs=end_status)

demo.launch()
